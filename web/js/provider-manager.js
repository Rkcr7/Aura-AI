import { devLog } from './config.js';

export class ProviderManager {
    constructor(stateManager, webSocketHandler) {
        this.stateManager = stateManager;
        this.webSocketHandler = webSocketHandler;
        this.aiProviders = [];
        
        this.onboardingForm = {};
        this.checks = {};
        this.initializeElements();
    }

    initializeElements() {
        this.onboardingForm = {
            providerSelect: document.getElementById('ai-provider-select'),
            modelSelect: document.getElementById('ai-model-select'),
            secondaryProviderSelect: document.getElementById('ai-secondary-provider-select'),
            secondaryModelSelect: document.getElementById('ai-secondary-model-select'),
            visionProviderSelect: document.getElementById('vision-provider-select'),
            visionModelSelect: document.getElementById('vision-model-select'),
            visionSecondaryProviderSelect: document.getElementById('vision-secondary-provider-select'),
            visionSecondaryModelSelect: document.getElementById('vision-secondary-model-select'),
        };
        
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

    async loadAiProviders() {
        try {
            const response = await fetch('/api/ai-providers');
            this.aiProviders = await response.json();
            this.stateManager.updateState({ aiProviders: this.aiProviders });

            this.populateProviderDropdowns();
            
            requestAnimationFrame(() => {
                this.setDefaultAIProvider();
            });
        } catch (error) {
            console.error("Failed to load AI providers:", error);
        }
    }

    populateProviderDropdowns() {
        // Primary provider
        if (this.onboardingForm.providerSelect) {
            this.onboardingForm.providerSelect.innerHTML = '<option value="">Select AI Provider</option>';
            this.aiProviders.forEach(p => {
                const option = document.createElement('option');
                option.value = p.name;
                option.textContent = p.name;
                this.onboardingForm.providerSelect.appendChild(option);
            });
        }

        // Secondary provider
        if (this.onboardingForm.secondaryProviderSelect) {
            this.onboardingForm.secondaryProviderSelect.innerHTML = '<option value="">Select Secondary Provider (Optional)</option>';
            this.aiProviders.forEach(p => {
                const option = document.createElement('option');
                option.value = p.name;
                option.textContent = p.name;
                this.onboardingForm.secondaryProviderSelect.appendChild(option);
            });
        }

        // Vision providers
        const visionProviders = this.aiProviders.filter(p => p.supportsVision && p.visionModels?.length > 0);
        
        if (this.onboardingForm.visionProviderSelect) {
            this.onboardingForm.visionProviderSelect.innerHTML = '<option value="">Select Vision Provider (Optional)</option>';
            visionProviders.forEach(p => {
                const option = document.createElement('option');
                option.value = p.name;
                option.textContent = `${p.name} (Vision)`;
                this.onboardingForm.visionProviderSelect.appendChild(option);
            });
        }

        if (this.onboardingForm.visionSecondaryProviderSelect) {
            this.onboardingForm.visionSecondaryProviderSelect.innerHTML = '<option value="">Select Secondary Vision Provider (Optional)</option>';
            visionProviders.forEach(p => {
                const option = document.createElement('option');
                option.value = p.name;
                option.textContent = `${p.name} (Vision)`;
                this.onboardingForm.visionSecondaryProviderSelect.appendChild(option);
            });
        }
    }

    setDefaultAIProvider() {
        try {
            // Set primary provider
            const primaryProvider = this.aiProviders.find(p => p.defaultPrimary);
            if (primaryProvider && this.onboardingForm.providerSelect) {
                this.onboardingForm.providerSelect.value = primaryProvider.name;
                this.onboardingForm.providerSelect.dispatchEvent(new Event('change'));

                setTimeout(() => {
                    if (this.onboardingForm.modelSelect && !this.onboardingForm.modelSelect.disabled) {
                        const defaultModel = primaryProvider.defaultModel || primaryProvider.models[0];
                        if (defaultModel) {
                            // Handle both string and object models for default selection
                            const modelName = this._getModelName(defaultModel);
                            if (modelName) {
                                this.onboardingForm.modelSelect.value = modelName;
                            }
                        }
                    }
                }, 150);
            }

            // Set secondary provider
            const secondaryProvider = this.aiProviders.find(p => p.defaultSecondary);
            if (secondaryProvider && this.onboardingForm.secondaryProviderSelect) {
                this.onboardingForm.secondaryProviderSelect.value = secondaryProvider.name;
                this.onboardingForm.secondaryProviderSelect.dispatchEvent(new Event('change'));

                setTimeout(() => {
                    if (this.onboardingForm.secondaryModelSelect && !this.onboardingForm.secondaryModelSelect.disabled) {
                        const defaultModel = secondaryProvider.defaultModel || secondaryProvider.models[0];
                        if (defaultModel) {
                            // Handle both string and object models for default selection
                            const modelName = this._getModelName(defaultModel);
                            if (modelName) {
                                this.onboardingForm.secondaryModelSelect.value = modelName;
                            }
                        }
                    }
                }, 200);
            }

            // Set primary vision provider
            const primaryVisionProvider = this.aiProviders.find(p => p.defaultVisionPrimary);
            if (primaryVisionProvider && this.onboardingForm.visionProviderSelect) {
                this.onboardingForm.visionProviderSelect.value = primaryVisionProvider.name;
                this.onboardingForm.visionProviderSelect.dispatchEvent(new Event('change'));

                setTimeout(() => {
                    if (this.onboardingForm.visionModelSelect && !this.onboardingForm.visionModelSelect.disabled) {
                        const defaultModel = primaryVisionProvider.defaultVisionModel || primaryVisionProvider.visionModels[0];
                        if (defaultModel) {
                            // Handle both string and object models for default selection
                            const modelName = this._getModelName(defaultModel);
                            if (modelName) {
                                this.onboardingForm.visionModelSelect.value = modelName;
                            }
                        }
                    }
                }, 250);
            }

            // Set secondary vision provider
            const secondaryVisionProvider = this.aiProviders.find(p => p.defaultVisionSecondary);
            if (secondaryVisionProvider && this.onboardingForm.visionSecondaryProviderSelect) {
                this.onboardingForm.visionSecondaryProviderSelect.value = secondaryVisionProvider.name;
                this.onboardingForm.visionSecondaryProviderSelect.dispatchEvent(new Event('change'));

                setTimeout(() => {
                    if (this.onboardingForm.visionSecondaryModelSelect && !this.onboardingForm.visionSecondaryModelSelect.disabled) {
                        const defaultModel = secondaryVisionProvider.defaultVisionModel || secondaryVisionProvider.visionModels[0];
                        if (defaultModel) {
                            // Handle both string and object models for default selection
                            const modelName = this._getModelName(defaultModel);
                            if (modelName) {
                                this.onboardingForm.visionSecondaryModelSelect.value = modelName;
                            }
                        }
                    }
                }, 300);
            }

        } catch (error) {
            console.error("Error setting default AI provider:", error);
        }
    }

    /**
     * Helper function to get the model name from either a string or object model
     * Used for matching default models and setting dropdown values
     *
     * @param {string|object} model - Model (string or object with modelName)
     * @returns {string} - The model name/identifier
     */
    _getModelName(model) {
        if (typeof model === 'string') {
            return model;
        } else if (typeof model === 'object' && model.modelName) {
            return model.modelName;
        }
        return null;
    }

    /**
     * Smart helper function to populate model dropdowns
     * Handles both string models and complex object models with routing
     *
     * @param {Array} models - Array of models (strings or objects)
     * @param {HTMLSelectElement} selectElement - The dropdown element to populate
     * @param {string} defaultOptionText - Text for the default option
     */
    _populateModelDropdown(models, selectElement, defaultOptionText) {
        if (!selectElement || !models) return;

        // Clear existing options and add default
        selectElement.innerHTML = `<option value="">${defaultOptionText}</option>`;
        selectElement.disabled = true;

        if (models.length > 0) {
            // A provider may list the same model twice, once as a routed object
            // and once as a bare string (OpenRouter does). The backend resolves
            // a name to the first entry that matches, so a second option with
            // the same value is unreachable: it silently applies the first
            // entry's routing. Keep the first occurrence so the dropdown agrees
            // with what the backend will actually use.
            const seen = new Set();
            models.forEach(model => {
                const modelValue = typeof model === 'string' ? model : model?.modelName;
                if (modelValue) {
                    if (seen.has(modelValue)) return;
                    seen.add(modelValue);
                }

                const option = document.createElement('option');

                // Handle both string models and object models with routing
                if (typeof model === 'string') {
                    // Simple string model - use as both value and display text
                    option.value = model;
                    option.textContent = model;
                } else if (typeof model === 'object' && model.modelName) {
                    // Complex object model with routing - use modelName as value and description as display
                    option.value = model.modelName;
                    option.textContent = model.description || model.modelName;
                } else {
                    // Fallback for unexpected model format
                    console.warn('Unexpected model format:', model);
                    return; // Skip this model
                }
                
                selectElement.appendChild(option);
            });
            selectElement.disabled = false;
        }
    }

    updateModelDropdown() {
        const providerName = this.onboardingForm.providerSelect?.value;
        const provider = this.aiProviders.find(p => p.name === providerName);
        
        // Use the smart helper function to populate the dropdown
        this._populateModelDropdown(
            provider?.models || [],
            this.onboardingForm.modelSelect,
            'Select Model'
        );
    }

    updateSecondaryModelDropdown() {
        const providerName = this.onboardingForm.secondaryProviderSelect?.value;
        const provider = this.aiProviders.find(p => p.name === providerName);
        
        // Use the smart helper function to populate the dropdown
        this._populateModelDropdown(
            provider?.models || [],
            this.onboardingForm.secondaryModelSelect,
            'Select Secondary Model'
        );
    }

    updateVisionModelDropdown() {
        const providerName = this.onboardingForm.visionProviderSelect?.value;
        const provider = this.aiProviders.find(p => p.name === providerName);
        
        // Use the smart helper function to populate the dropdown
        this._populateModelDropdown(
            provider?.visionModels || [],
            this.onboardingForm.visionModelSelect,
            'Select Vision Model'
        );
    }

    updateSecondaryVisionModelDropdown() {
        const providerName = this.onboardingForm.visionSecondaryProviderSelect?.value;
        const provider = this.aiProviders.find(p => p.name === providerName);
        
        // Use the smart helper function to populate the dropdown
        this._populateModelDropdown(
            provider?.visionModels || [],
            this.onboardingForm.visionSecondaryModelSelect,
            'Select Secondary Vision Model'
        );
    }

    async runPreFlightChecks() {
        const state = this.stateManager.getState();

        // Show/hide secondary checks based on selection
        if (state.selectedSecondaryProvider.name && state.selectedSecondaryProvider.model) {
            this.checks.aiSecondaryProvider.style.display = 'flex';
            devLog('Secondary provider selected, will verify during preflight');
        } else {
            this.checks.aiSecondaryProvider.style.display = 'none';
            devLog('No secondary provider selected, skipping verification');
        }

        if (state.selectedVisionProvider.name && state.selectedVisionProvider.model) {
            this.checks.visionProvider.style.display = 'flex';
            devLog('Primary vision provider selected, will verify during preflight');
        } else {
            this.checks.visionProvider.style.display = 'none';
            devLog('No primary vision provider selected, skipping verification');
        }

        if (state.selectedSecondaryVisionProvider.name && state.selectedSecondaryVisionProvider.model) {
            this.checks.visionSecondaryProvider.style.display = 'flex';
            devLog('Secondary vision provider selected, will verify during preflight');
        } else {
            this.checks.visionSecondaryProvider.style.display = 'none';
            devLog('No secondary vision provider selected, skipping verification');
        }

        // This is a new, separate step to verify the selected STT engine's key.
        this.verifySttEngine();

        await this.verifyAiProviders();
    }

    verifySttEngine() {
        const state = this.stateManager.getState();
        const engine = state.selectedSttEngine || 'deepgram';
        const label = engine === 'sixtydb' ? '60db' : 'Deepgram';
        devLog(`➡️ [Pre-Flight] Requesting ${label} STT verification...`);
        this.webSocketHandler.updateCheckStatus(this.checks.deepgram, 'pending', `Checking ${label}...`);
        this.webSocketHandler.sendMessage('verify_stt', { engine });
    }

    async verifyAiProviders() {
        const state = this.stateManager.getState();

        // Verify primary provider (required)
        await this.verifyProvider(state.selectedProvider, this.checks.aiProvider, 'Primary');
        
        // Verify secondary provider if selected (optional)
        if (state.selectedSecondaryProvider.name && state.selectedSecondaryProvider.model) {
            await this.verifyProvider(state.selectedSecondaryProvider, this.checks.aiSecondaryProvider, 'Secondary');
        }
        
        // Verify vision provider if selected (optional)
        if (state.selectedVisionProvider.name && state.selectedVisionProvider.model) {
            await this.verifyVisionProvider(state.selectedVisionProvider, this.checks.visionProvider, 'Primary Vision');
        }
        
        // Verify secondary vision provider if selected (optional)
        if (state.selectedSecondaryVisionProvider.name && state.selectedSecondaryVisionProvider.model) {
            await this.verifyVisionProvider(state.selectedSecondaryVisionProvider, this.checks.visionSecondaryProvider, 'Secondary Vision');
        }
        
        // This was the missing piece. After all provider checks are complete,
        // we must check if all systems are green to enable the start button.
        this.webSocketHandler.checkAllSystemsGo();
    }

    async verifyProvider(providerConfig, checkElement, providerType) {
        const { name, model } = providerConfig;
        devLog(`➡️ [Pre-Flight] Verifying ${providerType} provider: ${name} (${model})`);
        this.webSocketHandler.updateCheckStatus(checkElement, 'pending', `Checking ${providerType} ${name}...`);
        
        try {
            const response = await fetch('/api/verify-provider', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, model }),
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.webSocketHandler.updateCheckStatus(checkElement, 'success', `${providerType} ${name} (${model}) OK`);
                devLog(`✅ [FRONTEND] Received and processed successful verification for ${providerType} provider: ${name}`);
            } else {
                this.webSocketHandler.updateCheckStatus(checkElement, 'error', `${providerType} ${name} Connection Failed`);
                devLog(`❌ [FRONTEND] Received and processed failed verification for ${providerType} provider: ${name}`);
            }
        } catch (error) {
            this.webSocketHandler.updateCheckStatus(checkElement, 'error', `${providerType} Provider Check Failed`);
            console.error(`❌ ${providerType} provider check error:`, error);
        }
    }

    handleApiKeyStatus({ service, valid }) {
        devLog(`⬅️ [ProviderManager] Handling 'api_key_status' for ${service}. Valid: ${valid}`);

        // Both STT engines report through the same pre-flight check element.
        if (service === 'deepgram' || service === 'sixtydb') {
            const checkElement = this.checks.deepgram;
            const serviceName = service === 'sixtydb' ? '60db' : 'Deepgram';
            if (valid) {
                this.webSocketHandler.updateCheckStatus(checkElement, 'success', `${serviceName} API OK`);
            } else {
                this.webSocketHandler.updateCheckStatus(checkElement, 'error', `${serviceName} API Key Invalid`);
            }
            // Crucially, check all systems *after* the status has been updated.
            this.webSocketHandler.checkAllSystemsGo();
        }
    }

    async verifyVisionProvider(providerConfig, checkElement, providerType) {
        const { name, model } = providerConfig;
        devLog(`➡️ [Pre-Flight] Verifying ${providerType} provider: ${name} (${model})`);
        this.webSocketHandler.updateCheckStatus(checkElement, 'pending', `Checking ${providerType} ${name}...`);
        
        try {
            const response = await fetch('/api/verify-vision-provider', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, model }),
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.webSocketHandler.updateCheckStatus(checkElement, 'success', `${providerType} ${name} (${model}) OK`);
                devLog(`✅ [FRONTEND] Received and processed successful verification for ${providerType} vision provider: ${name}`);
            } else {
                this.webSocketHandler.updateCheckStatus(checkElement, 'error', `${providerType} ${name} Connection Failed`);
                devLog(`❌ [FRONTEND] Received and processed failed verification for ${providerType} vision provider: ${name}`);
            }
        } catch (error) {
            this.webSocketHandler.updateCheckStatus(checkElement, 'error', `${providerType} Provider Check Failed`);
            console.error(`❌ ${providerType} provider check error:`, error);
        }
    }

    checkAllSystemsGo() {
        // Check all required systems
        const requiredChecks = [
            this.checks.micPermission,
            this.checks.micSelection,
            this.checks.backend,
            this.checks.deepgram,
            this.checks.aiProvider
        ];

        // Add optional checks that are visible (selected by user)
        const optionalChecks = [
            this.checks.aiSecondaryProvider,
            this.checks.visionProvider,
            this.checks.visionSecondaryProvider
        ];

        // Filter optional checks to only include visible ones
        const visibleOptionalChecks = optionalChecks.filter(check =>
            check && check.style.display !== 'none'
        );

        const allChecks = [...requiredChecks, ...visibleOptionalChecks];

        // Check if all systems are green
        const allSystemsGo = allChecks.every(check => {
            if (!check) return false;
            const indicator = check.querySelector('.indicator');
            return indicator && indicator.textContent === '🟢';
        });

        // Enable/disable start button
        const startButton = document.getElementById('start-interview-button');
        if (startButton) {
            startButton.disabled = !allSystemsGo;
            devLog(`[checkAllSystemsGo] Start button ${allSystemsGo ? 'ENABLED' : 'DISABLED'}`);
            
            if (allSystemsGo) {
                devLog('🚀 All systems are GO! Interview can start.');
            } else {
                // Log which checks are failing for debugging
                const failingChecks = allChecks.filter(check => {
                    if (!check) return true;
                    const indicator = check.querySelector('.indicator');
                    return !indicator || indicator.textContent !== '🟢';
                }).map(check => check ? check.id : 'null');
                devLog(`❌ Systems not ready. Failing checks: ${failingChecks.join(', ')}`);
            }
        }

        return allSystemsGo;
    }
}