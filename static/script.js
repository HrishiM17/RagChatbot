class ChatBot {
    constructor() {
        this.userId = this.generateUserId();
        this.sessionId = null;
        this.isLoading = false;
        
        this.initializeElements();
        this.attachEventListeners();
        this.updateUsageCounter();
        
        console.log('ChatBot initialized with user ID:', this.userId);
    }

    initializeElements() {
        // Chat elements
        this.messagesArea = document.getElementById('messages');
        this.messageInput = document.getElementById('message-input');
        this.sendBtn = document.getElementById('send-btn');
        this.usageCounter = document.getElementById('usage-counter');
        this.loadingOverlay = document.getElementById('loading');
        
        // Modal elements
        this.uploadModal = document.getElementById('upload-modal');
        this.uploadBtn = document.getElementById('upload-btn');
        this.uploadDocsBtn = document.getElementById('upload-docs');
        this.clearChatBtn = document.getElementById('clear-chat');
        this.closeModalBtns = document.querySelectorAll('.close, .close-modal');
        
        // Upload elements
        this.uploadArea = document.getElementById('upload-area');
        this.fileInput = document.getElementById('file-input');
        this.uploadStatus = document.getElementById('upload-status');
        this.directText = document.getElementById('direct-text');
        this.textSourceName = document.getElementById('text-source-name');
        this.addTextBtn = document.getElementById('add-text-btn');
        
        this.selectedFiles = [];
    }

    generateUserId() {
        // Generate or retrieve user ID from localStorage
        let userId = localStorage.getItem('chatbot_user_id');
        if (!userId) {
            userId = 'user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('chatbot_user_id', userId);
        }
        return userId;
    }

    attachEventListeners() {
        // Chat input events
        this.messageInput.addEventListener('input', () => this.handleInputChange());
        this.messageInput.addEventListener('keydown', (e) => this.handleKeyDown(e));
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        
        // Modal events
        this.uploadDocsBtn.addEventListener('click', () => this.showUploadModal());
        this.clearChatBtn.addEventListener('click', () => this.clearChat());
        this.closeModalBtns.forEach(btn => {
            btn.addEventListener('click', () => this.hideUploadModal());
        });
        
        // Upload events
        this.uploadArea.addEventListener('click', () => this.fileInput.click());
        this.uploadArea.addEventListener('dragover', (e) => this.handleDragOver(e));
        this.uploadArea.addEventListener('dragleave', (e) => this.handleDragLeave(e));
        this.uploadArea.addEventListener('drop', (e) => this.handleFileDrop(e));
        this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        this.uploadBtn.addEventListener('click', () => this.uploadFiles());
        this.addTextBtn.addEventListener('click', () => this.addTextDirectly());
        
        // Close modal when clicking outside
        window.addEventListener('click', (e) => {
            if (e.target === this.uploadModal) {
                this.hideUploadModal();
            }
        });
        
        // Auto-resize textarea
        this.messageInput.addEventListener('input', () => this.autoResizeTextarea());
        this.directText.addEventListener('input', () => this.autoResizeTextarea(this.directText));
    }

    autoResizeTextarea(element = this.messageInput) {
        element.style.height = 'auto';
        element.style.height = Math.min(element.scrollHeight, 120) + 'px';
    }

    handleInputChange() {
        const hasText = this.messageInput.value.trim().length > 0;
        this.sendBtn.disabled = !hasText || this.isLoading;
    }

    handleKeyDown(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!this.isLoading && this.messageInput.value.trim()) {
                this.sendMessage();
            }
        }
    }

    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message || this.isLoading) return;

        // Add user message to chat
        this.addMessage(message, 'user');
        this.messageInput.value = '';
        this.handleInputChange();
        this.autoResizeTextarea();

        // Show typing indicator
        const typingId = this.addTypingIndicator();

        // Show loading state
        this.setLoading(true);

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    user_id: this.userId,
                    session_id: this.sessionId
                })
            });

            const data = await response.json();

            // Remove typing indicator
            this.removeTypingIndicator(typingId);

            if (!response.ok) {
                throw new Error(data.detail || 'Failed to send message');
            }

            // Add bot response
            this.addMessage(data.response, 'bot', data.sources_used);
            
            // Update usage counter
            this.updateUsageCounter(data.usage_remaining);

        } catch (error) {
            // Remove typing indicator
            this.removeTypingIndicator(typingId);
            
            console.error('Error sending message:', error);
            this.addMessage(
                `Sorry, I encountered an error: ${error.message}. Please try again.`, 
                'bot'
            );
        } finally {
            this.setLoading(false);
            // Focus back to input for next message
            setTimeout(() => {
                if (this.messageInput && !this.messageInput.disabled) {
                    this.messageInput.focus();
                }
            }, 100);
        }
    }

    addTypingIndicator() {
        const typingId = 'typing-' + Date.now();
        const typingDiv = document.createElement('div');
        typingDiv.id = typingId;
        typingDiv.className = 'message bot-message';
        typingDiv.innerHTML = `
            <div class="message-content">
                <div class="typing-indicator">
                    <span>AI is thinking</span>
                    <div class="typing-dots">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
            </div>
        `;
        
        this.messagesArea.appendChild(typingDiv);
        this.scrollToBottom();
        return typingId;
    }

    removeTypingIndicator(typingId) {
        const typingElement = document.getElementById(typingId);
        if (typingElement) {
            typingElement.remove();
        }
    }

    addMessage(content, sender, sources = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;

        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        messageContent.innerHTML = this.formatMessage(content);

        const messageTime = document.createElement('div');
        messageTime.className = 'message-time';
        messageTime.textContent = new Date().toLocaleTimeString();

        messageDiv.appendChild(messageContent);
        messageDiv.appendChild(messageTime);

        // Add sources if available
        if (sources && sources.length > 0) {
            const sourcesDiv = document.createElement('div');
            sourcesDiv.className = 'message-sources';
            sourcesDiv.textContent = `Sources: ${sources.join(', ')}`;
            messageDiv.appendChild(sourcesDiv);
        }

        this.messagesArea.appendChild(messageDiv);
        this.scrollToBottom();
    }

    formatMessage(content) {
        // Enhanced formatting: convert newlines to <br> and handle basic markdown-like formatting
        return content
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code style="background: #f1f5f9; padding: 2px 4px; border-radius: 4px; font-family: monospace;">$1</code>')
            .replace(/```([\s\S]*?)```/g, '<pre style="background: #f1f5f9; padding: 1rem; border-radius: 8px; overflow-x: auto; margin: 0.5rem 0;"><code>$1</code></pre>');
    }

    scrollToBottom() {
        // Smooth scroll to bottom
        setTimeout(() => {
            this.messagesArea.scrollTo({
                top: this.messagesArea.scrollHeight,
                behavior: 'smooth'
            });
        }, 100);
    }

    setLoading(loading) {
        this.isLoading = loading;
        this.loadingOverlay.style.display = loading ? 'flex' : 'none';
        this.sendBtn.disabled = loading || !this.messageInput.value.trim();
        this.messageInput.disabled = loading;
        
        // Update button appearance when disabled
        if (loading) {
            this.sendBtn.style.opacity = '0.5';
        } else {
            this.sendBtn.style.opacity = '1';
        }
    }

    async updateUsageCounter(remaining = null) {
        try {
            if (remaining === null) {
                const response = await fetch(`/api/usage/${this.userId}`);
                const data = await response.json();
                remaining = data.messages_remaining;
            }

            const used = 200 - remaining;
            this.usageCounter.textContent = `Messages: ${used}/200`;
            
            if (remaining < 10) {
                this.usageCounter.style.color = '#ef4444';
            } else if (remaining < 50) {
                this.usageCounter.style.color = '#f59e0b';
            } else {
                this.usageCounter.style.color = '#10b981';
            }
        } catch (error) {
            console.error('Error updating usage counter:', error);
        }
    }

    async clearChat() {
        if (confirm('Are you sure you want to clear the chat history?')) {
            try {
                const response = await fetch(`/api/sessions/${this.userId}`, {
                    method: 'DELETE'
                });

                if (response.ok) {
                    // Clear messages area except the initial bot message
                    const initialMessage = this.messagesArea.querySelector('.message');
                    const initialContent = initialMessage ? initialMessage.outerHTML : '';
                    this.messagesArea.innerHTML = initialContent;
                    console.log('Chat history cleared');
                    
                    // Focus input after clearing
                    setTimeout(() => {
                        if (this.messageInput) {
                            this.messageInput.focus();
                        }
                    }, 100);
                }
            } catch (error) {
                console.error('Error clearing chat:', error);
                alert('Failed to clear chat history');
            }
        }
    }

    // Upload Modal Functions
    showUploadModal() {
        this.uploadModal.style.display = 'block';
        this.resetUploadForm();
    }

    hideUploadModal() {
        this.uploadModal.style.display = 'none';
    }

    resetUploadForm() {
        this.selectedFiles = [];
        this.fileInput.value = '';
        this.directText.value = '';
        this.uploadStatus.textContent = '';
        this.uploadStatus.className = 'upload-status';
        this.uploadBtn.disabled = true;
        this.updateFileDisplay();
    }

    handleDragOver(e) {
        e.preventDefault();
        this.uploadArea.classList.add('dragover');
    }

    handleDragLeave(e) {
        e.preventDefault();
        this.uploadArea.classList.remove('dragover');
    }

    handleFileDrop(e) {
        e.preventDefault();
        this.uploadArea.classList.remove('dragover');
        
        const files = Array.from(e.dataTransfer.files);
        this.handleFiles(files);
    }

    handleFileSelect(e) {
        const files = Array.from(e.target.files);
        this.handleFiles(files);
    }

    handleFiles(files) {
        const allowedTypes = ['.pdf', '.docx', '.txt', '.md'];
        const validFiles = files.filter(file => {
            const extension = '.' + file.name.split('.').pop().toLowerCase();
            return allowedTypes.includes(extension);
        });

        if (validFiles.length !== files.length) {
            this.showUploadStatus('Some files were skipped. Only PDF, DOCX, TXT, and MD files are supported.', 'error');
        }

        this.selectedFiles = [...this.selectedFiles, ...validFiles];
        this.updateFileDisplay();
        this.uploadBtn.disabled = this.selectedFiles.length === 0;
    }

    updateFileDisplay() {
        const uploadText = this.uploadArea.querySelector('p');
        if (uploadText) {
            if (this.selectedFiles.length > 0) {
                const fileNames = this.selectedFiles.map(f => f.name).join(', ');
                uploadText.textContent = `Selected: ${fileNames}`;
            } else {
                uploadText.textContent = 'Drag and drop files here or click to select';
            }
        }
    }

    async uploadFiles() {
        if (this.selectedFiles.length === 0) return;

        const formData = new FormData();
        this.selectedFiles.forEach(file => {
            formData.append('files', file);
        });
        formData.append('user_id', this.userId);

        this.uploadBtn.disabled = true;
        this.showUploadStatus('Uploading files...', 'info');

        try {
            const response = await fetch('/api/upload-documents', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok) {
                this.showUploadStatus(
                    `✅ ${data.message}. Created ${data.chunks_created} chunks.`, 
                    'success'
                );
                setTimeout(() => {
                    this.hideUploadModal();
                }, 2000);
            } else {
                throw new Error(data.detail || 'Upload failed');
            }
        } catch (error) {
            console.error('Upload error:', error);
            this.showUploadStatus(`❌ Upload failed: ${error.message}`, 'error');
        } finally {
            this.uploadBtn.disabled = false;
        }
    }

    async addTextDirectly() {
        const text = this.directText.value.trim();
        const sourceName = this.textSourceName.value.trim() || 'direct_input';

        if (!text) {
            alert('Please enter some text to add');
            return;
        }

        this.addTextBtn.disabled = true;
        this.showUploadStatus('Adding text...', 'info');

        try {
            const formData = new FormData();
            formData.append('text', text);
            formData.append('source_name', sourceName);
            formData.append('user_id', this.userId);

            const response = await fetch('/api/add-text', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok) {
                this.showUploadStatus(
                    `✅ ${data.message}`, 
                    'success'
                );
                this.directText.value = '';
                setTimeout(() => {
                    this.hideUploadModal();
                }, 2000);
            } else {
                throw new Error(data.detail || 'Failed to add text');
            }
        } catch (error) {
            console.error('Add text error:', error);
            this.showUploadStatus(`❌ Failed to add text: ${error.message}`, 'error');
        } finally {
            this.addTextBtn.disabled = false;
        }
    }

    showUploadStatus(message, type) {
        this.uploadStatus.textContent = message;
        this.uploadStatus.className = `upload-status ${type}`;
    }
}

// Initialize the chatbot when the page loads
document.addEventListener('DOMContentLoaded', () => {
    try {
        new ChatBot();
    } catch (error) {
        console.error('Failed to initialize chatbot:', error);
    }
});