// Screenshot Service for Vision AI Processing
// Handles screen capture, queue management, and vision model integration

// Longest edge a capture is allowed to keep, in pixels. Chosen so that 1080p
// and 1440p displays are never touched and only larger or multi-monitor
// captures are scaled down. Raise it if you work on a 4K display and find
// small text being missed; lower it to shrink payloads further.
const MAX_CAPTURE_EDGE_PX = 2560;

// Screenshots queued when the provider does not declare its own limit.
const DEFAULT_MAX_SCREENSHOTS = 4;

class ScreenshotService {
    constructor() {
        this.screenshotQueue = [];
        this.maxScreenshots = DEFAULT_MAX_SCREENSHOTS;
        this.isCapturing = false;
        this.visionConfig = null;
        this.programmingLanguages = [];
        
        this.setupUI();
        this.setupStyles();
        console.log('📸 ScreenshotService initialized');
    }
    
    setupUI() {
        // Create screenshot queue UI element
        const queueContainer = document.createElement('div');
        queueContainer.id = 'screenshot-queue';
        queueContainer.className = 'screenshot-queue hidden';
        queueContainer.innerHTML = `
            <div class="queue-header">
                <span class="queue-title">📸 Screenshots Queue</span>
                <div class="queue-controls">
                    <button id="clear-queue-btn" class="queue-btn clear">Clear All</button>
                    <button id="process-queue-btn" class="queue-btn process" disabled>Process (0)</button>
                </div>
            </div>
            <div class="queue-grid" id="queue-grid">
                <!-- Screenshots will be added here -->
            </div>
        `;
        
        // Store reference for later insertion
        this.queueElement = queueContainer;
        
        // Setup event listeners
        this.setupQueueEventListeners();
    }
    
    setupQueueEventListeners() {
        // Will be set up after DOM insertion
    }
    
    insertQueueUI() {
        const liveView = document.getElementById('live-view');
        if (liveView && this.queueElement && !document.getElementById('screenshot-queue')) {
            const interviewContent = liveView.querySelector('.interview-content');
            if (interviewContent) {
                interviewContent.appendChild(this.queueElement);
                
                // Setup event listeners now that elements are in DOM
                document.getElementById('clear-queue-btn')?.addEventListener('click', () => {
                    this.clearQueue();
                });
                
                document.getElementById('process-queue-btn')?.addEventListener('click', () => {
                    this.processQueue();
                });
                
                console.log('✅ Screenshot queue UI added to live view');
            }
        }
    }
    
