// Live Interview Interface Module (Main Coordinator)
import { devLog, isDev } from './config.js';
import { LiveStreaming } from './live-streaming.js';
import { LiveControls } from './live-controls.js';
import muteManager from './mute-manager.js';
import { StreamingMarkdownParser } from './streaming-markdown-parser.js';

class LiveInterviewUI {
    constructor() {
        this.conversationStream = null;
        this.activityIndicator = null;
        this.endButton = null;
        this.resetButton = null;
        this.muteButton = null;
        this.currentInterviewerElement = null; // Track interviewer message separately
        this.currentCandidateElement = null; // Track candidate message separately
        this.currentAIElement = null; // Track AI message separately
        this.isStreaming = false;
        this.eventsInitialized = false;
        
        // Enhanced smart scroll management
        this.scrollState = {
            mode: 'live_bottom',           // 'live_bottom', 'ai_start', 'user_reading'
            userReadingMode: false,        // User has intentionally scrolled up to read
            lastUserScrollTime: 0,         // When user last scrolled
            lastUserScrollDirection: 'down', // 'up' or 'down'
            consecutiveUpScrolls: 0,       // Count of consecutive up scrolls (indicates intent)
            aiResponseStartElement: null,  // Reference to current AI response element
            isLiveSpeaking: false,         // Whether someone is currently speaking
            lastScrollPosition: 0,         // Track scroll position changes
            isNearBottom: true,            // Is the scroll position near the bottom?
            bottomThreshold: 100,          // Pixels from bottom to consider "near bottom"
            readingThreshold: 200,         // Pixels scrolled up to consider "reading mode"
            newContentPending: false,      // New content arrived while user is reading
            resumeScrollButton: null,      // Reference to resume button
        };
        
        // Initialize modules
        this.streaming = new LiveStreaming({
            enableStreaming: true,
            streamingSpeed: 15,
            aiStreamingSpeed: 5
        });
        
        this.controls = new LiveControls();
        
        // Initialize real-time markdown parser
        this.markdownParser = new StreamingMarkdownParser();
        
        // Enable thinking content filter by default
        this.thinkingFilterEnabled = true;
    }

    // Initialize elements
    init() {
        this.conversationStream = document.getElementById('conversation-stream');
        this.activityIndicator = document.getElementById('activity-indicator');
        this.endButton = document.getElementById('end-interview-btn');
        this.resetButton = document.getElementById('reset-interview-btn');
        this.muteButton = document.getElementById('mute-btn');
        
        // Listen to the mute manager for state changes
        muteManager.on('stateChange', (status) => this.handleMuteStateChange(status));
        
        this.setupEventListeners();
    }

    setupEventListeners() {
        if (this.eventsInitialized) return;

        if (this.endButton) {
            this.endButton.addEventListener('click', () => this.endInterview());
        }

        if (this.resetButton) {
            this.resetButton.addEventListener('click', () => this.resetInterview());
        }
        
        if (this.muteButton) {
            this.muteButton.addEventListener('click', () => this.toggleMute());
        }
        
        // Setup smart scroll detection
        this.setupSmartScroll();
        
        // Setup keyboard shortcuts for scroll control
        this.setupScrollKeyboardShortcuts();
        
        this.eventsInitialized = true;
    }

    setupSmartScroll() {
        if (!this.conversationStream) return;

        this.conversationStream.addEventListener('scroll', () => {
            this.handleScrollEvent();
        });

        // Track user scroll intent via wheel events
        this.conversationStream.addEventListener('wheel', (e) => {
            this.handleWheelEvent(e);
        }, { passive: true });

        // Create resume scroll button (initially hidden)
        this.createResumeScrollButton();
    }

    handleScrollEvent() {
        const { scrollTop, scrollHeight, clientHeight } = this.conversationStream;
        const currentPosition = scrollTop;
        const maxScrollTop = scrollHeight - clientHeight;
        
        // Determine scroll direction
        const direction = currentPosition > this.scrollState.lastScrollPosition ? 'down' : 'up';
        
        // Update state
        this.scrollState.lastScrollPosition = currentPosition;
        this.scrollState.lastUserScrollTime = Date.now();
        this.scrollState.isNearBottom = currentPosition >= maxScrollTop - this.scrollState.bottomThreshold;
        
        // Track scroll direction changes
        if (direction !== this.scrollState.lastUserScrollDirection) {
            this.scrollState.consecutiveUpScrolls = direction === 'up' ? 1 : 0;
        } else if (direction === 'up') {
            this.scrollState.consecutiveUpScrolls++;
        }
        
        this.scrollState.lastUserScrollDirection = direction;
        
        // Determine if user is intentionally reading (scrolled up significantly)
        const distanceFromBottom = maxScrollTop - currentPosition;
        const wasInReadingMode = this.scrollState.userReadingMode;
        
        if (distanceFromBottom > this.scrollState.readingThreshold && this.scrollState.consecutiveUpScrolls >= 2) {
            // User has scrolled up intentionally (multiple up scrolls + significant distance)
            this.enterReadingMode();
        } else if (this.scrollState.isNearBottom && this.scrollState.userReadingMode) {
            // User has returned to bottom - exit reading mode
            this.exitReadingMode();
        }
        
    }

    handleWheelEvent(e) {
        // Additional intent detection: rapid up scrolls indicate reading intent
        if (e.deltaY < 0) { // Scrolling up
            this.scrollState.consecutiveUpScrolls++;
        } else {
            this.scrollState.consecutiveUpScrolls = 0;
        }
    }

    enterReadingMode() {
        if (!this.scrollState.userReadingMode) {
            this.scrollState.userReadingMode = true;
            this.scrollState.mode = 'user_reading';
            console.log('📚 User reading mode activated - auto-scroll paused');
            this.showResumeScrollButton();
        }
    }
    
    exitReadingMode() {
        if (this.scrollState.userReadingMode) {
            this.scrollState.userReadingMode = false;
            this.scrollState.newContentPending = false;
            this.setScrollMode('live_bottom');
            this.hideResumeScrollButton();
            console.log('📜 User returned to bottom - auto-scroll resumed');
        }
    }

