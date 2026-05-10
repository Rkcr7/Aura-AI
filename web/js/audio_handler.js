// --- audio_handler.js ---
// This module handles all interactions with the Web Media APIs
// for capturing and processing audio via an AudioWorklet.

import { devLog, devError } from './config.js';
import muteManager from './mute-manager.js';

let audioContext = null;
let micStream = null;
let systemStream = null;
let micGainNode = null;
let screenVideoTrack = null; // Store video track for screenshot reuse

/**
 * Requests permission to use the microphone and populates the dropdown.
 * @returns {Promise<boolean>} True if permission was granted, false otherwise.
 */
export async function setupMicrophone() {
    const micSelect = document.getElementById('mic-select');
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
        stream.getTracks().forEach(track => track.stop());

        const devices = await navigator.mediaDevices.enumerateDevices();
        const audioDevices = devices.filter(device => device.kind === 'audioinput');

        if (audioDevices.length === 0) return false;

        micSelect.innerHTML = '';
        audioDevices.forEach(device => {
            const option = document.createElement('option');
            option.value = device.deviceId;
            option.textContent = device.label || `Microphone ${micSelect.options.length + 1}`;
            micSelect.appendChild(option);
        });
        
        micSelect.disabled = false;
        return true;
    } catch (err) {
        devError("Error setting up microphone:", err);
        return false;
    }
}

/**
 * Starts audio processing by setting up the AudioContext, loading the worklet,
 * and connecting the audio streams.
 * @param {string} micId - The deviceId of the selected microphone.
 * @param {function} onAudioData - Callback function to handle the processed PCM audio data.
 * @returns {Promise<boolean>} True if processing started successfully.
 */
export async function startAudioProcessing(micId, onAudioData) {
    try {
        // ── PHASE 1: Initiate EVERYTHING synchronously within user-gesture ────────
        // WebKit invalidates the gesture token after the first `await`. To keep
        // getUserMedia, getDisplayMedia, and AudioContext.resume() all within
        // the gesture boundary we must START them before yielding the event loop.

        // (a) Start mic capture — initiated synchronously, not yet awaited
        const micStreamPromise = navigator.mediaDevices.getUserMedia({
            audio: { deviceId: { exact: micId } },
        });

        // (b) Start screen sharing — initiated synchronously, not yet awaited.
        //     Optional on macOS: the screen picker may be hidden behind the
        //     always-on-top Aura window; 45 s timeout → mic-only fallback.
        const withTimeout = (promise, ms, label) =>
            Promise.race([
                promise,
                new Promise((_, reject) =>
                    setTimeout(() => reject(new Error(`${label} timed out after ${ms / 1000}s`)), ms)
                ),
            ]);

        const displayMediaPromise = withTimeout(
            navigator.mediaDevices.getDisplayMedia({ video: true, audio: true }),
            45000,
            'Screen sharing'
        ).catch(err => {
            console.warn(`⚠️ System audio unavailable — mic-only mode. (${err.message})`);
            console.warn('   Tip: a "Choose what to share" dialog may be hidden behind the Aura window.');
            return null;
        });

        // (c) Create AudioContext — synchronous, within gesture ✅
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        console.log(`🎵 AudioContext created: ${audioContext.sampleRate}Hz (state: ${audioContext.state})`);

        // (d) Start loading AudioWorklet module — initiated synchronously,
        //     awaited below. Runs in parallel while screen picker is open.
        const addModulePromise = audioContext.audioWorklet.addModule('/static/js/audio_processor.js');

        // ── PHASE 2: Await all concurrent operations ──────────────────────────────
        [micStream, systemStream] = await Promise.all([
            micStreamPromise,
            displayMediaPromise,
        ]);
        await addModulePromise;
        console.log('🎛️ AudioWorklet module loaded');

        if (!micStream) {
            console.error('Could not get microphone stream.');
            stopAudioProcessing();
            return false;
        }
        if (!systemStream) {
            console.warn('⚠️ Proceeding in mic-only mode — interviewer audio will not be captured.');
        }

        // WebKit may suspend AudioContext while the screen picker was open.
        if (audioContext.state === 'suspended') {
            await audioContext.resume();
            console.log('▶️ AudioContext resumed');
        }

        // ── PHASE 3: Build audio graph ────────────────────────────────────────────
        // 3. Create a single mixed processor for better diarization
        const mixedProcessor = new AudioWorkletNode(audioContext, 'mixed-processor');

        // Handle mixed audio with mute-aware speaker detection
        let audioProcessingCounter = 0; // For throttled logging
        
        mixedProcessor.port.onmessage = (event) => {
            // If universally muted, drop all audio data immediately.
            if (muteManager.isAudioPaused()) {
                if (audioProcessingCounter % 200 === 0) { // Log occasionally to show it's paused
                    devLog(`⏸️ Audio processing paused due to universal mute.`);
                }
                audioProcessingCounter++;
                return;
            }

            const { audioData, micLevel, systemLevel } = event.data;
            let speakerHint;

            if (muteManager.isMicrophoneMuted()) {
                // When microphone is muted, all audio is from the interviewer.
                speakerHint = 'system';
                // Logging removed to reduce console noise.
            } else {
                // When unmuted, distinguish based on volume.
                speakerHint = systemLevel > micLevel * 2 ? 'system' : 'microphone';
            }

            audioProcessingCounter++;
            onAudioData(audioData, speakerHint);
        };

        // 4. Connect both sources to the mixed processor with mute control
        const micSource = audioContext.createMediaStreamSource(micStream);

        // On macOS, getDisplayMedia typically returns a video-only stream.
        // createMediaStreamSource() throws if the stream has NO audio tracks.
        // Guard: only create a system source when audio tracks actually exist.
        const systemAudioTracks = systemStream ? systemStream.getAudioTracks() : [];
        const hasSystemAudio = systemAudioTracks.length > 0;

        if (systemStream && !hasSystemAudio) {
            console.warn('⚠️ Screen shared but no system audio tracks found (common on macOS) — mic-only mode.');
        }

        const systemSource = hasSystemAudio
            ? audioContext.createMediaStreamSource(systemStream)
            : null;

        // Create gain node for microphone muting
        micGainNode = audioContext.createGain();
        updateMicGainNode(); // Set initial gain based on mute manager state
        
        // Listen for future changes
        muteManager.on('microphoneMuteChange', updateMicGainNode);
        
        // Connect mic through gain node for mute control
        micSource.connect(micGainNode);
        micGainNode.connect(mixedProcessor);
        
        // System audio connects directly only when audio tracks were captured
        if (systemSource) {
            systemSource.connect(mixedProcessor);
            console.log('🔊 System audio connected to mix');
        }

        // Store the video track for screenshots; stop it if no audio (reduces
        // the macOS screen-recording indicator overhead when unneeded).
        if (systemStream) {
            const videoTracks = systemStream.getVideoTracks();
            if (videoTracks.length > 0) {
                if (hasSystemAudio) {
                    screenVideoTrack = videoTracks[0];
                    console.log('📹 Screen video track stored for screenshot reuse');
                } else {
                    // No audio — stop video track to dismiss the recording indicator
                    videoTracks[0].stop();
                    console.log('📹 Video track stopped (no system audio available)');
                }
            }
        } else {
            console.warn('⚠️ Screenshots unavailable in mic-only mode');
        }

        devLog("✅ Audio processing started successfully");
        return true;

    } catch (err) {
        console.error("❌ Error starting audio processing:", err);
        stopAudioProcessing();
        return false;
    }
}

