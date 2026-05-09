// hotkeys.js — macOS Edition
// Provides keyboard shortcuts for transparency and other controls.
// macOS: Alt key = ⌥ Option key.  Key codes are identical — only UI labels change.

import { devLog } from './config.js';
import muteManager from './mute-manager.js';

class HotkeyManager {
    constructor() {
        this.transparencyLevels = [0.2, 0.4, 0.6, 0.8, 1.0]; // 5 levels: 20%→100%
        this.currentTransparencyLevel = 3; // Default 80% (index 3)
        this.isEnabled = true;
        this.isAlwaysOnTop = true;

        this.setupEventListeners();
        devLog('🎹 Hotkey manager initialized (macOS — ⌥ Option key)');
    }

    setupEventListeners() {
        document.addEventListener('keydown', this.handleKeyDown.bind(this));
        document.addEventListener('keyup',   this.handleKeyUp.bind(this));

        // Prevent default browser shortcuts that might interfere
        document.addEventListener('keydown', (e) => {
            // ⌥[ and ⌥] — transparency step down/up
            if (e.altKey && ['[', ']'].includes(e.key)) {
                e.preventDefault();
            }
        });
    }

    handleKeyDown(event) {
        if (!this.isEnabled) return;

        // ⌥[ → decrease opacity
        if (event.altKey && event.key === '[') {
            this.decreaseTransparency();
            return;
        }

        // ⌥] → increase opacity
        if (event.altKey && event.key === ']') {
            this.increaseTransparency();
            return;
        }
    }

    handleKeyUp(event) {
        // kept for symmetry with setupEventListeners
    }

    decreaseTransparency() {
        if (this.currentTransparencyLevel > 0) {
            this.currentTransparencyLevel--;
            this.applyTransparency();
        }
    }

    increaseTransparency() {
        if (this.currentTransparencyLevel < this.transparencyLevels.length - 1) {
            this.currentTransparencyLevel++;
            this.applyTransparency();
        }
    }

    async applyTransparency() {
        const transparency = this.transparencyLevels[this.currentTransparencyLevel];
        const percent      = Math.round(transparency * 100);

        try {
            const currentView = document.querySelector('.view.active');
            const isLiveView  = currentView && currentView.id === 'live-view';

            if (!isLiveView) {
                console.log('ℹ️ Transparency hotkeys only work during live interview');
                this.showTransparencyFeedback(100, 'Transparency only available in live interview');
                return;
            }

            const response = await fetch('/api/transparency', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ transparency }),
            });

            if (response.ok) {
                devLog(`🪟 Transparency set to ${percent}% via ⌥[ / ⌥]`);
                this.showTransparencyFeedback(percent);
            }
        } catch (error) {
            console.error('❌ Error setting transparency via hotkey:', error);
        }
    }

    showTransparencyFeedback(percent, message = null) {
        this.removeExistingFeedback();

        const feedback = document.createElement('div');
        feedback.id = 'transparency-feedback';

        if (message) {
            feedback.innerHTML = `<div class="transparency-feedback">ℹ️ ${message}</div>`;
        } else {
            feedback.innerHTML = `
                <div class="transparency-feedback">
                    🪟 ${percent}% Opacity
                    <div class="transparency-bar">${this.generateTransparencyBar()}</div>
                    <div class="hotkey-hint">⌥[ decrease &nbsp; ⌥] increase</div>
                </div>`;
        }

        document.body.appendChild(feedback);
        setTimeout(() => { if (feedback.parentNode) feedback.remove(); }, 2000);
    }

    generateTransparencyBar() {
        return this.transparencyLevels
            .map((_, i) => {
                const active = i === this.currentTransparencyLevel;
                return `<span class="bar-segment ${active ? 'active' : ''}">${active ? '●' : '○'}</span>`;
            })
            .join('');
    }

    removeExistingFeedback() {
        const el = document.getElementById('transparency-feedback');
        if (el) el.remove();
    }

    // ── Public API ────────────────────────────────────────────────────────
    setEnabled(enabled) {
        this.isEnabled = enabled;
        devLog(`🎹 Hotkeys ${enabled ? 'enabled' : 'disabled'}`);
    }

    getCurrentTransparency() {
        return {
            level:   this.currentTransparencyLevel + 1,
            percent: Math.round(this.transparencyLevels[this.currentTransparencyLevel] * 100),
            value:   this.transparencyLevels[this.currentTransparencyLevel],
        };
    }

    setTransparencyLevel(level) {
        if (level >= 1 && level <= 5) {
            this.currentTransparencyLevel = level - 1;
            this.applyTransparency();
        }
    }
}

// ── Singleton ─────────────────────────────────────────────────────────────
const hotkeyManager = new HotkeyManager();

// Console helpers
window.enableHotkeys       = () => hotkeyManager.setEnabled(true);
window.disableHotkeys      = () => hotkeyManager.setEnabled(false);
window.getTransparencyLevel = () => hotkeyManager.getCurrentTransparency();
window.setTransparencyLevel = (l) => hotkeyManager.setTransparencyLevel(l);

export default hotkeyManager;