    createResumeScrollButton() {
        // Inject CSS for the button if not already present
        if (!document.getElementById('resume-scroll-styles')) {
            const style = document.createElement('style');
            style.id = 'resume-scroll-styles';
            style.textContent = `
                .resume-scroll-btn {
                    position: fixed;
                    bottom: 30px;
                    right: 20px;
                    z-index: 1000;
                    background: rgba(255, 255, 255, 0.8);
                    color: rgb(0, 0, 0);;
                    border: none;
                    border-radius: 50%;
                    width: 32px;
                    height: 32px;
                    font-size: 14px;
                    font-weight:700;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    backdrop-filter: blur(10px);
                    transition: all 0.2s ease;
                    transform: translateY(0);
                    opacity: 0.4;
                    line-height: 1;
                }
                
                .resume-scroll-btn.hidden {
                    transform: translateY(50px) scale(0.8);
                    opacity: 0;
                    pointer-events: none;
                }
                
                .resume-scroll-btn:hover {
                    background: rgba(40, 40, 40, 0.8);
                    color: #fff;
                    opacity: 0.9;
                    transform: scale(1.1);
                }
                
                .resume-scroll-btn.has-new-content {
                    background: rgba(34, 139, 34, 0.7);
                    color: #fff;
                    opacity: 0.8;
                    animation: subtlePulse 3s infinite;
                }
                
                .resume-scroll-btn.has-new-content:hover {
                    background: rgba(34, 139, 34, 0.9);
                    opacity: 1;
                }
                
                @keyframes subtlePulse {
                    0%, 100% { 
                        opacity: 0.6;
                        transform: scale(1);
                    }
                    50% { 
                        opacity: 0.9;
                        transform: scale(1.05);
                    }
                }
            `;
            document.head.appendChild(style);
        }

        // Create a floating button that appears when user is in reading mode
        const button = document.createElement('button');
        button.className = 'resume-scroll-btn hidden';
        button.innerHTML = '↓';
        button.title = 'Resume auto-scroll (End key)';
        
        button.addEventListener('click', () => {
            this.resumeAutoScroll();
        });
        
        // Add to body (fixed positioning)
        document.body.appendChild(button);
        this.scrollState.resumeScrollButton = button;
    }

    showResumeScrollButton() {
        if (this.scrollState.resumeScrollButton) {
            this.scrollState.resumeScrollButton.classList.remove('hidden');
            
            // Update button based on whether new content is pending
            if (this.scrollState.newContentPending) {
                this.scrollState.resumeScrollButton.innerHTML = '•';
                this.scrollState.resumeScrollButton.title = 'New content available - Resume auto-scroll (End key)';
                this.scrollState.resumeScrollButton.classList.add('has-new-content');
            }
        }
    }

    hideResumeScrollButton() {
        if (this.scrollState.resumeScrollButton) {
            this.scrollState.resumeScrollButton.classList.add('hidden');
            this.scrollState.resumeScrollButton.classList.remove('has-new-content');
            this.scrollState.resumeScrollButton.innerHTML = '↓';
            this.scrollState.resumeScrollButton.title = 'Resume auto-scroll (End key)';
        }
    }

    resumeAutoScroll() {
        // Manually resume auto-scroll and go to bottom
        this.exitReadingMode();
        this.scrollToBottom();
        console.log('🎯 User manually resumed auto-scroll');
    }

