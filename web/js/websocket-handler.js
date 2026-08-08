import { devLog } from './config.js';
import liveInterviewUI from './live-interview.js';

export class WebSocketHandler {
    constructor(stateManager) {
        this.stateManager = stateManager;
        this.socket = null;
        this.providerManager = null; // Direct reference to the ProviderManager
        this.session_id = null;
        this.reconnect_attempts = 0;
        this.max_reconnect_attempts = 5;
        this.is_intentionally_closing = false;
        this.checks = {};
        this.initializeCheckElements();
    }

    initializeCheckElements() {
        this.checks = {
            micPermission: document.getElementById('check-mic-permission'),
            micSelection: document.getElementById('check-mic-selection'),
            backend: document.getElementById('check-backend'),
            deepgram: document.getElementById('check-deepgram'),
            aiProvider: document.getElementById('check-ai-provider'),
            aiSecondaryProvider: document.getElementById('check-ai-secondary-provider'),
            visionProvider: document.getElementById('check-vision-provider'),
            visionSecondaryProvider: document.getElementById('check-vision-secondary-provider'),
        };
    }

    connect() {
        return new Promise((resolve, reject) => {
            this.is_intentionally_closing = false;
            // Derive the host from the page origin. main.py picks a free port at
            // startup and falls back off 8002 when it is busy, so a hardcoded port
            // would break the socket exactly when the fallback kicks in.
            const host = window.location.host || '127.0.0.1:8002';
            const scheme = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            let url = `${scheme}//${host}/ws`;
            if (this.session_id) {
                url += `?session_id=${this.session_id}`;
            }

            this.updateCheckStatus(this.checks.backend, 'pending', 'Connecting...');
            this.socket = new WebSocket(url);
            this.stateManager.setSocket(this.socket);

            // Store the promise's resolver to be called when session is confirmed.
            this.resolveConnectionPromise = resolve;

            // Clear any old listeners before attaching new ones
            this.socket.onopen = null;
            this.socket.onclose = null;
            this.socket.onerror = null;
            this.socket.onmessage = null;
            
            // Use addEventListener for all events for consistency and robustness.
            this.socket.addEventListener('open', this.onOpen.bind(this));
            this.socket.addEventListener('close', this.onClose.bind(this));
            this.socket.addEventListener('error', (err) => {
                this.onError(err);
                reject(new Error("WebSocket connection failed."));
            });
            this.socket.addEventListener('message', this.onMessage.bind(this));
        });
    }

    onOpen(event) {
        console.log("[open] Connection established");
        // This is now handled by the ProviderManager
        // this.updateCheckStatus(this.checks.backend, 'success', 'Backend Connected');
        this.reconnect_attempts = 0;
    }

    onClose(event) {
        console.log(`[close] Connection closed. Intentional: ${this.is_intentionally_closing}`);
        // This is now handled by the ProviderManager
        // this.updateCheckStatus(this.checks.backend, 'error', 'Disconnected');
        if (!this.is_intentionally_closing) {
            this.handleReconnect();
        }
    }

    onError(error) {
        console.error(`[error] WebSocket error:`, error);
        // This is now handled by the ProviderManager
        // this.updateCheckStatus(this.checks.backend, 'error', 'Connection Failed');
    }
    
    onMessage(event) {
        const data = JSON.parse(event.data);
        devLog("Received from backend:", data);

        if (data.type === 'session_created') {
            this.session_id = data.payload.session_id;
            console.log(`🚀 New session started: ${this.session_id}`);
            // Resolve the connection promise now that session is confirmed.
            if (this.resolveConnectionPromise) {
                this.resolveConnectionPromise();
                this.resolveConnectionPromise = null; // Ensure it's only called once
            }
        } else if (data.type === 'session_resumed') {
            console.log(`✅ Session resumed: ${data.payload.session_id}`);
            liveInterviewUI.addMessage("Connection restored. Your session has been resumed.", "system-message");
            // Also resolve the promise on resume.
            if (this.resolveConnectionPromise) {
                this.resolveConnectionPromise();
                this.resolveConnectionPromise = null;
            }
        }
        
        this.handleMessage(data);
    }

