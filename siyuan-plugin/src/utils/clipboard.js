/**
 * Clipboard utilities for the SiYuan plugin.
 *
 * Provides functions for copying text to clipboard with fallback support
 * and user feedback for copy operations.
 */

class ClipboardUtils {
    constructor() {
        this.copySuccessCallbacks = [];
        this.copyErrorCallbacks = [];
    }

    /**
     * Copy text to clipboard using modern Clipboard API with fallback
     * @param {string} text - Text to copy
     * @returns {Promise<boolean>} Success status
     */
    async copyToClipboard(text) {
        try {
            // Try modern Clipboard API first
            if (navigator.clipboard && window.isSecureContext) {
                await navigator.clipboard.writeText(text);
                this._triggerSuccessCallbacks(text);
                return true;
            } else {
                // Fallback to execCommand
                return this._fallbackCopyToClipboard(text);
            }
        } catch (error) {
            console.error('Failed to copy to clipboard:', error);
            this._triggerErrorCallbacks(error);
            return false;
        }
    }

    /**
     * Fallback copy method using document.execCommand
     * @param {string} text - Text to copy
     * @returns {boolean} Success status
     */
    _fallbackCopyToClipboard(text) {
        // Create temporary textarea element
        const textArea = document.createElement('textarea');
        textArea.value = text;

        // Make it invisible but selectable
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        textArea.style.opacity = '0';

        document.body.appendChild(textArea);

        try {
            // Select and copy
            textArea.focus();
            textArea.select();

            const successful = document.execCommand('copy');
            if (successful) {
                this._triggerSuccessCallbacks(text);
                return true;
            } else {
                throw new Error('execCommand copy failed');
            }
        } catch (error) {
            console.error('Fallback copy failed:', error);
            this._triggerErrorCallbacks(error);
            return false;
        } finally {
            // Clean up
            document.body.removeChild(textArea);
        }
    }

    /**
     * Copy code snippet with syntax formatting
     * @param {string} code - Code to copy
     * @param {string} language - Programming language
     * @returns {Promise<boolean>} Success status
     */
    async copyCodeSnippet(code, language = '') {
        // Format code with language identifier if provided
        const formattedCode = language
            ? `\`\`\`${language}\n${code}\n\`\`\``
            : code;

        return await this.copyToClipboard(formattedCode);
    }

    /**
     * Copy multiple code snippets as a single block
     * @param {Array} snippets - Array of code snippet objects
     * @returns {Promise<boolean>} Success status
     */
    async copyMultipleSnippets(snippets) {
        const combinedCode = snippets
            .map(snippet => {
                const title = snippet.title ? `// ${snippet.title}\n` : '';
                const language = snippet.language || '';
                const code = snippet.code;

                if (language) {
                    return `${title}\`\`\`${language}\n${code}\n\`\`\`\n\n`;
                } else {
                    return `${title}${code}\n\n`;
                }
            })
            .join('');

        return await this.copyToClipboard(combinedCode.trim());
    }

    /**
     * Show toast notification for copy operations
     * @param {string} message - Message to show
     * @param {string} type - Notification type ('success', 'error', 'info')
     */
    showCopyNotification(message, type = 'success') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `clipboard-notification ${type}`;
        notification.textContent = message;

        // Style the notification
        Object.assign(notification.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            background: type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6',
            color: 'white',
            padding: '12px 16px',
            borderRadius: '6px',
            boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
            zIndex: '10000',
            fontSize: '14px',
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            opacity: '0',
            transform: 'translateY(-10px)',
            transition: 'all 0.3s ease'
        });

        document.body.appendChild(notification);

        // Animate in
        setTimeout(() => {
            notification.style.opacity = '1';
            notification.style.transform = 'translateY(0)';
        }, 10);

        // Auto remove after 3 seconds
        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transform = 'translateY(-10px)';
            setTimeout(() => {
                if (notification.parentNode) {
                    document.body.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }

    /**
     * Add success callback
     * @param {Function} callback - Callback function(text)
     */
    onCopySuccess(callback) {
        this.copySuccessCallbacks.push(callback);
    }

    /**
     * Add error callback
     * @param {Function} callback - Callback function(error)
     */
    onCopyError(callback) {
        this.copyErrorCallbacks.push(callback);
    }

    /**
     * Remove success callback
     * @param {Function} callback - Callback to remove
     */
    offCopySuccess(callback) {
        const index = this.copySuccessCallbacks.indexOf(callback);
        if (index > -1) {
            this.copySuccessCallbacks.splice(index, 1);
        }
    }

    /**
     * Remove error callback
     * @param {Function} callback - Callback to remove
     */
    offCopyError(callback) {
        const index = this.copyErrorCallbacks.indexOf(callback);
        if (index > -1) {
            this.copyErrorCallbacks.splice(index, 1);
        }
    }

    /**
     * Trigger success callbacks
     * @param {string} text - Copied text
     */
    _triggerSuccessCallbacks(text) {
        this.copySuccessCallbacks.forEach(callback => {
            try {
                callback(text);
            } catch (error) {
                console.error('Copy success callback error:', error);
            }
        });
    }

    /**
     * Trigger error callbacks
     * @param {Error} error - Copy error
     */
    _triggerErrorCallbacks(error) {
        this.copyErrorCallbacks.forEach(callback => {
            try {
                callback(error);
            } catch (callbackError) {
                console.error('Copy error callback error:', callbackError);
            }
        });
    }

    /**
     * Check if clipboard is supported
     * @returns {boolean} Support status
     */
    isClipboardSupported() {
        return !!(navigator.clipboard && window.isSecureContext) ||
               !!(document.execCommand && document.queryCommandSupported && document.queryCommandSupported('copy'));
    }

    /**
     * Get clipboard permission status
     * @returns {Promise<string>} Permission status
     */
    async getClipboardPermission() {
        if (!navigator.permissions) {
            return 'unknown';
        }

        try {
            const result = await navigator.permissions.query({ name: 'clipboard-write' });
            return result.state;
        } catch (error) {
            return 'unknown';
        }
    }
}

// Default instance with built-in notifications
const defaultClipboardUtils = new ClipboardUtils();

// Add default success notification
defaultClipboardUtils.onCopySuccess((text) => {
    const preview = text.length > 50 ? text.substring(0, 50) + '...' : text;
    defaultClipboardUtils.showCopyNotification(`Copied: ${preview}`, 'success');
});

// Add default error notification
defaultClipboardUtils.onCopyError((error) => {
    defaultClipboardUtils.showCopyNotification('Failed to copy to clipboard', 'error');
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ClipboardUtils;
} else if (typeof window !== 'undefined') {
    window.ClipboardUtils = ClipboardUtils;
    window.clipboardUtils = defaultClipboardUtils;
}
