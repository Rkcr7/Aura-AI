// Preset Manager for Dynamic AI Model Switching
// Handles UI updates, notifications, and preset switching functionality

class PresetManager {
    constructor() {
        this.currentPreset = null;
        this.availablePresets = [];
        this.healthStatus = {};
        this.isInitialized = false;
        this.notificationTimeout = null;
        
        this.setupPresetUI();
        this.setupNotificationStyles();
        console.log('🎯 PresetManager initialized');
    }
    
    setupPresetUI() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.createPresetIndicator());
        } else {
            this.createPresetIndicator();
        }
    }
    
    createPresetIndicator() {
        // Create preset indicator for live interview view
        const presetIndicator = document.createElement('div');
        presetIndicator.id = 'preset-indicator';
        presetIndicator.className = 'preset-indicator';
        presetIndicator.innerHTML = `
            <div class="preset-display">
                <div class="preset-header">
                    <span class="preset-label">AI Model:</span>
                    <span class="preset-health-dot" title="Provider Health Status"></span>
                </div>
                <div class="preset-details">
                    <span class="preset-name">Loading...</span>
                    <span class="preset-provider">Initializing...</span>
                </div>
                <div class="preset-hotkeys">
                    <span class="hotkey-hint">Alt+Q: Primary | Alt+W: Secondary | Alt+E: Auto</span>
                </div>
            </div>
        `;
        
        // Store reference for later insertion
        this.presetIndicatorElement = presetIndicator;
        
        // Try to insert into live view if it exists
        this.insertPresetIndicator();
    }
    
    insertPresetIndicator() {
        const liveView = document.getElementById('live-view');
        if (liveView && this.presetIndicatorElement && !document.getElementById('preset-indicator')) {
            const liveHeader = liveView.querySelector('.live-header');
            if (liveHeader) {
                liveHeader.appendChild(this.presetIndicatorElement);
                console.log('✅ Preset indicator added to live view');
            }
        }
    }
    
    setupNotificationStyles() {
        // Inject CSS for notifications if not already present
        if (!document.getElementById('preset-manager-styles')) {
            const style = document.createElement('style');
            style.id = 'preset-manager-styles';
            style.textContent = `
                .preset-indicator {
                    background: rgba(0, 0, 0, 0.9);
                    border: 1px solid var(--border-color, #333);
                    border-radius: 6px;
                    padding: 8px 12px;
                    margin-left: 12px;
                    backdrop-filter: blur(10px);
                    min-width: 200px;
                }
                
                .preset-header {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    margin-bottom: 4px;
                }
                
                .preset-label {
                    font-size: 11px;
                    font-weight: 600;
                    color: #a0aec0;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }
                
                .preset-health-dot {
                    width: 8px;
                    height: 8px;
                    border-radius: 50%;
                    background: #4a5568;
                    transition: background-color 0.3s ease;
                }
                
                .preset-health-dot.healthy {
                    background: #48bb78;
                    box-shadow: 0 0 4px rgba(72, 187, 120, 0.4);
                }
                
                .preset-health-dot.unhealthy {
                    background: #f56565;
                    box-shadow: 0 0 4px rgba(245, 101, 101, 0.4);
                }
                
                .preset-details {
                    display: flex;
                    flex-direction: column;
                    gap: 2px;
                }
                
                .preset-name {
                    font-size: 12px;
                    font-weight: 600;
                    color: #ffffff;
                }
                
                .preset-provider {
                    font-size: 10px;
                    color: #718096;
                    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
                }
                
                .preset-hotkeys {
                    margin-top: 4px;
                    border-top: 1px solid rgba(255, 255, 255, 0.1);
                    padding-top: 4px;
                }
                
                .hotkey-hint {
                    font-size: 9px;
                    color: #4a5568;
                    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
                }
                
                .preset-notification {
                    position: fixed;
                    top: 50px;
                    right: 20px;
                    z-index: 10000;
                    max-width: 400px;
                    pointer-events: none;
                    animation: slideInRight 0.3s ease-out;
                }
                
                .notification-content {
                    background: rgba(0, 0, 0, 0.95);
                    border: 1px solid var(--border-color, #333);
                    border-radius: 8px;
                    padding: 16px;
                    backdrop-filter: blur(15px);
                    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
                }
                
                .notification-content.success {
                    border-left: 4px solid #48bb78;
                }
                
                .notification-content.error {
                    border-left: 4px solid #f56565;
                }
                
                .notification-content.warning {
                    border-left: 4px solid #ed8936;
                }
                
                .notification-content.info {
                    border-left: 4px solid #4299e1;
                }
                
                .notification-title {
                    font-size: 14px;
                    font-weight: 600;
                    color: #ffffff;
                    margin-bottom: 8px;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }
                
                .notification-message {
                    font-size: 12px;
                    color: #a0aec0;
                    margin-bottom: 8px;
                    line-height: 1.4;
                }
                
                .notification-details {
                    font-size: 11px;
                    color: #718096;
                    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
                    background: rgba(255, 255, 255, 0.05);
                    padding: 8px;
                    border-radius: 4px;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                }
                
                .health-status {
                    display: flex;
                    gap: 8px;
                    margin-top: 8px;
                }
                
                .health-item {
                    display: flex;
                    align-items: center;
                    gap: 4px;
                    font-size: 10px;
                    color: #718096;
                }
                
                .health-item .health-dot {
                    width: 6px;
                    height: 6px;
                    border-radius: 50%;
                    background: #4a5568;
                }
                
                .health-item .health-dot.healthy {
                    background: #48bb78;
                }
                
                .health-item .health-dot.unhealthy {
                    background: #f56565;
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
                
                .preset-primary {
                    color: #0066ff !important;
                }
                
                .preset-secondary {
                    color: #ff6b35 !important;
                }
                
                .preset-auto {
                    color: #6366f1 !important;
                }
            `;
            document.head.appendChild(style);
        }
    }
    
    updatePresetDisplay(presetInfo) {
        this.currentPreset = presetInfo;
        this.isInitialized = true;
        
        // Ensure the indicator is in the DOM
        this.insertPresetIndicator();
        
        const presetNameElement = document.querySelector('.preset-name');
        const presetProviderElement = document.querySelector('.preset-provider');
        const healthDot = document.querySelector('.preset-health-dot');
        
        if (presetNameElement) {
            presetNameElement.textContent = presetInfo.description || 'Unknown';
            presetNameElement.className = `preset-name preset-${presetInfo.key}`;
        }
        
        if (presetProviderElement) {
            presetProviderElement.textContent = `${presetInfo.provider} - ${presetInfo.model}`;
        }
        
        if (healthDot) {
            healthDot.className = `preset-health-dot ${presetInfo.is_healthy ? 'healthy' : 'unhealthy'}`;
            healthDot.title = presetInfo.is_healthy ? 'Provider is healthy' : 'Provider has issues';
        }
        
        console.log('✅ Preset display updated:', presetInfo);
    }
    
    updateHealthStatus(healthStatus) {
        this.healthStatus = healthStatus;
        
        // Update the health dot based on current preset
        if (this.currentPreset) {
            const healthDot = document.querySelector('.preset-health-dot');
            if (healthDot) {
                const isHealthy = healthStatus[this.currentPreset.key];
                healthDot.className = `preset-health-dot ${isHealthy ? 'healthy' : 'unhealthy'}`;
                healthDot.title = isHealthy ? 'Provider is healthy' : 'Provider has issues';
            }
        }
    }
    
    showSwitchNotification(switchData) {
        // Handle transparency notifications
        if (switchData.type === 'transparency') {
            this.showNotification('🔍 Transparency Changed', switchData.message, '', 'info');
            return;
        }
        
        // Handle audio control notifications
        if (switchData.type === 'audio') {
            let icon = '🎤';
            if (switchData.message.toLowerCase().includes('system')) {
                icon = '⏸️';
            }
            this.showNotification(`${icon} Audio Control`, switchData.message, '', 'info');
            return;
        }
        
        // Handle preset switching notifications
        const isAutoSelected = switchData.auto_selected || false;
        const currentPreset = switchData.current_preset || {};
        const previousPreset = switchData.previous_preset || '';
        const healthResults = switchData.health_results || {};
        
        let title, message, type;
        
        if (isAutoSelected) {
            title = '🤖 Auto-Selected Best Provider';
            message = `Automatically switched to ${currentPreset.description}`;
            type = 'success';
        } else {
            title = '🔄 Model Switched';
            message = `Switched from ${previousPreset} to ${currentPreset.description}`;
            type = 'success';
        }
        
        const details = `Provider: ${currentPreset.provider}\nModel: ${currentPreset.model}\nHealth: ${currentPreset.is_healthy ? '✅ Healthy' : '❌ Issues detected'}`;
        
        this.showNotification(title, message, details, type, healthResults);
    }
    
    showErrorNotification(error, data = {}, title = '❌ Error') {
        const message = typeof error === 'string' ? error : 'An unexpected error occurred';
        const details = data.available_presets ? 
            `Available presets: ${data.available_presets.join(', ')}` : 
            'Please check your configuration';
            
        this.showNotification(title, message, details, 'error', data.health_results);
    }
    
    showNotification(title, message, details = '', type = 'success', healthResults = {}) {
        // Remove existing notification
        this.removeExistingNotification();
        
        const notification = document.createElement('div');
        notification.className = 'preset-notification';
        notification.id = 'preset-notification';
        
        const healthStatusHtml = Object.keys(healthResults).length > 0 ? 
            `<div class="health-status">
                ${Object.entries(healthResults).map(([key, healthy]) => 
                    `<div class="health-item">
                        <span class="health-dot ${healthy ? 'healthy' : 'unhealthy'}"></span>
                        <span>${key}</span>
                    </div>`
                ).join('')}
            </div>` : '';
        
        notification.innerHTML = `
            <div class="notification-content ${type}">
                <div class="notification-title">${title}</div>
                <div class="notification-message">${message}</div>
                ${details ? `<div class="notification-details">${details}</div>` : ''}
                ${healthStatusHtml}
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-hide after 4 seconds
        this.notificationTimeout = setTimeout(() => {
            this.removeExistingNotification();
        }, 4000);
    }
    
    removeExistingNotification() {
        const existing = document.getElementById('preset-notification');
        if (existing) {
            existing.remove();
        }
        
        if (this.notificationTimeout) {
            clearTimeout(this.notificationTimeout);
            this.notificationTimeout = null;
        }
    }
    
    // Public API methods
    getCurrentPreset() {
        return this.currentPreset;
    }
    
    getHealthStatus() {
        return this.healthStatus;
    }
    
    isReady() {
        return this.isInitialized;
    }
    
    // Handle manual preset switching with UI feedback
    switchPreset(presetKey) {
        if (!this.isInitialized) {
            this.showErrorNotification('Preset system not initialized');
            return;
        }
        
        // Show loading state
        this.showNotification(
            '🔄 Switching Model...',
            `Changing to ${presetKey} preset`,
            'Please wait...',
            'warning'
        );
        
        // Trigger the actual switch via main.js
        if (window.switchPreset) {
            window.switchPreset(presetKey);
        } else {
            this.showErrorNotification('Preset switching not available');
        }
    }
}

// Create global instance
const presetManager = new PresetManager();

// Make it globally accessible
window.presetManager = presetManager;

export default presetManager; 