/**
 * Connection visualization widget for SiYuan plugin.
 *
 * Displays document connections and relationships in an interactive UI
 * that integrates with SiYuan's interface.
 */

class ConnectionsWidget {
    constructor(apiClient, connectionUtils) {
        this.apiClient = apiClient;
        this.connectionUtils = connectionUtils;
        this.currentDocId = null;
        this.connections = [];
        this.container = null;
    }

    /**
     * Initialize the widget
     * @param {HTMLElement} container - Container element
     * @param {string} docId - Current document ID
     */
    async init(container, docId) {
        this.container = container;
        this.currentDocId = docId;

        // Create widget structure
        this.createWidgetStructure();

        // Load and display connections
        await this.loadConnections();
    }

    /**
     * Create the widget HTML structure
     */
    createWidgetStructure() {
        this.container.innerHTML = `
            <div class="connections-widget">
                <div class="connections-header">
                    <h3 class="connections-title">Document Connections</h3>
                    <div class="connections-controls">
                        <button class="refresh-btn" title="Refresh connections">🔄</button>
                        <select class="filter-select">
                            <option value="all">All Connections</option>
                            <option value="strong">Strong Only (≥0.8)</option>
                            <option value="medium">Medium+ (≥0.6)</option>
                        </select>
                    </div>
                </div>

                <div class="connections-stats">
                    <div class="stat-item">
                        <span class="stat-label">Total:</span>
                        <span class="stat-value total-count">0</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Avg Strength:</span>
                        <span class="stat-value avg-strength">0.0</span>
                    </div>
                </div>

                <div class="connections-list">
                    <div class="loading">Loading connections...</div>
                </div>

                <div class="connections-visualization" style="display: none;">
                    <div class="viz-placeholder">
                        <p>Connection graph visualization</p>
                        <small>(Interactive graph will be implemented here)</small>
                    </div>
                </div>
            </div>
        `;

        // Add event listeners
        this.setupEventListeners();

        // Add styles
        this.addStyles();
    }

    /**
     * Setup event listeners for interactive elements
     */
    setupEventListeners() {
        const refreshBtn = this.container.querySelector('.refresh-btn');
        const filterSelect = this.container.querySelector('.filter-select');

        refreshBtn.addEventListener('click', () => this.loadConnections());
        filterSelect.addEventListener('change', (e) => this.filterConnections(e.target.value));
    }

    /**
     * Load connections for the current document
     */
    async loadConnections() {
        if (!this.currentDocId) return;

        const listContainer = this.container.querySelector('.connections-list');
        listContainer.innerHTML = '<div class="loading">Loading connections...</div>';

        try {
            const response = await this.apiClient.getConnections(this.currentDocId);

            if (response.error) {
                listContainer.innerHTML = `
                    <div class="error">
                        <p>Unable to load connections</p>
                        <small>${response.message}</small>
                    </div>
                `;
                return;
            }

            this.connections = response.connections || [];
            this.displayConnections(this.connections);

        } catch (error) {
            console.error('Failed to load connections:', error);
            listContainer.innerHTML = `
                <div class="error">
                    <p>Connection failed</p>
                    <small>Please check backend availability</small>
                </div>
            `;
        }
    }

    /**
     * Display connections in the UI
     * @param {Array} connections - Connections to display
     */
    displayConnections(connections) {
        const listContainer = this.container.querySelector('.connections-list');
        const statsContainer = this.container.querySelector('.connections-stats');

        if (!connections || connections.length === 0) {
            listContainer.innerHTML = `
                <div class="no-connections">
                    <p>No connections found for this document</p>
                    <small>Connections are automatically discovered from document content</small>
                </div>
            `;

            // Update stats
            statsContainer.querySelector('.total-count').textContent = '0';
            statsContainer.querySelector('.avg-strength').textContent = '0.0';

            return;
        }

        // Calculate and display stats
        const stats = this.connectionUtils.calculateConnectionStats(connections);
        statsContainer.querySelector('.total-count').textContent = stats.total;
        statsContainer.querySelector('.avg-strength').textContent = stats.averageStrength.toFixed(2);

        // Create connections list
        const connectionsHtml = connections
            .map(conn => this.createConnectionItem(conn))
            .join('');

        listContainer.innerHTML = connectionsHtml;
    }

