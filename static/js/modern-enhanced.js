// ULTRA-MODERN CV OPTIMIZER PRO - ENHANCED JAVASCRIPT

class CVOptimizerPro {
    constructor() {
        this.cvText = '';
        this.isProcessing = false;
        this.initializeElements();
        this.bindEvents();
        this.initializeAnimations();
    }

    initializeElements() {
        // Form elements
        this.cvForm = document.getElementById('cv-upload-form');
        this.cvFileInput = document.getElementById('cv-file');
        this.processBtn = document.getElementById('process-cv-btn');
        this.jobTitleInput = document.getElementById('job-title');
        this.jobDescriptionInput = document.getElementById('job-description');
        this.jobUrlInput = document.getElementById('job-url');
        
        // CV text elements
        this.cvPreview = document.getElementById('cv-preview');
        this.cvEditor = document.getElementById('cv-editor');
        this.cvTextEditor = document.getElementById('cv-text-editor');
        this.editCvBtn = document.getElementById('edit-cv-btn');
        this.saveCvBtn = document.getElementById('save-cv-btn');
        this.cancelEditBtn = document.getElementById('cancel-edit-btn');
        
        // Result elements
        this.resultContainer = document.getElementById('result-container');
        this.loadingState = document.getElementById('loading-state');
        this.copyResultBtn = document.getElementById('copy-result-btn');
        this.compareVersionsBtn = document.getElementById('compare-versions-btn');
    }

    bindEvents() {
        // CV Upload
        if (this.cvForm) {
            this.cvForm.addEventListener('submit', (e) => this.handleCVUpload(e));
        }

        // Process CV
        if (this.processBtn) {
            this.processBtn.addEventListener('click', () => this.handleProcessCV());
        }

        // CV Editor
        if (this.editCvBtn) {
            this.editCvBtn.addEventListener('click', () => this.enableCVEdit());
        }
        if (this.saveCvBtn) {
            this.saveCvBtn.addEventListener('click', () => this.saveCVChanges());
        }
        if (this.cancelEditBtn) {
            this.cancelEditBtn.addEventListener('click', () => this.cancelCVEdit());
        }

        // Copy result
        if (this.copyResultBtn) {
            this.copyResultBtn.addEventListener('click', () => this.copyResult());
        }

        // Compare versions
        if (this.compareVersionsBtn) {
            this.compareVersionsBtn.addEventListener('click', () => this.compareVersions());
        }

        // File input change
        if (this.cvFileInput) {
            this.cvFileInput.addEventListener('change', () => this.onFileSelected());
        }

        // Auto-save for form inputs
        this.setupAutoSave();
    }

    initializeAnimations() {
        // Smooth reveal animations
        const cards = document.querySelectorAll('.premium-card');
        cards.forEach((card, index) => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            
            setTimeout(() => {
                card.style.transition = 'all 0.6s cubic-bezier(0.4, 0, 0.2, 1)';
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, index * 150);
        });
    }

    onFileSelected() {
        if (this.cvFileInput.files.length > 0) {
            const file = this.cvFileInput.files[0];
            
            // Validate file
            if (!this.validateFile(file)) {
                return;
            }
            
            // Update UI
            this.updateProcessButton(true);
            this.showNotification('Plik wybrany! Gotowy do przesłania.', 'success');
        }
    }

    validateFile(file) {
        const maxSize = 16 * 1024 * 1024; // 16MB
        const allowedTypes = ['application/pdf'];
        
        if (!allowedTypes.includes(file.type)) {
            this.showNotification('Proszę wybrać plik PDF.', 'error');
            this.cvFileInput.value = '';
            return false;
        }
        
        if (file.size > maxSize) {
            this.showNotification('Plik jest za duży. Maksymalny rozmiar to 16MB.', 'error');
            this.cvFileInput.value = '';
            return false;
        }
        
        return true;
    }

    updateProcessButton(enabled) {
        if (this.processBtn) {
            this.processBtn.disabled = !enabled;
            this.processBtn.innerHTML = enabled 
                ? '<i class="fas fa-brain me-2"></i>Gotowe do analizy!'
                : '<i class="fas fa-brain me-2"></i>Analizuj z AI';
        }
    }

    async handleCVUpload(e) {
        e.preventDefault();
        
        if (this.isProcessing) return;
        
        const formData = new FormData(this.cvForm);
        
        try {
            this.isProcessing = true;
            this.showLoadingState('Przesyłanie CV...');
            
            const response = await fetch('/upload-cv', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.cvText = data.cv_text;
                this.displayCVText(data.cv_text);
                this.updateProcessButton(true);
                this.showNotification('CV przesłane pomyślnie!', 'success');
            } else {
                this.showNotification(data.message || 'Błąd podczas przesyłania CV', 'error');
            }
        } catch (error) {
            console.error('Upload error:', error);
            this.showNotification('Błąd połączenia. Spróbuj ponownie.', 'error');
        } finally {
            this.isProcessing = false;
            this.hideLoadingState();
        }
    }