    setupScrollKeyboardShortcuts() {
        // Add keyboard shortcuts for scroll control
        document.addEventListener('keydown', (e) => {
            // Only handle shortcuts when not typing in an input
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                return;
            }

            // Ctrl+End or End: Resume auto-scroll / go to bottom
            if (e.key === 'End') {
                e.preventDefault();
                this.resumeAutoScroll();
            }
            
            // Ctrl+Home or Home: Enter reading mode and go to top
            else if (e.key === 'Home') {
                e.preventDefault();
                this.enterReadingMode();
                if (this.conversationStream) {
                    this.conversationStream.scrollTop = 0;
                }
            }
            
            // Escape: Toggle reading mode
            else if (e.key === 'Escape' && !e.ctrlKey && !e.altKey) {
                e.preventDefault();
                if (this.scrollState.userReadingMode) {
                    this.resumeAutoScroll();
                } else {
                    this.enterReadingMode();
                }
            }
        });
    }

    // Show activity indicator
    showActivity(text = 'Listening...') {
        if (!this.activityIndicator) return;

        const status = muteManager.getMuteStatus();
        let indicatorText = text;
        
        if (status.universal) {
            indicatorText = '⏸️ System Paused - Press Alt+U to resume';
            this.activityIndicator.classList.add('paused');
        } else if (status.microphone) {
            indicatorText = '🔇 Microphone Muted - Press Alt+M to unmute';
            this.activityIndicator.classList.remove('paused');
        } else {
            this.activityIndicator.classList.remove('paused');
        }

        this.activityIndicator.querySelector('span').textContent = indicatorText;
        this.activityIndicator.classList.add('show');
    }

    hideActivity() {
        if (this.activityIndicator) {
            this.activityIndicator.classList.remove('show');
        }
    }

    // Add interviewer question
    addInterviewerQuestion(question, isInterim = false) {
        // Live speech is high priority - but respect reading mode
        if (!this.scrollState.userReadingMode) {
            this.setScrollMode('live_bottom');
        }
        this.scrollState.isLiveSpeaking = true;

        if (isInterim) {
            if (!this.currentInterviewerElement) {
                this.currentInterviewerElement = this.createMessageElement('', 'interviewer');
                this.conversationStream.appendChild(this.currentInterviewerElement);
                this.updateEmptyState();
            }
            this.updateInterviewerMessage(this.currentInterviewerElement.querySelector('.streaming-text').textContent + ' ' + question);
        } else {
            if (this.currentInterviewerElement) {
                this.finalizeInterviewerMessage(question);
            } else {
                this.addMessage(question, 'interviewer');
            }
            this.hideActivity();
            this.updateEmptyState();
            this.scrollState.isLiveSpeaking = false;
        }
        
        // For live speech, be more aggressive about scrolling (but still respect reading mode)
        if (!this.scrollState.userReadingMode) {
            this.scrollToBottom();
        } else {
            // Notify user of new content if they're reading
            this.scrollState.newContentPending = true;
            this.showResumeScrollButton();
        }
    }

    // Add candidate transcript (for when diarization is disabled - all speech from candidate)
    addCandidateTranscript(transcript, isInterim = false) {
        // Live speech is high priority - but respect reading mode
        if (!this.scrollState.userReadingMode) {
            this.setScrollMode('live_bottom');
        }
        this.scrollState.isLiveSpeaking = true;

        if (isInterim) {
            if (!this.currentCandidateElement) {
                this.currentCandidateElement = this.createMessageElement('', 'candidate');
                this.conversationStream.appendChild(this.currentCandidateElement);
                this.updateEmptyState();
            }
            this.updateCandidateMessage(this.currentCandidateElement.querySelector('.streaming-text').textContent + ' ' + transcript);
        } else {
            if (this.currentCandidateElement) {
                this.finalizeCandidateMessage(transcript);
            } else {
                this.addMessage(transcript, 'candidate');
            }
            this.hideActivity();
            this.updateEmptyState();
            this.scrollState.isLiveSpeaking = false;
        }
        
        // For live speech, be more aggressive about scrolling (but still respect reading mode)
        if (!this.scrollState.userReadingMode) {
            this.scrollToBottom();
        } else {
            // Notify user of new content if they're reading
            this.scrollState.newContentPending = true;
            this.showResumeScrollButton();
        }
    }

    // Add AI response (legacy method)
    addAIResponse(response, metadata = {}) {
        // Filter thinking content from response
        const filteredResponse = this.filterThinkingContent(response);
        
        this.currentAIElement = this.createMessageElement(filteredResponse, 'ai-response');
        this.conversationStream.appendChild(this.currentAIElement);

        // Use ai_streaming mode to prevent forced scrolling
        this.setScrollMode('ai_streaming', this.currentAIElement);

        this.startStreaming(this.currentAIElement, filteredResponse, true, () => {
            // Add metadata after streaming completes
            this.addResponseMetadata(this.currentAIElement, metadata);
            
            // On completion, stay in current position - don't force scroll
            // Only set to live_bottom if user is already at bottom
            if (this.isUserNearBottom()) {
                this.setScrollMode('live_bottom');
            } else {
                this.setScrollMode('ai_static');
            }
        });
        
        this.hideActivity();
        this.updateEmptyState();
    }

    // Add vision analysis response
    addVisionAnalysis(analysis, metadata = {}) {
        console.log('🎭 LiveInterviewUI.addVisionAnalysis called:', {
            analysisLength: analysis?.length || 0,
            provider: metadata?.provider,
            model: metadata?.model,
            screenshotCount: metadata?.screenshotCount
        });
        
        // Filter thinking content from analysis
        const filteredAnalysis = this.filterThinkingContent(analysis);
        
        const visionElement = this.createVisionAnalysisElement(filteredAnalysis, metadata);
        this.conversationStream.appendChild(visionElement);

        // Use ai_streaming mode to prevent forced scrolling
        this.setScrollMode('ai_streaming', visionElement);

        this.startStreaming(visionElement, filteredAnalysis, true, () => {
            // On completion, stay in current position - don't force scroll
            // Only set to live_bottom if user is already at bottom
            if (this.isUserNearBottom()) {
                this.setScrollMode('live_bottom');
            } else {
                this.setScrollMode('ai_static');
            }
            console.log('🎭 Vision analysis streaming completed');
        });
        
        this.hideActivity();
        this.updateEmptyState();
    }

    // Add message to conversation
    addMessage(content, type) {
        // Filter thinking content from all messages
        const filteredContent = this.filterThinkingContent(content);
        
        const messageElement = this.createMessageElement(filteredContent, type);
        this.conversationStream.appendChild(messageElement);
        this.startStreaming(messageElement, filteredContent);
        
        // Only auto-scroll if user is near bottom, otherwise respect their position
        if (this.isUserNearBottom()) {
            this.scrollToBottom();
        }
        
        this.updateEmptyState();
    }

    // Create message element
    createMessageElement(content, type) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        
        const label = document.createElement('span');
        label.className = 'label';
        
        // Set label based on type
        switch (type) {
            case 'interviewer':
                label.textContent = '🎤 Interviewer';
                break;
            case 'candidate':
                label.textContent = '👤 Candidate';
                break;
            default:
                label.textContent = '🤖 AI Assistant';
                break;
        }
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'streaming-text';
        
        messageDiv.appendChild(label);
        messageDiv.appendChild(contentDiv);
        
        return messageDiv;
    }

    // Create vision analysis element with enhanced styling
    createVisionAnalysisElement(content, metadata = {}) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message ai-response vision-analysis';
        
        // Create header with vision-specific information
        const headerDiv = document.createElement('div');
        headerDiv.className = 'vision-header';
        
        const label = document.createElement('span');
        label.className = 'label';
        label.innerHTML = '👁️ Vision AI Analysis';
        
        const metaInfo = document.createElement('div');
        metaInfo.className = 'vision-meta';
        
        let metaText = '';
        if (metadata.provider && metadata.model) {
            metaText += `${metadata.provider} - ${metadata.model}`;
        }
        if (metadata.screenshotCount) {
            metaText += ` • ${metadata.screenshotCount} screenshot${metadata.screenshotCount > 1 ? 's' : ''}`;
        }
        if (metadata.languages && metadata.languages.length > 0) {
            metaText += ` • ${metadata.languages.join(', ')}`;
        }
        
        metaInfo.textContent = metaText;
        
        headerDiv.appendChild(label);
        headerDiv.appendChild(metaInfo);
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'streaming-text vision-content';
        
        messageDiv.appendChild(headerDiv);
        messageDiv.appendChild(contentDiv);
        
        // Add vision-specific styling if not already present
        this.addVisionStyles();
        
        return messageDiv;
    }

    // Add CSS styles for vision analysis elements
    addVisionStyles() {
        if (!document.getElementById('vision-analysis-styles')) {
            const style = document.createElement('style');
            style.id = 'vision-analysis-styles';
            style.textContent = `
                .message.vision-analysis {
                    border-left: 4px solid #6366f1;
                    background: linear-gradient(135deg, rgba(99, 102, 241, 0.05) 0%, rgba(139, 92, 246, 0.05) 100%);
                }
                
                .vision-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 12px;
                    padding-bottom: 8px;
                    border-bottom: 1px solid rgba(99, 102, 241, 0.2);
                }
                
                .vision-header .label {
                    color: #6366f1;
                    font-weight: 600;
                    font-size: 14px;
                }
                
                .vision-meta {
                    font-size: 11px;
                    color: #64748b;
                    font-weight: 500;
                    text-align: right;
                }
                
                .vision-content {
                    line-height: 1.6;
                }
                
                .vision-content h1,
                .vision-content h2,
                .vision-content h3 {
                    color: #6366f1;
                    margin-top: 20px;
                    margin-bottom: 10px;
                }
                
                .vision-content h1 {
                    font-size: 18px;
                    border-bottom: 2px solid rgba(99, 102, 241, 0.3);
                    padding-bottom: 5px;
                }
                
                .vision-content h2 {
                    font-size: 16px;
                }
                
                .vision-content h3 {
                    font-size: 14px;
                }
                
                .vision-content code {
                    background: rgba(99, 102, 241, 0.1);
                    padding: 2px 6px;
                    border-radius: 3px;
                    font-family: 'Fira Code', 'Monaco', 'Consolas', monospace;
                    font-size: 13px;
                }
                
                .vision-content pre {
                    background: rgba(15, 23, 42, 0.95);
                    border: 1px solid rgba(99, 102, 241, 0.3);
                    border-radius: 6px;
                    padding: 16px;
                    margin: 12px 0;
                    overflow-x: auto;
                    position: relative;
                }
                
                .vision-content pre code {
                    background: none;
                    padding: 0;
                    color: #e2e8f0;
                    font-size: 13px;
                    line-height: 1.5;
                }
                
                .vision-content ul,
                .vision-content ol {
                    margin: 12px 0;
                    padding-left: 20px;
                }
                
                .vision-content li {
                    margin: 6px 0;
                    line-height: 1.5;
                }
                
                .vision-content strong {
                    color: #6366f1;
                    font-weight: 600;
                }
                
                .vision-content blockquote {
                    border-left: 3px solid #6366f1;
                    margin: 16px 0;
                    padding: 12px 16px;
                    background: rgba(99, 102, 241, 0.05);
                    border-radius: 0 4px 4px 0;
                }
            `;
            document.head.appendChild(style);
        }
        
        // Add streaming styles if not present
        this.addStreamingStyles();
    }

    addStreamingStyles() {
        if (!document.getElementById('streaming-response-styles')) {
            const style = document.createElement('style');
            style.id = 'streaming-response-styles';
            style.textContent = `
                .streaming-indicator {
                    color: #3b82f6;
                    font-weight: 500;
                    animation: pulse 1.5s ease-in-out infinite;
                    cursor: default !important;
                }
                
                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.5; }
                }
                
                /* Fix potential cursor/blinking issues */
                .streaming-text {
                    caret-color: transparent !important;
                    cursor: default !important;
                }
                
                .streaming-text * {
                    caret-color: transparent !important;
                    cursor: default !important;
                }
                
                /* Prevent text selection during streaming */
                .message.ai-response:not(.complete) .streaming-text {
                    user-select: none;
                    -webkit-user-select: none;
                    -moz-user-select: none;
                    -ms-user-select: none;
                }
                
                .response-meta {
                    font-size: 9px;
                    margin-top: 6px;
                    padding: 2px 6px;
                    border-radius: 2px;
                    opacity: 0.6;
                    display: inline-block;
                    margin-right: 6px;
                }
                
                .response-meta.model-info {
                    background: rgba(99, 102, 241, 0.08);
                    color: #6366f1;
                    border: 1px solid rgba(99, 102, 241, 0.2);
                }
                
                .response-meta.fallback-info {
                    background: rgba(245, 158, 11, 0.08);
                    color: #d97706;
                    border: 1px solid rgba(245, 158, 11, 0.2);
                }
                
                .response-meta.error-info {
                    background: rgba(239, 68, 68, 0.08);
                    color: #dc2626;
                    border: 1px solid rgba(239, 68, 68, 0.2);
                }
                
                /* Real-time markdown pending content */
                .pending-text {
                    opacity: 0.7;
                    color: rgba(255, 255, 255, 0.8);
                    font-family: inherit;
                }
                
                /* Ensure pending elements don't interfere with styling */
                .pending-text .markdown-header,
                .pending-text .markdown-list,
                .pending-text .markdown-paragraph {
                    animation: none;
                }
                
                /* Code block styling for streaming - Compact & Professional */
                .code-block-container {
                    margin: 0.75rem 0;
                    border-radius: 6px;
                    overflow: hidden;
                    background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%);
                    border: 1px solid rgba(74, 85, 104, 0.4);
                    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
                    position: relative;
                }
                
                .code-block-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 0.3rem 0.6rem;
                    background: rgba(45, 55, 72, 0.8);
                    border-bottom: 1px solid rgba(74, 85, 104, 0.3);
                    min-height: 26px;
                }
                
                .code-language {
                    font-size: 0.7rem;
                    color: #a0aec0;
                    font-weight: 500;
                    text-transform: uppercase;
                    letter-spacing: 0.8px;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                }
                
                .copy-button {
                    background: rgba(113, 128, 150, 0.08);
                    border: 1px solid rgba(113, 128, 150, 0.2);
                    color: #718096;
                    padding: 0.1rem 0.25rem;
                    border-radius: 2px;
                    font-size: 0.55rem;
                    cursor: pointer;
                    transition: all 0.15s ease;
                    font-weight: 400;
                    display: flex;
                    align-items: center;
                    height: 16px;
                    min-width: 28px;
                    justify-content: center;
                    opacity: 0.6;
                }
                
                .copy-button:hover {
                    background: rgba(113, 128, 150, 0.15);
                    color: #a0aec0;
                    border-color: rgba(113, 128, 150, 0.35);
                    opacity: 0.9;
                    transform: none;
                }
                
                .copy-button:active {
                    background: rgba(72, 187, 120, 0.15);
                    color: #68d391;
                    border-color: rgba(72, 187, 120, 0.3);
                    opacity: 1;
                }
                
                .code-block {
                    margin: 0;
                    padding: 0.75rem;
                    background: #1a202c !important;
                    font-family: 'JetBrains Mono', 'Fira Code', 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
                    font-size: 0.85rem;
                    line-height: 1.4;
                    color: #e2e8f0;
                    overflow-x: auto;
                    white-space: pre;
                    border: none;
                }
                
                .code-block code {
                    color: inherit;
                    background: none !important;
                    padding: 0;
                    border: none;
                    font-family: inherit;
                    font-size: inherit;
                    line-height: inherit;
                }
                
                /* Subtle scroll styling for code blocks */
                .code-block::-webkit-scrollbar {
                    height: 8px;
                }
                
                .code-block::-webkit-scrollbar-track {
                    background: rgba(45, 55, 72, 0.5);
                }
                
                .code-block::-webkit-scrollbar-thumb {
                    background: rgba(113, 128, 150, 0.3);
                    border-radius: 4px;
                }
                
                .code-block::-webkit-scrollbar-thumb:hover {
                    background: rgba(113, 128, 150, 0.5);
                }
            `;
            document.head.appendChild(style);
        }
    }

    // Start streaming animation (delegated to streaming module)
    startStreaming(messageElement, content, isAI = false, onCompletion = null) {
        const contentDiv = messageElement.querySelector('.streaming-text');
        const speed = isAI ? this.streaming.config.aiStreamingSpeed : this.streaming.config.streamingSpeed;

        this.isStreaming = true;

        const scrollCallback = () => {
            // Only auto-scroll during live speech streaming, not during AI responses
            if (this.scrollState.mode === 'live_bottom') {
                this.scrollToBottom();
            }
            // Don't scroll during ai_streaming or ai_static modes
        };

        this.streaming.streamContent(contentDiv, content, speed, scrollCallback).then(() => {
            messageElement.classList.add('complete');
            this.isStreaming = false;
            if (onCompletion) {
                onCompletion();
            }
        });
    }

    // Update interviewer message (for interim results)
    updateInterviewerMessage(content) {
        if (this.currentInterviewerElement) {
            const contentDiv = this.currentInterviewerElement.querySelector('.streaming-text');
            
            // Mark as interim to hide typing cursor
            this.currentInterviewerElement.classList.add('interim');
            
            // Clear and update instantly using streaming module
            contentDiv.innerHTML = '';
            this.streaming.displayInstantText(contentDiv, content);
        }
    }

    // Finalize interviewer message (for final results)
    finalizeInterviewerMessage(content) {
        if (this.currentInterviewerElement) {
            // Remove interim class to show typing animation for final result
            this.currentInterviewerElement.classList.remove('interim');
            
            const contentDiv = this.currentInterviewerElement.querySelector('.streaming-text');
            contentDiv.innerHTML = '';
            
            // Use streaming module for final content
            this.streaming.streamContent(contentDiv, content, this.streaming.config.streamingSpeed).then(() => {
                if (this.currentInterviewerElement) {
                    this.currentInterviewerElement.classList.add('complete');
                }
            });
            
            // Clear the reference since this is final
            this.currentInterviewerElement = null;
            
            // Reset auto-scroll for new response
            this.autoScrollEnabled = true;
        }
    }

    // Update candidate message (for interim results)
    updateCandidateMessage(content) {
        if (this.currentCandidateElement) {
            const contentDiv = this.currentCandidateElement.querySelector('.streaming-text');
            
            // Mark as interim to hide typing cursor
            this.currentCandidateElement.classList.add('interim');
            
            // Clear and update instantly using streaming module
            contentDiv.innerHTML = '';
            this.streaming.displayInstantText(contentDiv, content);
        }
    }

    // Finalize candidate message (for final results)
    finalizeCandidateMessage(content) {
        if (this.currentCandidateElement) {
            // Remove interim class to show typing animation for final result
            this.currentCandidateElement.classList.remove('interim');
            
            const contentDiv = this.currentCandidateElement.querySelector('.streaming-text');
            contentDiv.innerHTML = '';
            
            // Use streaming module for final content
            this.streaming.streamContent(contentDiv, content, this.streaming.config.streamingSpeed).then(() => {
                if (this.currentCandidateElement) {
                    this.currentCandidateElement.classList.add('complete');
                }
            });
            
            // Clear the reference since this is final
            this.currentCandidateElement = null;
            
            // Reset auto-scroll for new response
            this.autoScrollEnabled = true;
        }
    }

    // --- New Smart Scrolling System ---

    setScrollMode(mode, targetElement = null) {
        this.scrollState.mode = mode;

        switch (mode) {
            case 'live_bottom':
                this.scrollToBottom();
                break;
            case 'ai_start':
                if (targetElement) {
                    this.scrollState.aiResponseStartElement = targetElement;
                    this.scrollToAiResponseStart();
                }
                break;
            case 'user_reading':
                // In this mode, we don't trigger any automatic scrolling
                // but we mark that new content is pending
                this.scrollState.newContentPending = true;
                this.showResumeScrollButton();
                break;
            case 'ai_streaming':
                // ai_streaming mode doesn't auto-scroll - lets user stay where they are
                // Just store the element reference for potential future use
                if (targetElement) {
                    this.scrollState.aiResponseStartElement = targetElement;
                }
                break;
            case 'ai_static':
                // ai_static mode doesn't auto-scroll - AI response completed, maintain position
                break;
        }
    }

    scrollToBottom() {
        if (this.scrollState.userReadingMode) {
            // Don't interrupt user reading - just mark that new content is available
            this.scrollState.newContentPending = true;
            this.showResumeScrollButton();
            return;
        }
        if (this.conversationStream) {
            this.conversationStream.scrollTop = this.conversationStream.scrollHeight;
        }
    }

    scrollToAiResponseStart() {
        if (this.scrollState.userReadingMode) {
            // Don't interrupt user reading - just mark that new content is available
            this.scrollState.newContentPending = true;
            this.showResumeScrollButton();
            return;
        }
        if (this.scrollState.aiResponseStartElement) {
            // A behavior passed to scrollIntoView wins over the CSS
            // scroll-behavior property, so the reduced-motion media query in
            // main.css cannot suppress this one. Check it here instead. This
            // fires on every AI response and animates the whole conversation
            // pane, making it the largest single movement in the overlay.
            const reduceMotion = window.matchMedia
                && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
            this.scrollState.aiResponseStartElement.scrollIntoView({
                behavior: reduceMotion ? 'auto' : 'smooth',
                block: 'start'
            });
        }
    }

    // Start real-time streaming AI response
    startStreamingAIResponse(metadata = {}) {
        console.log('🚀 Starting real-time AI streaming with markdown parsing...');
        
        // If there's an existing streaming element, finalize it first
        if (this.currentStreamingElement) {
            console.log('📝 Finalizing previous response before starting new one');
            this.finalizeStreamingResponse({ forceFinalize: true });
        }
        
        // Reset markdown parser for new response
        this.markdownParser.reset();
        
        // Create NEW AI response element for each response
        this.currentStreamingElement = this.createMessageElement('', 'ai-response');
        this.conversationStream.appendChild(this.currentStreamingElement);
        
        // Get content div for streaming
        this.currentStreamingContent = this.currentStreamingElement.querySelector('.streaming-text');
        
        // Add streaming indicator (no cursor to avoid blinking issues)
        this.currentStreamingContent.innerHTML = '<span class="streaming-indicator">🤖 Thinking...</span>';
        
        // Set scroll mode for real-time streaming
        this.setScrollMode('ai_streaming', this.currentStreamingElement);
        
        // Hide activity indicator
        this.hideActivity();
        this.updateEmptyState();
        
        console.log('✅ Real-time streaming with markdown parsing prepared for new response');
    }

    // Append streaming chunk with real-time markdown processing
    appendStreamingChunk(chunk) {
        if (!this.currentStreamingElement || !this.currentStreamingContent) {
            console.warn('⚠️ No active streaming element for chunk');
            return;
        }
        
        // Remove streaming indicator on first chunk
        const indicator = this.currentStreamingContent.querySelector('.streaming-indicator');
        if (indicator) {
            indicator.remove();
        }
        
        // Process chunk through real-time markdown parser first (don't filter individual chunks)
        // The markdown parser will handle the thinking content filtering at the buffer level
        const renderedHTML = this.markdownParser.processChunk(chunk);
        
        // Update content with rendered HTML
        this.currentStreamingContent.innerHTML = renderedHTML;
        
        // Auto-scroll if user is near bottom
        if (this.isUserNearBottom()) {
            this.scrollToBottom();
        }
    }

    // Finalize streaming response
    finalizeStreamingResponse(metadata = {}) {
        console.log('✅ Finalizing real-time streaming...');
        
        if (this.currentStreamingElement) {
            // Mark as complete (this will re-enable text selection via CSS)
            this.currentStreamingElement.classList.add('complete');
            
            // Only process content if not force finalizing
            if (!metadata.forceFinalize && this.currentStreamingContent) {
                // Finalize the markdown parser to process any remaining content
                // The markdown parser already handles thinking content filtering
                const finalContent = this.markdownParser.finalize();
                this.currentStreamingContent.innerHTML = finalContent;
                console.log('📝 Real-time markdown parsing finalized with thinking content filtering');
            } else if (metadata.forceFinalize) {
                // For force finalize, just mark as complete with current content
                console.log('🔄 Force finalizing previous response to start new one');
            }
            
            // Always show metadata for completed responses (unless force finalizing)
            if (!metadata.forceFinalize) {
                this.addResponseMetadata(this.currentStreamingElement, metadata);
            }
            
            // Reset scroll mode
            if (this.isUserNearBottom()) {
                this.setScrollMode('live_bottom');
            } else {
                this.setScrollMode('ai_static');
            }
            
            if (metadata.forceFinalize) {
                console.log('🔄 Previous response force-finalized for new response');
            } else {
                console.log('🤖 Real-time AI streaming completed normally');
            }
            
            // Show listening indicator after response is complete
            this.showActivity('Listening...');

        } else {
            console.warn('⚠️ No streaming element to finalize');
        }
        
        // Clear streaming references to allow new responses
        this.currentStreamingElement = null;
        this.currentStreamingContent = null;
    }

    // Add response metadata (preset info, errors, etc.)
    addResponseMetadata(element, metadata) {
        if (!element) return;
        
        let metaHTML = '';
        
        // Always show model info in minimalistic way
        if (metadata.preset && metadata.preset.model) {
            const modelName = metadata.preset.model.length > 25 ? 
                metadata.preset.model.substring(0, 25) + '...' : 
                metadata.preset.model;
            metaHTML += `<div class="response-meta model-info">
                🧠 ${modelName}
            </div>`;
        }
        
        // Show fallback info if used
        if (metadata.fallback && metadata.fallback.fallback_used) {
            metaHTML += `<div class="response-meta fallback-info">
                🔄 Backup used
            </div>`;
        }
        
        // Show error info if present
        if (metadata.error) {
            metaHTML += `<div class="response-meta error-info">
                ⚠️ Error
            </div>`;
        }
        
        if (metaHTML) {
            element.insertAdjacentHTML('beforeend', metaHTML);
            console.log('📡 Metadata added:', metadata.preset?.model || 'Unknown model');
        }
    }

    // Filter thinking content helper
    filterThinkingContent(content) {
        if (!content || typeof content !== 'string') {
            return content;
        }
        
        // Check if thinking filter is enabled (default to true)
        if (this.thinkingFilterEnabled === false) {
            return content;
        }
        
        // Remove content between <think> and </think> tags (case insensitive, multiline)
        const thinkingRegex = /<think\s*>[\s\S]*?<\/think\s*>/gi;
        const originalLength = content.length;
        
        // Remove thinking content but preserve surrounding whitespace structure
        let filteredContent = content.replace(thinkingRegex, (match, offset, string) => {
            // Check if the thinking block is on its own line(s)
            const beforeMatch = string.substring(0, offset);
            const afterMatch = string.substring(offset + match.length);
            
            const beforeEndsWithNewline = beforeMatch.endsWith('\n') || beforeMatch.endsWith('\n\n');
            const afterStartsWithNewline = afterMatch.startsWith('\n') || afterMatch.startsWith('\n\n');
            
            // If the thinking block is on its own line, preserve one newline
            if (beforeEndsWithNewline && afterStartsWithNewline) {
                return '\n';
            }
            // If it's inline, just remove it
            return '';
        });
        
        // Only clean up excessive newlines (3 or more consecutive), preserve normal paragraph breaks
        filteredContent = filteredContent.replace(/\n{3,}/g, '\n\n');
        
        // Log if thinking content was filtered
        if (originalLength !== filteredContent.length) {
            console.log(`🧠 Filtered thinking content: ${originalLength} → ${filteredContent.length} chars`);
        }
        
        return filteredContent;
    }

    // Clear conversation
    clearConversation() {
        if (this.conversationStream) {
            this.conversationStream.innerHTML = '';
        }
        
        // Clear all references to prevent multiple elements
        this.currentInterviewerElement = null;
        this.currentCandidateElement = null;
        this.currentAIElement = null;
        this.currentStreamingElement = null;
        this.currentStreamingContent = null;
        this.isStreaming = false;
        
        // Reset markdown parser
        this.markdownParser.reset();
        
        this.updateEmptyState();
        console.log('🧹 Conversation cleared and all references reset');
    }

    // Update empty state class
    updateEmptyState() {
        if (!this.conversationStream) return;
        
        const messageCount = this.conversationStream.querySelectorAll('.message').length;
        if (messageCount === 0) {
            this.conversationStream.classList.add('no-messages');
        } else {
            this.conversationStream.classList.remove('no-messages');
        }
    }

    // Toggle microphone mute via the UI button
    toggleMute() {
        // The hotkey manager and mute manager now handle the logic.
        // This just needs to trigger the toggle.
        muteManager.toggleMicrophoneMute();
    }

    // Central handler for all mute state changes
    handleMuteStateChange(status) {
        this.updateMuteButton(status.microphone);
        this.showActivity(); // Re-evaluates the activity indicator text
    }

    // Update mute button appearance
    updateMuteButton(isMuted) {
        if (this.muteButton) {
            if (isMuted) {
                this.muteButton.classList.add('muted');
                this.muteButton.title = 'Unmute microphone input to app (Alt+M)';
            } else {
                this.muteButton.classList.remove('muted');
                this.muteButton.title = 'Mute microphone input to app (Alt+M)';
            }
        }
    }

    // End interview
    endInterview() {
        if (typeof window.endInterview === 'function') {
            window.endInterview();
        }
    }

    // Reset interview
    resetInterview() {
        if (typeof window.resetInterview === 'function') {
            window.resetInterview();
        }
    }

    // Initialize
    initialize() {
        this.clearConversation();
        this.showActivity('Listening...');
        this.controls.initialize(); // Initialize controls module
        this.updateEmptyState();
        
        // Set initial UI state from the mute manager
        const initialStatus = muteManager.getMuteStatus();
        this.updateMuteButton(initialStatus.microphone);
        console.log(`🎤 UI initialized with microphone ${initialStatus.microphone ? 'muted' : 'unmuted'}`);
        
        // Reset scroll state
        this.scrollState = {
            mode: 'live_bottom',
            userReadingMode: false,
            lastUserScrollTime: 0,
            lastUserScrollDirection: 'down',
            consecutiveUpScrolls: 0,
            aiResponseStartElement: null,
            isLiveSpeaking: false,
            lastScrollPosition: 0,
            isNearBottom: true,
            bottomThreshold: 100,
            readingThreshold: 200,
            newContentPending: false,
            resumeScrollButton: this.scrollState?.resumeScrollButton || null, // Preserve button reference
        };
        
        console.log('🎬 Live interview UI initialized');
    }

    // Get current configuration
    getConfig() {
        return {
            streaming: this.streaming.getConfig(),
            transparency: this.controls.getConfig()
        };
    }

    isUserNearBottom() {
        if (this.conversationStream) {
            const { scrollTop, scrollHeight, clientHeight } = this.conversationStream;
            const maxScrollTop = scrollHeight - clientHeight;
            return scrollTop >= maxScrollTop - this.scrollState.bottomThreshold;
        }
        return false;
    }

    // --- Transparency Control Methods ---
    // Add transparency methods to LiveInterviewUI for hotkey integration
    
    async setTransparency(level) {
        console.log(`🪟 Setting transparency level: ${level}`);
        
        // Handle both numeric (1,2,3) and string ("transparent","semi","opaque") levels
        // for compatibility with both hotkey systems and direct calls
        let targetMode;
        
        if (typeof level === 'number') {
            // Numeric levels from original hotkey system (Alt+1, Alt+2, Alt+3)
            switch(level) {
                case 1:
                    targetMode = 'transparent';
                    break;
                case 2:
                    targetMode = 'semi';
                    break;
                case 3:
                    targetMode = 'opaque';
                    break;
                default:
                    console.warn(`⚠️ Unknown numeric transparency level: ${level}`);
                    return false;
            }
        } else if (typeof level === 'string') {
            // String levels from global hotkey system
            targetMode = level.toLowerCase();
        } else {
            console.warn(`⚠️ Invalid transparency level type: ${typeof level}`);
            return false;
        }
        
        // Execute the appropriate transparency preset
        switch(targetMode) {
            case 'transparent':
                console.log('🪟 Setting transparent mode (40% opacity)');
                return await this.controls.setInterviewMode();
            case 'semi':
            case 'semi-transparent':
                console.log('🪟 Setting semi-transparent mode (70% opacity)');
                return await this.controls.setSemiTransparentMode();
            case 'opaque':
                console.log('🪟 Setting opaque mode (100% opacity)');
                return await this.controls.setOpaqueMode();
            default:
                console.warn(`⚠️ Unknown transparency mode: ${targetMode}`);
                return false;
        }
    }

    // Expose other transparency methods for consistency
    async setWindowTransparency(transparency) {
        return await this.controls.setWindowTransparency(transparency);
    }

    async setWindowTransparencyPercent(percent) {
        return await this.controls.setWindowTransparencyPercent(percent);
    }

    async setInterviewMode() {
        return await this.controls.setInterviewMode();
    }

    async setSemiTransparentMode() {
        return await this.controls.setSemiTransparentMode();
    }

    async setOpaqueMode() {
        return await this.controls.setOpaqueMode();
    }
}