    /**
     * Create HTML for a single connection item
     * @param {object} connection - Connection data
     * @returns {string} HTML string
     */
    createConnectionItem(connection) {
        const formatted = this.connectionUtils.formatConnectionForDisplay(connection);
        const strength = formatted.display.strength;
        const type = formatted.display.type;

        return `
            <div class="connection-item" data-strength="${connection.strength}" data-type="${connection.connection_type}">
                <div class="connection-header">
                    <div class="connection-strength">
                        <span class="strength-indicator" style="color: ${strength.color}; opacity: ${strength.opacity}">
                            ${strength.icon}
                        </span>
                        <span class="strength-value">${connection.strength.toFixed(2)}</span>
                    </div>
                    <div class="connection-type">
                        <span class="type-icon" title="${type.description}">${type.icon}</span>
                        <span class="type-label">${type.label}</span>
                    </div>
                </div>

                <div class="connection-target">
                    <div class="target-doc">
                        <strong>${connection.target_doc_id}</strong>
                    </div>
                    <div class="connection-context">
                        ${formatted.display.contextPreview}
                    </div>
                </div>

                <div class="connection-actions">
                    <button class="action-btn open-doc" data-doc-id="${connection.target_doc_id}" title="Open in SiYuan">
                        📖 Open
                    </button>
                    <button class="action-btn show-details" data-connection='${JSON.stringify(connection)}' title="Show details">
                        ℹ️ Details
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * Filter connections based on criteria
     * @param {string} filterType - Filter type
     */
    filterConnections(filterType) {
        let filteredConnections = [...this.connections];

        switch (filterType) {
            case 'strong':
                filteredConnections = this.connectionUtils.filterConnectionsByStrength(filteredConnections, 0.8);
                break;
            case 'medium':
                filteredConnections = this.connectionUtils.filterConnectionsByStrength(filteredConnections, 0.6);
                break;
            case 'all':
            default:
                // No filtering
                break;
        }

        this.displayConnections(filteredConnections);
    }

    /**
     * Add CSS styles for the widget
     */
    addStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .connections-widget {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 100%;
                margin: 0 auto;
            }

            .connections-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 12px;
                padding-bottom: 8px;
                border-bottom: 1px solid #e5e7eb;
            }

            .connections-title {
                margin: 0;
                font-size: 16px;
                font-weight: 600;
                color: #111827;
            }

            .connections-controls {
                display: flex;
                gap: 8px;
                align-items: center;
            }

            .refresh-btn {
                background: none;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                padding: 4px 8px;
                cursor: pointer;
                font-size: 14px;
                transition: background-color 0.2s;
            }

            .refresh-btn:hover {
                background-color: #f3f4f6;
            }

            .filter-select {
                padding: 4px 8px;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                font-size: 12px;
                background: white;
            }

            .connections-stats {
                display: flex;
                gap: 16px;
                margin-bottom: 12px;
                font-size: 12px;
                color: #6b7280;
            }

            .stat-item {
                display: flex;
                gap: 4px;
            }

            .stat-label {
                font-weight: 500;
            }

            .connections-list {
                max-height: 400px;
                overflow-y: auto;
            }

            .connection-item {
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                padding: 12px;
                margin-bottom: 8px;
                background: white;
                transition: box-shadow 0.2s;
            }

            .connection-item:hover {
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }

            .connection-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 8px;
            }

            .connection-strength {
                display: flex;
                align-items: center;
                gap: 6px;
            }

            .strength-indicator {
                font-size: 16px;
            }

            .strength-value {
                font-weight: 600;
                font-size: 12px;
                color: #374151;
            }

            .connection-type {
                display: flex;
                align-items: center;
                gap: 4px;
                font-size: 12px;
                color: #6b7280;
            }

            .connection-target {
                margin-bottom: 8px;
            }

            .target-doc strong {
                color: #1f2937;
                font-size: 14px;
            }

            .connection-context {
                font-size: 12px;
                color: #6b7280;
                margin-top: 4px;
                line-height: 1.4;
            }

            .connection-actions {
                display: flex;
                gap: 6px;
            }

            .action-btn {
                background: none;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                padding: 4px 8px;
                cursor: pointer;
                font-size: 11px;
                transition: background-color 0.2s;
            }

            .action-btn:hover {
                background-color: #f3f4f6;
            }

            .loading, .error, .no-connections {
                text-align: center;
                padding: 20px;
                color: #6b7280;
            }

            .error {
                color: #ef4444;
            }

            .no-connections {
                color: #9ca3af;
            }
        `;

        document.head.appendChild(style);
    }

    /**
     * Update the current document ID
     * @param {string} docId - New document ID
     */
    async updateDocument(docId) {
        if (this.currentDocId !== docId) {
            this.currentDocId = docId;
            await this.loadConnections();
        }
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
    module.exports = ConnectionsWidget;
} else if (typeof window !== 'undefined') {
    window.ConnectionsWidget = ConnectionsWidget;
}