    async handleProcessCV() {
        if (this.isProcessing || !this.cvText) return;
        
        const selectedOption = document.querySelector('input[name="optimization-option"]:checked')?.value;
        const selectedLanguage = document.querySelector('input[name="language"]:checked')?.value || 'pl';
        
        if (!selectedOption) {
            this.showNotification('Proszę wybrać opcję analizy.', 'warning');
            return;
        }
        
        // Validate required fields
        if (!this.validateRequiredFields(selectedOption)) {
            return;
        }
        
        const requestData = {
            cv_text: this.cvText,
            job_title: this.jobTitleInput?.value.trim() || '',
            job_description: this.jobDescriptionInput?.value.trim() || '',
            job_url: this.jobUrlInput?.value.trim() || '',
            selected_option: selectedOption,
            language: selectedLanguage
        };
        
        try {
            this.isProcessing = true;
            this.showProcessingState();
            
            const response = await fetch('/process-cv', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.displayResults(data.result, selectedOption);
                this.enableResultActions();
                this.showNotification('Analiza zakończona pomyślnie!', 'success');
            } else {
                if (data.payment_required) {
                    this.showPaymentModal();
                } else {
                    this.showNotification(data.message || 'Błąd podczas analizy', 'error');
                }
            }
        } catch (error) {
            console.error('Process error:', error);
            this.showNotification('Błąd połączenia. Spróbuj ponownie.', 'error');
        } finally {
            this.isProcessing = false;
            this.hideProcessingState();
        }
    }

    validateRequiredFields(selectedOption) {
        const requiresJobDescription = ['optimize', 'cover_letter', 'feedback', 'ats_check', 'interview_questions', 'keyword_analysis'];
        const requiresJobTitle = ['position_optimization'];
        
        if (requiresJobDescription.includes(selectedOption)) {
            const hasJobDescription = this.jobDescriptionInput?.value.trim() || this.jobUrlInput?.value.trim();
            if (!hasJobDescription) {
                this.showNotification('Ta opcja wymaga opisu stanowiska lub linku do oferty.', 'warning');
                return false;
            }
        }
        
        if (requiresJobTitle.includes(selectedOption)) {
            if (!this.jobTitleInput?.value.trim()) {
                this.showNotification('Ta opcja wymaga nazwy stanowiska.', 'warning');
                return false;
            }
        }
        
        return true;
    }

    displayCVText(text) {
        if (this.cvPreview) {
            this.cvPreview.innerHTML = this.formatTextAsHtml(text);
        }
        if (this.cvTextEditor) {
            this.cvTextEditor.value = text;
        }
        if (this.editCvBtn) {
            this.editCvBtn.disabled = false;
        }
    }