// Create global instance
window.liveInterviewUI = new LiveInterviewUI();

// Add global configuration functions for easy control
window.setInterviewStreaming = (enabled) => {
    window.liveInterviewUI.streaming.setStreamingEnabled(enabled);
    console.log(`🎬 Streaming ${enabled ? 'enabled' : 'disabled'}`);
};

window.setInterviewSpeed = (speed) => {
    window.liveInterviewUI.streaming.setStreamingSpeed(speed);
    console.log(`⚡ Interviewer streaming speed set to ${speed}ms`);
};

window.setAISpeed = (speed) => {
    window.liveInterviewUI.streaming.setAIStreamingSpeed(speed);
    console.log(`🤖 AI streaming speed set to ${speed}ms`);
};

window.setMarkdownEnabled = (enabled) => {
    window.liveInterviewUI.streaming.setMarkdownEnabled(enabled);
    console.log(`📝 Markdown processing ${enabled ? 'enabled' : 'disabled'}`);
};

window.setMarkdownSpeed = (speed) => {
    window.liveInterviewUI.streaming.setMarkdownSpeed(speed);
    console.log(`📝 Markdown element speed set to ${speed}ms`);
};

// Process All Speakers Configuration
window.setProcessAllSpeakers = (enabled) => {
    // This function will be fully implemented in main.js where the socket is managed
    if (typeof window.sendSocketMessage === 'function') {
        window.sendSocketMessage('config_update', {
            processAllSpeakers: enabled
        });
        console.log(`🎯 Process All Speakers config sent: ${enabled}`);
    } else {
        console.warn('sendSocketMessage not defined yet. Make sure it is globally available.');
    }
};