/**
 * Updates the microphone gain node based on the central mute manager state.
 */
function updateMicGainNode() {
    if (!micGainNode || !audioContext) return;
    
    const isMuted = muteManager.isMicrophoneMuted();
    const targetGain = isMuted ? 0 : 1;
    
    // Smooth transition to avoid audio pops
    micGainNode.gain.setTargetAtTime(targetGain, audioContext.currentTime, 0.05);
    devLog(`🎤 Microphone gain set to ${targetGain} based on mute manager.`);
}

// --- Legacy Functions (now wrappers for MuteManager) ---
// These are kept for backward compatibility with other modules that might call them.

/**
 * @deprecated Use muteManager.setMicrophoneMute(mute) instead.
 */
export function setMicrophoneMute(mute) {
    muteManager.setMicrophoneMute(mute);
    return muteManager.isMicrophoneMuted();
}

/**
 * @deprecated Use muteManager.isMicrophoneMuted() instead.
 */
export function isMicrophoneMuted() {
    return muteManager.isMicrophoneMuted();
}

/**
 * @deprecated Use muteManager.toggleMicrophoneMute() instead.
 */
export function toggleMicrophoneMute() {
    return muteManager.toggleMicrophoneMute();
}

/**
 * @deprecated Use muteManager.getMuteStatus() instead.
 */
export function getAudioProcessingMode() {
    return muteManager.getMuteStatus();
}

/**
 * Gets the screen video track for screenshot capture.
 * @returns {MediaStreamTrack|null} The screen video track if available.
 */
export function getScreenVideoTrack() {
    return screenVideoTrack;
}

/**
 * Checks if screen sharing is available for screenshots.
 * @returns {boolean} True if screen video track is available and active.
 */
export function isScreenSharingAvailable() {
    return screenVideoTrack && screenVideoTrack.readyState === 'live';
}

/**
 * Stops all audio streams and closes the AudioContext.
 */
export function stopAudioProcessing() {
    console.log("Stopping audio processing.");
    if (micStream) {
        micStream.getTracks().forEach(track => track.stop());
        micStream = null;
    }
    if (systemStream) {
        systemStream.getTracks().forEach(track => track.stop());
        systemStream = null;
    }
    if (screenVideoTrack) {
        screenVideoTrack.stop();
        screenVideoTrack = null;
        console.log("📹 Screen video track stopped");
    }
    if (audioContext && audioContext.state !== 'closed') {
        audioContext.close();
        audioContext = null;
    }
    
    // Reset mute state in the central manager
    muteManager.setMicrophoneMute(true);
    muteManager.setUniversalMute(false);
    micGainNode = null;
}