    setupStyles() {
        if (!document.getElementById('screenshot-service-styles')) {
            const style = document.createElement('style');
            style.id = 'screenshot-service-styles';
            style.textContent = `
                .screenshot-queue {
                    position: absolute;
                    top: 10px;
                    right: 10px;
                    width: 320px;
                    background: rgba(0, 0, 0, 0.95);
                    border: 1px solid #333;
                    border-radius: 8px;
                    backdrop-filter: blur(15px);
                    z-index: 1000;
                    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
                    transition: all 0.3s ease;
                }
                
                .screenshot-queue.hidden {
                    opacity: 0;
                    pointer-events: none;
                    transform: translateY(-10px);
                }
                
                .queue-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 12px;
                    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                }
                
                .queue-title {
                    font-size: 12px;
                    font-weight: 600;
                    color: #ffffff;
                }
                
                .queue-controls {
                    display: flex;
                    gap: 6px;
                }
                
                .queue-btn {
                    padding: 4px 8px;
                    font-size: 10px;
                    border: 1px solid #333;
                    border-radius: 4px;
                    background: rgba(255, 255, 255, 0.1);
                    color: #ffffff;
                    cursor: pointer;
                    transition: all 0.2s ease;
                }
                
                .queue-btn:hover:not(:disabled) {
                    background: rgba(255, 255, 255, 0.2);
                    border-color: #555;
                }
                
                .queue-btn:disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
                }
                
                .queue-btn.clear {
                    border-color: #f56565;
                    color: #f56565;
                }
                
                .queue-btn.clear:hover:not(:disabled) {
                    background: rgba(245, 101, 101, 0.2);
                }
                
                .queue-btn.process {
                    border-color: #48bb78;
                    color: #48bb78;
                }
                
                .queue-btn.process:hover:not(:disabled) {
                    background: rgba(72, 187, 120, 0.2);
                }
                
                .queue-grid {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 8px;
                    padding: 12px;
                    max-height: 240px;
                    overflow-y: auto;
                }
                
                .screenshot-item {
                    position: relative;
                    border-radius: 4px;
                    overflow: hidden;
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    background: rgba(255, 255, 255, 0.05);
                }
                
                .screenshot-image {
                    width: 100%;
                    height: 80px;
                    object-fit: cover;
                    display: block;
                }
                
                .screenshot-info {
                    padding: 6px;
                    font-size: 9px;
                    color: #a0aec0;
                    text-align: center;
                }
                
                .screenshot-remove {
                    position: absolute;
                    top: 4px;
                    right: 4px;
                    width: 16px;
                    height: 16px;
                    background: rgba(245, 101, 101, 0.9);
                    border: none;
                    border-radius: 50%;
                    color: white;
                    font-size: 10px;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    transition: all 0.2s ease;
                }
                
                .screenshot-remove:hover {
                    background: #f56565;
                    transform: scale(1.1);
                }
                
                .vision-mode-indicator {
                    position: fixed;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    background: rgba(0, 0, 0, 0.9);
                    color: white;
                    padding: 20px 30px;
                    border-radius: 8px;
                    border: 2px solid #6366f1;
                    backdrop-filter: blur(15px);
                    z-index: 10000;
                    text-align: center;
                    animation: fadeInScale 0.3s ease-out;
                }
                
                .vision-mode-content h3 {
                    margin: 0 0 10px 0;
                    color: #6366f1;
                    font-size: 18px;
                }
                
                .vision-mode-content p {
                    margin: 0 0 15px 0;
                    color: #a0aec0;
                    font-size: 14px;
                }
                
                .vision-hotkeys {
                    display: flex;
                    gap: 15px;
                    justify-content: center;
                }
                
                .vision-hotkey {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 5px;
                }
                
                .vision-hotkey kbd {
                    background: #6366f1;
                    color: white;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: 600;
                }
                
                .vision-hotkey span {
                    font-size: 10px;
                    color: #718096;
                }
                
                @keyframes fadeInScale {
                    from {
                        opacity: 0;
                        transform: translate(-50%, -50%) scale(0.9);
                    }
                    to {
                        opacity: 1;
                        transform: translate(-50%, -50%) scale(1);
                    }
                }
                
                .capture-notification {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    background: rgba(0, 0, 0, 0.9);
                    color: white;
                    padding: 12px 20px;
                    border-radius: 6px;
                    border-left: 4px solid #48bb78;
                    z-index: 10000;
                    animation: slideInRight 0.3s ease-out;
                    /* Matches the preset and transparency toasts, which are both
                       already click-through. Without this the toast swallows
                       clicks in the top-right corner for its full 3s lifetime. */
                    pointer-events: none;
                }

                /* showNotification() is called with 'error' for Permission Denied,
                   Capture Timeout, Capture Failed, Queue Full, No Vision Model,
                   Analysis Failed and Processing Error, and 'warning' for Queue
                   Cleared, but every one of them inherited the success green. */
                .capture-notification.error {
                    border-left-color: #f56565;
                }

                .capture-notification.warning {
                    border-left-color: #ecc94b;
                }

                .capture-notification.info {
                    border-left-color: #6366f1;
                }
                
                @keyframes slideInRight {
                    from {
                        transform: translateX(100%);
                        opacity: 0;
                    }
                    to {
                        transform: translateX(0);
                        opacity: 1;
                    }
                }
            `;
            document.head.appendChild(style);
        }
    }
    