window.enableAllSpeakers = () => {
    window.setProcessAllSpeakers(true);
    console.log('🎯 All speakers mode activated - AI will respond to everyone');
};

window.disableAllSpeakers = () => {
    window.setProcessAllSpeakers(false);
    console.log('🎯 Interviewer-only mode activated - AI will only respond to interviewer');
};

// Smart scroll controls
window.setScrollMode = (mode) => {
    if (window.liveInterviewUI) {
        window.liveInterviewUI.setScrollMode(mode);
    }
};

window.getScrollState = () => {
    if (window.liveInterviewUI) {
        return window.liveInterviewUI.scrollState;
    }
    return null;
};

// Enhanced scroll control functions
window.enterReadingMode = () => {
    if (window.liveInterviewUI) {
        window.liveInterviewUI.enterReadingMode();
        console.log('📚 Manually entered reading mode');
    }
};

window.exitReadingMode = () => {
    if (window.liveInterviewUI) {
        window.liveInterviewUI.exitReadingMode();
        console.log('📜 Manually exited reading mode');
    }
};

window.resumeAutoScroll = () => {
    if (window.liveInterviewUI) {
        window.liveInterviewUI.resumeAutoScroll();
    }
};

window.isInReadingMode = () => {
    if (window.liveInterviewUI) {
        return window.liveInterviewUI.scrollState.userReadingMode;
    }
    return false;
};

