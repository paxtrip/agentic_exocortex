/**
 * Code display widget for SiYuan plugin.
 *
 * Displays code snippets with syntax highlighting and interactive features
 * for developers to explore and copy code examples.
 */

class CodeDisplayWidget {
    constructor(apiClient, clipboardUtils) {
        this.apiClient = apiClient;
        this.clipboardUtils = clipboardUtils;
        this.currentQuery = '';
        this.currentLanguage = '';
        this.snippets = [];
        this.container = null;
        this.highlightJsLoaded = false;
    }

    /**
     * Initialize the widget
     * @param {HTMLElement} container - Container element
     */
    async init(container) {
        this.container = container;

        // Load highlight.js if not already loaded
        await this.loadHighlightJs();

        // Create widget structure
        this.createWidgetStructure();

        // Setup event listeners
        this.setupEventListeners();
    }

    /**
     * Load highlight.js for syntax highlighting
     */
    async loadHighlightJs() {
        if (this.highlightJsLoaded) return;

        return new Promise((resolve, reject) => {
            // Load highlight.js CSS
            const cssLink = document.createElement('link');
            cssLink.rel = 'stylesheet';
            cssLink.href = 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css';
            document.head.appendChild(cssLink);

            // Load highlight.js JS
            const script = document.createElement('script');
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js';
            script.onload = () => {
                this.highlightJsLoaded = true;
                resolve();
            };
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    /**
     * Create the widget HTML structure
     */
    createWidgetStructure() {
        this.container.innerHTML = `
            <div class="code-display-widget">
                <div class="code-search-header">
                    <h3 class="code-search-title">Code Search</h3>
                    <div class="code-search-controls">
                        <input type="text" class="search-input" placeholder="Describe the code you need...">
                        <select class="language-select">
                            <option value="">All Languages</option>
                            <option value="python">Python</option>
                            <option value="javascript">JavaScript</option>
                            <option value="sql">SQL</option>
                            <option value="bash">Bash</option>
                            <option value="html">HTML</option>
                            <option value="css">CSS</option>
                        </select>
                        <button class="search-btn">🔍 Search</button>
                    </div>
                </div>

                <div class="code-results">
                    <div class="code-stats">
                        <div class="stat-item">
                            <span class="stat-label">Found:</span>
                            <span class="stat-value results-count">0</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Languages:</span>
                            <span class="stat-value languages-count">0</span>
                        </div>
                    </div>

                    <div class="code-list">
                        <div class="no-results">
                            <p>Enter a search query to find code examples</p>
                            <small>Try: "sorting algorithm", "API call", "file operations"</small>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Add styles
        this.addStyles();
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        const searchInput = this.container.querySelector('.search-input');
        const languageSelect = this.container.querySelector('.language-select');
        const searchBtn = this.container.querySelector('.search-btn');

        // Search on Enter key
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.performSearch();
            }
        });

        // Search on button click
        searchBtn.addEventListener('click', () => this.performSearch());

        // Search on language change
        languageSelect.addEventListener('change', () => this.performSearch());
    }

    /**
     * Perform code search
     */
    async performSearch() {
        const queryInput = this.container.querySelector('.search-input');
        const languageSelect = this.container.querySelector('.language-select');

        const query = queryInput.value.trim();
        const language = languageSelect.value;

        if (!query) {
            this.showNoResults('Please enter a search query');
            return;
        }

        this.currentQuery = query;
        this.currentLanguage = language;

        const resultsContainer = this.container.querySelector('.code-list');
        resultsContainer.innerHTML = '<div class="loading">Searching for code...</div>';

        try {
            const response = await this.apiClient.searchCode({
                query: query,
                language: language,
                limit: 20
            });

            if (response.error) {
                resultsContainer.innerHTML = `
                    <div class="error">
                        <p>Search failed</p>
                        <small>${response.message}</small>
                    </div>
                `;
                return;
            }

            this.snippets = response.snippets || [];
            this.displayResults(this.snippets);

        } catch (error) {
            console.error('Code search failed:', error);
            resultsContainer.innerHTML = `
                <div class="error">
                    <p>Search failed</p>
                    <small>Please check backend availability</small>
                </div>
            `;
        }
    }

    /**
     * Display search results
     * @param {Array} snippets - Code snippets to display
     */
    displayResults(snippets) {
        const resultsContainer = this.container.querySelector('.code-list');
        const statsContainer = this.container.querySelector('.code-stats');

        // Update stats
        const resultsCount = this.container.querySelector('.results-count');
        const languagesCount = this.container.querySelector('.languages-count');

        resultsCount.textContent = snippets.length;

        const languages = new Set(snippets.map(s => s.language));
        languagesCount.textContent = languages.size;

        if (!snippets || snippets.length === 0) {
            resultsContainer.innerHTML = `
                <div class="no-results">
                    <p>No code snippets found</p>
                    <small>Try different keywords or check your search terms</small>
                </div>
            `;
            return;
        }

        // Create snippets list
        const snippetsHtml = snippets
            .map(snippet => this.createSnippetItem(snippet))
            .join('');

        resultsContainer.innerHTML = snippetsHtml;

        // Apply syntax highlighting
        if (this.highlightJsLoaded && window.hljs) {
            resultsContainer.querySelectorAll('pre code').forEach((block) => {
                window.hljs.highlightElement(block);
            });
        }
    }

    /**
     * Create HTML for a code snippet item
     * @param {object} snippet - Code snippet data
     * @returns {string} HTML string
     */
    createSnippetItem(snippet) {
        const tagsHtml = (snippet.tags || [])
            .map(tag => `<span class="code-tag">${tag}</span>`)
            .join('');

        const confidencePercent = Math.round(snippet.confidence * 100);

        return `
            <div class="code-snippet-item" data-snippet-id="${snippet.id}">
                <div class="code-snippet-header">
                    <div class="code-snippet-meta">
                        <span class="code-language">${snippet.language}</span>
                        <span class="code-confidence" title="Detection confidence: ${confidencePercent}%">
                            ${'●'.repeat(Math.max(1, Math.round(confidencePercent / 20)))}
                        </span>
                        <span class="code-doc-id">${snippet.doc_id}</span>
                    </div>
                    <div class="code-snippet-actions">
                        <button class="action-btn copy-btn" data-code="${this.escapeHtml(snippet.code)}" title="Copy to clipboard">
                            📋 Copy
                        </button>
                        <button class="action-btn expand-btn" title="Expand/collapse">
                            ▼
                        </button>
                    </div>
                </div>

                <div class="code-snippet-title">
                    ${this.escapeHtml(snippet.title)}
                </div>

                <div class="code-snippet-tags">
                    ${tagsHtml}
                </div>

                <div class="code-snippet-content">
                    <pre><code class="language-${snippet.language}">${this.escapeHtml(snippet.code)}</code></pre>
                </div>

                <div class="code-snippet-footer">
                    <small>Lines ${snippet.line_start}-${snippet.line_end} • ${snippet.created_at}</small>
                </div>
            </div>
        `;
    }

    /**
     * Show no results message
     * @param {string} message - Message to display
     */
    showNoResults(message) {
        const resultsContainer = this.container.querySelector('.code-list');
        resultsContainer.innerHTML = `
            <div class="no-results">
                <p>${message}</p>
            </div>
        `;
    }

    /**
     * Escape HTML characters
     * @param {string} text - Text to escape
     * @returns {string} Escaped text
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Add CSS styles for the widget
     */
    addStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .code-display-widget {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Courier New', monospace;
                max-width: 100%;
                margin: 0 auto;
            }

            .code-search-header {
                margin-bottom: 16px;
                padding-bottom: 12px;
                border-bottom: 1px solid #e5e7eb;
            }

            .code-search-title {
                margin: 0 0 12px 0;
                font-size: 16px;
                font-weight: 600;
                color: #111827;
            }

            .code-search-controls {
                display: flex;
                gap: 8px;
                align-items: center;
            }

            .search-input {
                flex: 1;
                padding: 8px 12px;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                font-size: 14px;
                min-width: 200px;
            }

            .language-select {
                padding: 8px 12px;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                font-size: 14px;
                background: white;
                min-width: 120px;
            }

            .search-btn {
                background: #3b82f6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                cursor: pointer;
                font-size: 14px;
                transition: background-color 0.2s;
            }

            .search-btn:hover {
                background: #2563eb;
            }

            .code-stats {
                display: flex;
                gap: 16px;
                margin-bottom: 12px;
                font-size: 12px;
                color: #6b7280;
            }

            .code-list {
                max-height: 600px;
                overflow-y: auto;
            }

            .code-snippet-item {
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 16px;
                margin-bottom: 12px;
                background: white;
                transition: box-shadow 0.2s;
            }

            .code-snippet-item:hover {
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            }

            .code-snippet-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 8px;
            }

            .code-snippet-meta {
                display: flex;
                align-items: center;
                gap: 12px;
                font-size: 12px;
            }

            .code-language {
                background: #f3f4f6;
                color: #374151;
                padding: 2px 6px;
                border-radius: 4px;
                font-weight: 500;
                text-transform: uppercase;
            }

            .code-confidence {
                color: #10b981;
                font-size: 14px;
            }

            .code-doc-id {
                color: #6b7280;
                font-family: monospace;
            }

            .code-snippet-actions {
                display: flex;
                gap: 6px;
            }

            .action-btn {
                background: none;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                padding: 4px 8px;
                cursor: pointer;
                font-size: 12px;
                transition: background-color 0.2s;
            }

            .action-btn:hover {
                background-color: #f3f4f6;
            }

            .code-snippet-title {
                font-weight: 600;
                color: #111827;
                margin-bottom: 6px;
                font-size: 14px;
            }

            .code-snippet-tags {
                margin-bottom: 12px;
            }

            .code-tag {
                display: inline-block;
                background: #e0e7ff;
                color: #3730a3;
                padding: 2px 6px;
                border-radius: 4px;
                font-size: 11px;
                margin-right: 4px;
                margin-bottom: 4px;
            }

            .code-snippet-content {
                margin-bottom: 12px;
                border-radius: 6px;
                overflow: hidden;
            }

            .code-snippet-content pre {
                margin: 0;
                padding: 12px;
                background: #f8f9fa;
                border: 1px solid #e9ecef;
                font-size: 13px;
                line-height: 1.4;
                overflow-x: auto;
            }

            .code-snippet-footer {
                font-size: 11px;
                color: #6b7280;
                text-align: right;
            }

            .loading, .error, .no-results {
                text-align: center;
                padding: 40px 20px;
                color: #6b7280;
            }

            .error {
                color: #ef4444;
            }

            .no-results {
                color: #9ca3af;
            }

            /* Syntax highlighting adjustments */
            .hljs {
                background: transparent !important;
            }
        `;

        document.head.appendChild(style);

        // Add event listeners for dynamic elements
        this.setupDynamicEventListeners();
    }

    /**
     * Setup event listeners for dynamically created elements
     */
    setupDynamicEventListeners() {
        this.container.addEventListener('click', (e) => {
            const target = e.target;

            // Copy button
            if (target.classList.contains('copy-btn')) {
                const code = target.dataset.code;
                this.clipboardUtils.copyToClipboard(code);
                this.showCopyFeedback(target);
            }

            // Expand/collapse button
            if (target.classList.contains('expand-btn')) {
                this.toggleSnippetExpansion(target);
            }
        });
    }

    /**
     * Show copy feedback
     * @param {HTMLElement} button - Copy button element
     */
    showCopyFeedback(button) {
        const originalText = button.textContent;
        button.textContent = '✅ Copied!';
        button.style.backgroundColor = '#10b981';

        setTimeout(() => {
            button.textContent = originalText;
            button.style.backgroundColor = '';
        }, 2000);
    }

    /**
     * Toggle snippet expansion
     * @param {HTMLElement} button - Expand button element
     */
    toggleSnippetExpansion(button) {
        const snippetItem = button.closest('.code-snippet-item');
        const content = snippetItem.querySelector('.code-snippet-content');
        const isExpanded = content.style.display !== 'none';

        if (isExpanded) {
            content.style.display = 'none';
            button.textContent = '▶';
        } else {
            content.style.display = 'block';
            button.textContent = '▼';
        }
    }

    /**
     * Update search query
     * @param {string} query - New search query
     */
    updateQuery(query) {
        const searchInput = this.container.querySelector('.search-input');
        searchInput.value = query;
        this.performSearch();
    }

    /**
     * Destroy the widget and clean up
     */
    destroy() {
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CodeDisplayWidget;
} else if (typeof window !== 'undefined') {
    window.CodeDisplayWidget = CodeDisplayWidget;
}