    // Configuration methods
    /**
     * @param {number} [maxImages] Images this vision model accepts in one
     *   request. Providers differ: Cerebras gemma-4-31b rejects a third image
     *   with HTTP 413, while Gemini handles four. Without this the queue would
     *   happily fill to 4 and then fail the whole batch at Alt+P.
     */
    setVisionConfig(visionProvider, visionModel, maxImages) {
        this.visionConfig = {
            provider: visionProvider,
            model: visionModel
        };

        const cap = Number(maxImages) > 0 ? Math.floor(Number(maxImages)) : DEFAULT_MAX_SCREENSHOTS;
        if (cap !== this.maxScreenshots) {
            this.maxScreenshots = cap;
            console.log(`🔧 Screenshot queue cap set to ${cap} for ${visionProvider} ${visionModel}`);
            // Drop anything already queued beyond the new cap so Alt+P cannot
            // send a batch this model will reject.
            if (this.screenshotQueue.length > cap) {
                const dropped = this.screenshotQueue.length - cap;
                this.screenshotQueue = this.screenshotQueue.slice(0, cap);
                this.showNotification('📸 Queue Trimmed',
                    `${visionModel} accepts ${cap} image${cap === 1 ? '' : 's'} per request - removed ${dropped}`, 'warning');
            }
            this.updateQueueUI();
        }

        console.log('🔧 Vision config set:', this.visionConfig);
    }
    
    setProgrammingLanguages(languages) {
        this.programmingLanguages = languages;
        console.log('💻 Programming languages set:', this.programmingLanguages);
    }
    