// Quick presets
window.setFastStreaming = () => {
    window.setInterviewSpeed(15);
    window.setAISpeed(8);
    console.log('🚀 Fast streaming mode activated');
};

window.setSlowStreaming = () => {
    window.setInterviewSpeed(50);
    window.setAISpeed(30);
    console.log('🐌 Slow streaming mode activated');
};

window.setInstantMode = () => {
    window.setInterviewStreaming(false);
    console.log('⚡ Instant mode activated - no streaming animations');
};

// Markdown-specific presets
window.setFastMarkdown = () => {
    window.setMarkdownEnabled(true);
    window.setMarkdownSpeed(50);
    window.setInterviewSpeed(8);
    window.setAISpeed(3);
    console.log('📝 Fast markdown mode activated');
};

window.setSlowMarkdown = () => {
    window.setMarkdownEnabled(true);
    window.setMarkdownSpeed(150);
    window.setInterviewSpeed(20);
    window.setAISpeed(6);
    console.log('📝 Slow markdown mode activated');
};

window.disableMarkdown = () => {
    window.setMarkdownEnabled(false);
    console.log('📝 Markdown processing disabled - plain text only');
};

window.enableMarkdown = () => {
    window.setMarkdownEnabled(true);
    console.log('📝 Markdown processing enabled - formatted text');
};

// Thinking content filter controls
window.enableThinkingFilter = () => {
    if (window.liveInterviewUI) {
        window.liveInterviewUI.thinkingFilterEnabled = true;
        console.log('🧠 Thinking content filter enabled - <think> tags will be hidden');
    }
};

window.disableThinkingFilter = () => {
    if (window.liveInterviewUI) {
        window.liveInterviewUI.thinkingFilterEnabled = false;
        console.log('🧠 Thinking content filter disabled - <think> tags will be visible');
    }
};

window.isThinkingFilterEnabled = () => {
    if (window.liveInterviewUI) {
        return window.liveInterviewUI.thinkingFilterEnabled !== false; // Default to true
    }
    return true;
};


export default window.liveInterviewUI; 