    handleReconnect() {
        if (this.reconnect_attempts < this.max_reconnect_attempts) {
            this.reconnect_attempts++;
            const delay = Math.pow(2, this.reconnect_attempts) * 1000;
            console.log(`Attempting to reconnect in ${delay / 1000}s... (Attempt ${this.reconnect_attempts})`);
            liveInterviewUI.addMessage(`Connection lost. Reconnecting... (Attempt ${this.reconnect_attempts})`, "system-error", true);
            
            setTimeout(() => this.connect(), delay);
        } else {
            console.error("Max reconnect attempts reached.");
            liveInterviewUI.addMessage("Could not reconnect to the server. Please restart the interview.", "system-error");
        }
    }

    disconnect() {
        this.is_intentionally_closing = true;
        if (this.socket) {
            this.socket.close();
        }
        this.session_id = null; // Clear session on intentional disconnect
    }

    // --- All original message handlers go here ---
    handleMessage(data) {
        switch (data.type) {
            case 'api_key_status':
                this.handleApiKeyStatus(data.payload);
                break;
            case 'transcript_update':
                this.handleTranscriptUpdate(data.payload);
                break;
            case 'ai_processing_started':
                this.handleAiProcessingStarted(data.payload);
                break;
            case 'ai_answer_chunk':
                this.handleAiAnswerChunk(data.payload);
                break;
            case 'ai_answer_complete':
                this.handleAiAnswerComplete(data.payload);
                break;
            case 'preset_initialized':
                this.handlePresetInitialized(data.payload);
                break;
            case 'preset_switched':
                this.handlePresetSwitched(data.payload);
                break;
            case 'preset_switch_failed':
                this.handlePresetSwitchFailed(data.payload);
                break;
            case 'vision_analysis_result':
                this.handleVisionAnalysisResult(data.payload);
                break;
            case 'error':
                this.handleError(data.payload);
                break;
            // Ignore session messages as they are handled in onMessage
            case 'session_created':
            case 'session_resumed':
                break;
            case 'session_reset_complete':
                console.log('✅ Session reset confirmed by backend');
                break;
            default:
                console.warn('Unknown message type:', data.type);
        }
    }

    // ... (All other handle... methods from the original file)
    // NOTE: This is a simplified representation. The actual file will contain the full implementations.
    setProviderManager(manager) {
        this.providerManager = manager;
    }

    handleApiKeyStatus(payload) {
        // This is the crucial fix: Delegate the UI update to the ProviderManager,
        // which now has a direct, guaranteed reference.
        if (this.providerManager) {
            this.providerManager.handleApiKeyStatus(payload);
        } else {
            console.error("Fatal Error: ProviderManager not injected into WebSocketHandler.");
        }
    }

    handleTranscriptUpdate(payload) {
        // With diarization disabled, all speech comes from speaker 0 and should be labeled as Interviewer
        // With diarization enabled, speaker 0 = candidate, speaker 1+ = interviewer(s)
        const speakerId = payload.speaker !== undefined ? payload.speaker : 0;
        
        // Since diarization is disabled, all speech (speaker 0) should be treated as interviewer
        if (payload.is_final) {
            liveInterviewUI.addInterviewerQuestion(payload.transcript, false);
        } else {
            liveInterviewUI.addInterviewerQuestion(payload.transcript, true);
        }
    }
    
    handleAiProcessingStarted(payload) {
        liveInterviewUI.startStreamingAIResponse(payload);
    }

    handleAiAnswerChunk(payload) {
        liveInterviewUI.appendStreamingChunk(payload.chunk);
    }

    handleAiAnswerComplete(payload) {
        liveInterviewUI.finalizeStreamingResponse(payload);
    }

    handlePresetInitialized(payload) {
        this.stateManager.updateState({
            currentPreset: payload.current_preset,
            availablePresets: payload.available_presets
        });
        if (window.presetManager) {
            presetManager.updatePresetDisplay(payload.current_preset);
            presetManager.updateHealthStatus(payload.health_status);
        }
    }

    handlePresetSwitched(payload) {
        this.stateManager.updateState({ currentPreset: payload.current_preset });
        if (window.presetManager) {
            presetManager.updatePresetDisplay(payload.current_preset);
            presetManager.showSwitchNotification(payload);
        }
    }

    handlePresetSwitchFailed(payload) {
        if (window.presetManager) {
            presetManager.showErrorNotification(payload.error, payload);
        }
    }
    