    // Screenshot capture methods
    async captureScreenshot() {
        if (this.isCapturing) {
            console.log('⚠️ Screenshot capture already in progress');
            return false;
        }
        
        if (this.screenshotQueue.length >= this.maxScreenshots) {
            this.showNotification('❌ Queue Full', 'Remove some screenshots before taking more', 'error');
            return false;
        }
        
        this.isCapturing = true;
        
        try {
            // Try to use existing screen video track first
            let videoTrack = null;
            
            // Import audio handler to get existing screen track
            if (window.getScreenVideoTrack && window.isScreenSharingAvailable) {
                if (window.isScreenSharingAvailable()) {
                    videoTrack = window.getScreenVideoTrack();
                    console.log('📹 Using existing screen video track for screenshot');
                } else {
                    console.warn('⚠️ Screen sharing not available, requesting new permission');
                }
            }
            
            // Fallback to requesting new permission if no existing track
            if (!videoTrack) {
                if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
                    throw new Error('Screen capture not supported in this browser');
                }
                
                const stream = await navigator.mediaDevices.getDisplayMedia({
                    video: {
                        mediaSource: 'screen',
                        width: { max: 1920 },
                        height: { max: 1080 }
                    }
                });
                
                videoTrack = stream.getVideoTracks()[0];
                if (!videoTrack) {
                    throw new Error('No video track available from screen capture');
                }
                
                console.log('📹 Created new screen capture stream for screenshot');
            }
            
            // Create video element to capture frame
            const video = document.createElement('video');
            video.srcObject = new MediaStream([videoTrack]);
            video.play();
            
            // Wait for video to load
            await new Promise((resolve, reject) => {
                video.onloadedmetadata = resolve;
                video.onerror = reject;
                // Add timeout to prevent hanging
                setTimeout(() => reject(new Error('Video load timeout')), 5000);
            });
            
            // Create canvas and capture frame.
            //
            // The primary path reuses the display track opened by audio_handler,
            // which is requested without size constraints, so videoWidth is the
            // full native resolution. Capping the long edge bounds the payload on
            // very large or multi-monitor captures, where four queued screenshots
            // could otherwise approach a provider's request size limit.
            //
            // Verified on a 4512x3424 diagram: both Cerebras gemma-4-31b and
            // Gemini 3.6 Flash extracted exactly the same text before and after
            // downscaling, and Cerebras got 32% faster. Displays at or below the
            // cap are untouched, so most users see no change at all.
            const scale = Math.min(1, MAX_CAPTURE_EDGE_PX / Math.max(video.videoWidth, video.videoHeight));
            const canvas = document.createElement('canvas');
            canvas.width = Math.round(video.videoWidth * scale);
            canvas.height = Math.round(video.videoHeight * scale);

            const ctx = canvas.getContext('2d');
            if (scale < 1) {
                ctx.imageSmoothingEnabled = true;
                ctx.imageSmoothingQuality = 'high';
                console.log(`📐 Capture scaled ${video.videoWidth}x${video.videoHeight} -> ${canvas.width}x${canvas.height}`);
            }
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            
            // Convert to blob
            const blob = await new Promise(resolve => {
                canvas.toBlob(resolve, 'image/jpeg', 0.8);
            });
            
            // Only stop the track if we created a new one (not reusing existing)
            if (!window.getScreenVideoTrack || videoTrack !== window.getScreenVideoTrack()) {
                videoTrack.stop();
                console.log('📹 Stopped temporary screen capture track');
            }
            
            // Clean up video element
            video.srcObject = null;
            
            // Add to queue
            const screenshot = {
                id: Date.now(),
                blob: blob,
                dataUrl: canvas.toDataURL('image/jpeg', 0.8),
                timestamp: new Date(),
                size: blob.size
            };
            
            this.addToQueue(screenshot);
            this.showNotification('📸 Screenshot Captured (Global)', `Added to queue (${this.screenshotQueue.length}/${this.maxScreenshots}) - Alt+P to process`, 'success');
            
            return true;
            
        } catch (error) {
            console.error('❌ Screenshot capture failed:', error);
            
            if (error.name === 'NotAllowedError') {
                this.showNotification('❌ Permission Denied', 'Screen capture permission was denied', 'error');
            } else if (error.message.includes('timeout')) {
                this.showNotification('❌ Capture Timeout', 'Screenshot capture took too long', 'error');
            } else {
                this.showNotification('❌ Capture Failed', error.message, 'error');
            }
            
            return false;
        } finally {
            this.isCapturing = false;
        }
    }
    
    // Queue management methods
    addToQueue(screenshot) {
        this.screenshotQueue.push(screenshot);
        this.updateQueueUI();
        console.log('📸 Screenshot added to queue:', screenshot.id);
    }
    
    removeFromQueue(screenshotId) {
        this.screenshotQueue = this.screenshotQueue.filter(s => s.id !== screenshotId);
        this.updateQueueUI();
        console.log('🗑️ Screenshot removed from queue:', screenshotId);
    }
    
    clearQueue() {
        this.screenshotQueue = [];
        this.updateQueueUI();
        this.showNotification('🗑️ Queue Cleared', 'All screenshots removed', 'warning');
        console.log('🗑️ Screenshot queue cleared');
    }
    
    updateQueueUI() {
        const queueGrid = document.getElementById('queue-grid');
        const processBtn = document.getElementById('process-queue-btn');
        const queueTitle = document.querySelector('.queue-title');
        
        if (!queueGrid || !processBtn) return;
        
        // Update title to show current vision model
        if (queueTitle && this.visionConfig) {
            const currentProvider = window.appState?.visionMode?.currentVisionProvider || 'primary';
            const providerType = currentProvider === 'primary' ? '1°' : '2°';
            queueTitle.textContent = `📸 Vision Queue (${providerType} ${this.visionConfig.model})`;
        }
        
        // Update process button
        processBtn.textContent = `Process (${this.screenshotQueue.length})`;
        processBtn.disabled = this.screenshotQueue.length === 0 || !this.visionConfig;
        
        // Update grid
        queueGrid.innerHTML = '';
        
        this.screenshotQueue.forEach(screenshot => {
            const item = document.createElement('div');
            item.className = 'screenshot-item';
            item.innerHTML = `
                <img src="${screenshot.dataUrl}" alt="Screenshot" class="screenshot-image">
                <button class="screenshot-remove" type="button" title="Remove screenshot">×</button>
                <div class="screenshot-info">
                    ${new Date(screenshot.timestamp).toLocaleTimeString()}
                    <br>${this.formatFileSize(screenshot.size)}
                </div>
            `;
            // Bind in JS rather than via an onclick attribute: keeps the numeric
            // id (removeFromQueue compares with !==, so a string would silently
            // never match) and drops the hidden dependency on a global.
            const removeBtn = item.querySelector('.screenshot-remove');
            if (removeBtn) {
                removeBtn.addEventListener('click', () => this.removeFromQueue(screenshot.id));
            }
            queueGrid.appendChild(item);
        });
    }
    
    formatFileSize(bytes) {
        if (bytes < 1024) return bytes + 'B';
        if (bytes < 1024 * 1024) return Math.round(bytes / 1024) + 'KB';
        return Math.round(bytes / (1024 * 1024)) + 'MB';
    }
    
    // Vision processing methods
    async processQueue() {
        if (this.screenshotQueue.length === 0) {
            this.showNotification('❌ No Screenshots', 'Take some screenshots first', 'error');
            return;
        }
        
        if (!this.visionConfig) {
            this.showNotification('❌ No Vision Model', 'Configure a vision model in settings', 'error');
            return;
        }
        
        const processBtn = document.getElementById('process-queue-btn');
        if (processBtn) {
            processBtn.disabled = true;
            processBtn.textContent = 'Processing...';
        }
        
        try {
            const screenshots = this.screenshotQueue.map(s => s.dataUrl);
            
            console.log('🔄 Processing comprehensive multi-screenshot analysis...');
            console.log(`📸 Analyzing ${screenshots.length} screenshots together as one complete problem`);
            console.log('🧠 Generating two distinct solution approaches with full implementations');
            
            // Send to vision processing service
            const result = await this.sendToVisionAI(screenshots);
            
            if (result.success) {
                // Note: Vision analysis display is handled by main.js WebSocket message handler
                // to avoid duplicate display. We just handle UI feedback here.
                
                // Clear queue after successful processing
                this.clearQueue();
                this.showNotification('✅ Comprehensive Analysis Complete', 
                    `${screenshots.length} screenshots analyzed with 2 solution approaches`, 'success');
            } else {
                this.showNotification('❌ Analysis Failed', result.error || 'Vision AI processing failed', 'error');
            }
            
        } catch (error) {
            console.error('❌ Vision processing error:', error);
            this.showNotification('❌ Processing Error', error.message, 'error');
        } finally {
            if (processBtn) {
                processBtn.disabled = false;
                processBtn.textContent = `Process (${this.screenshotQueue.length})`;
            }
        }
    }
    
    async sendToVisionAI(screenshots) {
        try {
            console.log(`🔍 Sending ${screenshots.length} screenshots for comprehensive analysis`);
            console.log('📝 Enhanced prompt for multi-screenshot analysis');
            
            const payload = {
                screenshots: screenshots,
                visionConfig: this.visionConfig,
                languages: this.programmingLanguages
            };
            
            // Send via WebSocket if available
            if (window.sendSocketMessage) {
                // Show processing status in conversation
                if (window.webSocketHandler && window.webSocketHandler.showVisionProcessingStatus) {
                    window.webSocketHandler.showVisionProcessingStatus(
                        screenshots.length,
                        this.visionConfig.provider,
                        this.visionConfig.model
                    );
                }
                
                window.sendSocketMessage('vision_analysis', payload);
                
                // Return a promise that resolves when we get the response
                return new Promise((resolve, reject) => {
                    const timeout = setTimeout(() => {
                        // Hide processing status on timeout
                        if (window.webSocketHandler && window.webSocketHandler.hideVisionProcessingStatus) {
                            window.webSocketHandler.hideVisionProcessingStatus();
                        }
                        reject(new Error('Vision analysis timeout (45s)'));
                    }, 45000); // Reduced to 45 seconds to match backend optimization
                    
                    // This would be handled by the WebSocket message handler
                    window.visionAnalysisResolver = (result) => {
                        clearTimeout(timeout);
                        console.log(`✅ Vision analysis resolver called with result:`, result.success ? 'SUCCESS' : 'FAILED');
                        resolve(result);
                    };
                });
            } else {
                throw new Error('WebSocket not available - please ensure interview is active');
            }
            
        } catch (error) {
            console.error('❌ Vision AI request failed:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }
    
    // UI methods
    showVisionMode(isActive) {
        if (isActive) {
            this.insertQueueUI();
            const queueElement = document.getElementById('screenshot-queue');
            if (queueElement) {
                queueElement.classList.remove('hidden');
            }
            
            this.showVisionModeIndicator();
        } else {
            const queueElement = document.getElementById('screenshot-queue');
            if (queueElement) {
                queueElement.classList.add('hidden');
            }
            
            this.hideVisionModeIndicator();
        }
    }
    
    showVisionModeIndicator() {
        // Remove existing indicator
        this.hideVisionModeIndicator();
        
        const indicator = document.createElement('div');
        indicator.id = 'vision-mode-indicator';
        indicator.className = 'vision-mode-indicator';
        indicator.innerHTML = `
            <div class="vision-mode-content">
                <h3>👁️ Vision Mode Active (Global)</h3>
                <p>Ready to capture and analyze screenshots anywhere!</p>
                <div class="vision-hotkeys">
                    <div class="vision-hotkey">
                        <kbd>Alt+S</kbd>
                        <span>Capture</span>
                    </div>
                    <div class="vision-hotkey">
                        <kbd>Alt+P</kbd>
                        <span>Process</span>
                    </div>
                    <div class="vision-hotkey">
                        <kbd>Alt+T</kbd>
                        <span>Switch Model</span>
                    </div>
                    <div class="vision-hotkey">
                        <kbd>Alt+V</kbd>
                        <span>Exit Vision</span>
                    </div>
                </div>
                <p style="font-size: 11px; opacity: 0.8; margin-top: 10px;">
                    🌍 Works globally - no need to focus this app!
                </p>
            </div>
        `;
        
        document.body.appendChild(indicator);
        
        // Auto-hide after 4 seconds (bit longer for global message)
        setTimeout(() => {
            this.hideVisionModeIndicator();
        }, 4000);
    }
    
    hideVisionModeIndicator() {
        const indicator = document.getElementById('vision-mode-indicator');
        if (indicator) {
            indicator.remove();
        }
    }
    
    showNotification(title, message, type = 'info') {
        // Remove existing notification
        const existing = document.getElementById('capture-notification');
        if (existing) existing.remove();
        
        const notification = document.createElement('div');
        notification.id = 'capture-notification';
        notification.className = `capture-notification ${type}`;
        notification.innerHTML = `
            <div style="font-weight: 600; margin-bottom: 4px;">${title}</div>
            <div style="font-size: 12px; opacity: 0.8;">${message}</div>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-hide after 3 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 3000);
    }
    
    // Public API methods
    getQueueStatus() {
        return {
            count: this.screenshotQueue.length,
            maxCount: this.maxScreenshots,
            totalSize: this.screenshotQueue.reduce((sum, s) => sum + s.size, 0),
            isConfigured: !!this.visionConfig
        };
    }
    
    isReady() {
        return !!this.visionConfig && this.programmingLanguages.length > 0;
    }
}

// Create global instance
const screenshotService = new ScreenshotService();

// Make it globally accessible
window.screenshotService = screenshotService;

export default screenshotService; 