    displayResults(result, optionType) {
        if (!this.resultContainer) return;
        
        let formattedResult = this.formatResultByType(result, optionType);
        this.resultContainer.innerHTML = formattedResult;
        
        // Smooth reveal animation
        this.resultContainer.style.opacity = '0';
        this.resultContainer.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            this.resultContainer.style.transition = 'all 0.6s ease';
            this.resultContainer.style.opacity = '1';
            this.resultContainer.style.transform = 'translateY(0)';
        }, 100);
    }

    formatResultByType(result, optionType) {
        const typeFormatters = {
            'cv_score': this.formatScoreResult.bind(this),
            'optimize': this.formatOptimizedCV.bind(this),
            'feedback': this.formatFeedbackResult.bind(this),
            'cover_letter': this.formatCoverLetter.bind(this),
            'ats_check': this.formatATSResult.bind(this),
            'interview_questions': this.formatInterviewQuestions.bind(this)
        };
        
        const formatter = typeFormatters[optionType] || this.formatGenericResult.bind(this);
        return formatter(result);
    }

    formatScoreResult(result) {
        try {
            const data = typeof result === 'string' ? JSON.parse(result) : result;
            return `
                <div class="score-result">
                    <div class="score-header text-center mb-4">
                        <div class="score-circle">
                            <span class="score-number">${data.score}</span>
                            <span class="score-grade">${data.grade}</span>
                        </div>
                    </div>
                    <div class="row g-4">
                        <div class="col-md-6">
                            <h5 class="text-success"><i class="fas fa-thumbs-up me-2"></i>Mocne strony</h5>
                            <ul class="list-unstyled">
                                ${data.strengths?.map(s => `<li><i class="fas fa-check text-success me-2"></i>${s}</li>`).join('') || ''}
                            </ul>
                        </div>
                        <div class="col-md-6">
                            <h5 class="text-warning"><i class="fas fa-exclamation-triangle me-2"></i>Do poprawy</h5>
                            <ul class="list-unstyled">
                                ${data.weaknesses?.map(w => `<li><i class="fas fa-arrow-right text-warning me-2"></i>${w}</li>`).join('') || ''}
                            </ul>
                        </div>
                    </div>
                    <div class="mt-4">
                        <h5><i class="fas fa-lightbulb me-2"></i>Rekomendacje</h5>
                        <ul class="list-unstyled">
                            ${data.recommendations?.map(r => `<li><i class="fas fa-star text-primary me-2"></i>${r}</li>`).join('') || ''}
                        </ul>
                    </div>
                </div>
            `;
        } catch (e) {
            return this.formatGenericResult(result);
        }
    }

    formatOptimizedCV(result) {
        return `
            <div class="optimized-cv">
                <div class="alert alert-success mb-4">
                    <i class="fas fa-check-circle me-2"></i>
                    <strong>CV zostało zoptymalizowane!</strong> Poniżej znajdziesz ulepszoną wersję.
                </div>
                <div class="optimized-content">
                    ${this.formatTextAsHtml(result)}
                </div>
            </div>
        `;
    }

    formatGenericResult(result) {
        return `<div class="generic-result">${this.formatTextAsHtml(result)}</div>`;
    }

    formatTextAsHtml(text) {
        return text
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>')
            .replace(/^(.*)$/, '<p>$1</p>')
            .replace(/<p><\/p>/g, '')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>');
    }

    showProcessingState() {
        if (this.loadingState) {
            this.loadingState.style.display = 'block';
        }
        if (this.resultContainer) {
            this.resultContainer.style.display = 'none';
        }
        if (this.processBtn) {
            this.processBtn.disabled = true;
            this.processBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Przetwarzanie...';
        }
    }

    hideProcessingState() {
        if (this.loadingState) {
            this.loadingState.style.display = 'none';
        }
        if (this.resultContainer) {
            this.resultContainer.style.display = 'block';
        }
        if (this.processBtn) {
            this.processBtn.disabled = false;
            this.processBtn.innerHTML = '<i class="fas fa-brain me-2"></i>Analizuj z AI';
        }
    }

    enableResultActions() {
        if (this.copyResultBtn) {
            this.copyResultBtn.disabled = false;
        }
        if (this.compareVersionsBtn) {
            this.compareVersionsBtn.disabled = false;
        }
    }

    async copyResult() {
        try {
            const text = this.resultContainer.innerText;
            await navigator.clipboard.writeText(text);
            
            const originalHtml = this.copyResultBtn.innerHTML;
            this.copyResultBtn.innerHTML = '<i class="fas fa-check me-1"></i>Skopiowano!';
            this.copyResultBtn.classList.add('btn-success');
            
            setTimeout(() => {
                this.copyResultBtn.innerHTML = originalHtml;
                this.copyResultBtn.classList.remove('btn-success');
            }, 2000);
        } catch (error) {
            this.showNotification('Nie udało się skopiować. Zaznacz tekst ręcznie.', 'error');
        }
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
        notification.style.top = '20px';
        notification.style.right = '20px';
        notification.style.zIndex = '9999';
        notification.style.minWidth = '300px';
        
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }

    showPaymentModal() {
        // Implementation for payment modal
        const modal = new bootstrap.Modal(document.getElementById('paymentModal') || this.createPaymentModal());
        modal.show();
    }

    createPaymentModal() {
        const modalHtml = `
            <div class="modal fade" id="paymentModal" tabindex="-1">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title"><i class="fas fa-credit-card me-2"></i>Wymagana płatność</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body text-center">
                            <i class="fas fa-lock fa-3x text-primary mb-3"></i>
                            <h4>Odblokuj pełny potencjał AI</h4>
                            <p>Aby wygenerować analizę CV, dokonaj jednorazowej płatności <strong>9,99 PLN</strong></p>
                            <button class="btn btn-premium btn-lg" onclick="window.location.href='/checkout'">
                                <i class="fas fa-credit-card me-2"></i>Zapłać 9,99 PLN
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        return document.getElementById('paymentModal');
    }

    setupAutoSave() {
        const inputs = [this.jobTitleInput, this.jobDescriptionInput, this.jobUrlInput];
        
        inputs.forEach(input => {
            if (input) {
                input.addEventListener('input', this.debounce(() => {
                    this.saveToLocalStorage();
                }, 1000));
            }
        });
        
        this.loadFromLocalStorage();
    }

    saveToLocalStorage() {
        const data = {
            jobTitle: this.jobTitleInput?.value || '',
            jobDescription: this.jobDescriptionInput?.value || '',
            jobUrl: this.jobUrlInput?.value || ''
        };
        
        localStorage.setItem('cvOptimizerData', JSON.stringify(data));
    }

    loadFromLocalStorage() {
        try {
            const data = JSON.parse(localStorage.getItem('cvOptimizerData') || '{}');
            
            if (this.jobTitleInput && data.jobTitle) {
                this.jobTitleInput.value = data.jobTitle;
            }
            if (this.jobDescriptionInput && data.jobDescription) {
                this.jobDescriptionInput.value = data.jobDescription;
            }
            if (this.jobUrlInput && data.jobUrl) {
                this.jobUrlInput.value = data.jobUrl;
            }
        } catch (error) {
            console.warn('Could not load saved data:', error);
        }
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    window.cvOptimizer = new CVOptimizerPro();
});