    handleVisionAnalysisResult(result) {
        console.log('📸 Vision analysis result received:', result.success ? 'SUCCESS' : 'FAILED');
        
        // Hide processing status if it exists
        if (this.hideVisionProcessingStatus) {
            this.hideVisionProcessingStatus();
        }
        
        // Resolve the promise in screenshot-service.js
        if (window.visionAnalysisResolver) {
            window.visionAnalysisResolver(result);
            window.visionAnalysisResolver = null; // Clear the resolver
        }
        
        // Display the result in the specialized vision UI
        if (result.success && result.analysis) {
            // Use the dedicated vision analysis method with proper metadata
            const metadata = {
                provider: result.provider,
                model: result.model,
                screenshotCount: result.screenshot_count,
                languages: result.languages
            };
            liveInterviewUI.addVisionAnalysis(result.analysis, metadata);
        } else if (!result.success && result.error) {
            liveInterviewUI.addMessage(`❌ Vision analysis failed: ${result.error}`, "system-error");
        }
    }

    handleError(payload) {
        console.error("WebSocket error:", payload);
        if (window.presetManager) {
            presetManager.showErrorNotification(payload.message);
        }
    }

    sendMessage(type, payload) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({ type, payload }));
        } else {
            console.error(`Cannot send message ${type}: WebSocket not connected.`);
        }
    }

    sendAudioChunk(chunk, is_muted) {
        this.sendMessage('audio_chunk', {
            audio_b64: this.bytesToBase64(chunk),
            is_muted: is_muted
        });
    }

    /**
     * Base64-encode a PCM buffer for transport.
     *
     * Sending the raw bytes as a JSON array of integers cost roughly 4 bytes of
     * text per byte of audio; base64 costs 1.33. Encoded in slices because
     * String.fromCharCode.apply exceeds the argument limit on large buffers.
     */
    bytesToBase64(buffer) {
        const bytes = new Uint8Array(buffer);
        const SLICE = 0x8000;
        let binary = '';
        for (let i = 0; i < bytes.length; i += SLICE) {
            binary += String.fromCharCode.apply(null, bytes.subarray(i, i + SLICE));
        }
        return btoa(binary);
    }

    startInterview() {
        const state = this.stateManager.getState();
        const initialMuteStatus = window.muteManager?.getMuteStatus() || { microphone: false, universal: false };
        
        const interviewPayload = {
            aiProvider: {
                provider: state.selectedProvider.name,
                model: state.selectedProvider.model
            },
            onboardingData: { ...state.onboardingData, selectedLanguages: state.selectedLanguages },
            is_muted: initialMuteStatus.microphone,
            is_universally_muted: initialMuteStatus.universal,
            process_all_speakers: true,
            aiSecondaryProvider: state.selectedSecondaryProvider.name ? {
                provider: state.selectedSecondaryProvider.name,
                model: state.selectedSecondaryProvider.model
            } : null,
            visionProvider: state.selectedVisionProvider.name ? {
                provider: state.selectedVisionProvider.name,
                model: state.selectedVisionProvider.model
            } : null,
            visionSecondaryProvider: state.selectedSecondaryVisionProvider.name ? {
                provider: state.selectedSecondaryVisionProvider.name,
                model: state.selectedSecondaryVisionProvider.model
            } : null,
        };
        this.sendMessage('start_interview', interviewPayload);
    }

    endInterview() {
        this.sendMessage('end_interview', {});
        this.disconnect();
    }
    
    switchPreset(presetKey) {
        if (!this.stateManager.isLiveInterviewActive()) {
            presetManager.showErrorNotification('Start the interview first.');
            return;
        }
        this.sendMessage('switch_preset', { preset_key: presetKey });
    }

    updateCheckStatus(checkElement, status, text) {
        if (!checkElement) {
            devLog(`[updateCheckStatus] Warning: Attempted to update a null checkElement.`);
            return;
        }
        const indicator = checkElement.querySelector('.indicator');
        const textNode = Array.from(checkElement.childNodes).find(node =>
            node.nodeType === Node.TEXT_NODE && node.textContent.trim() !== ''
        );
        if (indicator) {
            indicator.textContent = status === 'success' ? '🟢' : status === 'error' ? '🔴' : '⚪';
        }
        if (textNode) {
            textNode.nodeValue = ` ${text}`;
        }
        devLog(`[UI UPDATE] Set ${checkElement.id} to ${status}: ${text}`);
    }

    checkAllSystemsGo() {
        // Delegate to ProviderManager which owns the UI elements
        if (this.providerManager) {
            return this.providerManager.checkAllSystemsGo();
        } else {
            console.error("Fatal Error: ProviderManager not injected into WebSocketHandler for checkAllSystemsGo.");
            return false;
        }
    }
}