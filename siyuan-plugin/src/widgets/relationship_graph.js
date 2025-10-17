/**
 * Relationship Graph Widget for SiYuan Plugin
 *
 * This widget visualizes semantic relationships between documents,
 * allowing writers to explore idea connections in their work.
 *
 * Supports User Story 3: Writer Discovering Idea Connections
 */

class RelationshipGraphWidget {
    constructor(container) {
        this.container = container;
        this.graph = null;
        this.network = null;
        this.currentDocumentId = null;
    }

    /**
     * Initialize the relationship graph widget
     */
    async init() {
        this.render();
        await this.loadRelationshipData();
        this.setupEventListeners();
    }

    /**
     * Render the widget UI
     */
    render() {
        this.container.innerHTML = `
            <div class="relationship-graph-widget">
                <div class="graph-header">
                    <h3>Idea Connections</h3>
                    <div class="graph-controls">
                        <button id="refresh-graph" class="graph-btn">🔄 Refresh</button>
                        <button id="expand-graph" class="graph-btn">📈 Expand</button>
                        <button id="focus-central" class="graph-btn">🎯 Focus</button>
                    </div>
                </div>
                <div class="graph-filters">
                    <label>
                        <input type="checkbox" id="filter-similar" checked> Similar
                    </label>
                    <label>
                        <input type="checkbox" id="filter-contrasts" checked> Contrasts
                    </label>
                    <label>
                        <input type="checkbox" id="filter-builds-on" checked> Builds On
                    </label>
                    <label>
                        <input type="checkbox" id="filter-related" checked> Related
                    </label>
                    <label>
                        <input type="range" id="confidence-threshold" min="0" max="1" step="0.1" value="0.3">
                        Confidence: <span id="confidence-value">0.3</span>
                    </label>
                </div>
                <div id="graph-container" class="graph-container">
                    <div id="graph-loading" class="graph-loading">
                        Loading relationship graph...
                    </div>
                </div>
                <div class="graph-info">
                    <div id="graph-stats" class="graph-stats">
                        Nodes: 0 | Edges: 0
                    </div>
                    <div id="selected-info" class="selected-info">
                        Click on nodes to see details
                    </div>
                </div>
            </div>
        `;

        // Add CSS styles
        this.addStyles();
    }

    /**
     * Add CSS styles for the widget
     */
    addStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .relationship-graph-widget {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: var(--b3-theme-background);
                border-radius: 8px;
                padding: 16px;
                margin: 8px 0;
            }

            .graph-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 12px;
            }

            .graph-header h3 {
                margin: 0;
                color: var(--b3-theme-on-background);
                font-size: 16px;
                font-weight: 600;
            }

            .graph-controls {
                display: flex;
                gap: 8px;
            }

            .graph-btn {
                padding: 4px 8px;
                border: 1px solid var(--b3-theme-surface-lighter);
                background: var(--b3-theme-background);
                color: var(--b3-theme-on-background);
                border-radius: 4px;
                cursor: pointer;
                font-size: 12px;
            }

            .graph-btn:hover {
                background: var(--b3-theme-surface-lighter);
            }

            .graph-filters {
                display: flex;
                flex-wrap: wrap;
                gap: 12px;
                margin-bottom: 12px;
                padding: 8px;
                background: var(--b3-theme-surface-lighter);
                border-radius: 4px;
            }

            .graph-filters label {
                display: flex;
                align-items: center;
                gap: 4px;
                font-size: 12px;
                color: var(--b3-theme-on-surface);
            }

            .graph-container {
                height: 400px;
                border: 1px solid var(--b3-theme-surface-lighter);
                border-radius: 4px;
                position: relative;
            }

            .graph-loading {
                display: flex;
                align-items: center;
                justify-content: center;
                height: 100%;
                color: var(--b3-theme-on-surface);
                font-size: 14px;
            }

            .graph-info {
                margin-top: 12px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                font-size: 12px;
                color: var(--b3-theme-on-surface);
            }

            .graph-stats {
                font-weight: 500;
            }

            .selected-info {
                font-style: italic;
                color: var(--b3-theme-on-surface-variant);
            }

            /* Vis.js network styling */
            .vis-network {
                background: var(--b3-theme-background);
            }

            .vis-network .vis-manipulation {
                background: var(--b3-theme-surface);
                border-color: var(--b3-theme-surface-lighter);
            }

            .vis-network .vis-tooltip {
                background: var(--b3-theme-surface);
                color: var(--b3-theme-on-surface);
                border: 1px solid var(--b3-theme-surface-lighter);
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
            }
        `;
        document.head.appendChild(style);
    }

    /**
     * Load relationship data from the backend
     */
    async loadRelationshipData() {
        try {
            this.showLoading(true);

            // Get current document ID from SiYuan
            this.currentDocumentId = await this.getCurrentDocumentId();

            // Fetch relationship graph data
            const response = await fetch('/api/relationships/graph');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            this.graph = data.graph;

            // Initialize the network visualization
            this.initializeNetwork();

            this.updateStats();
            this.showLoading(false);

        } catch (error) {
            console.error('Failed to load relationship data:', error);
            this.showError('Failed to load relationship graph. Please check your connection.');
            this.showLoading(false);
        }
    }

    /**
     * Initialize the Vis.js network visualization
     */
    initializeNetwork() {
        if (!this.graph || !this.graph.nodes || !this.graph.edges) {
            this.showError('No relationship data available');
            return;
        }

        const container = document.getElementById('graph-container');

        // Prepare nodes with styling
        const nodes = new vis.DataSet(this.graph.nodes.map(node => ({
            id: node.id,
            label: node.label || node.id,
            group: node.group || 'document',
            title: this.createNodeTooltip(node),
            size: this.getNodeSize(node),
            color: this.getNodeColor(node)
        })));

        // Prepare edges with styling
        const edges = new vis.DataSet(this.graph.edges.map(edge => ({
            from: edge.from,
            to: edge.to,
            label: edge.label,
            title: edge.context || edge.label,
            width: this.getEdgeWidth(edge),
            color: this.getEdgeColor(edge),
            arrows: 'to',
            smooth: true
        })));

        // Network options
        const options = {
            nodes: {
                shape: 'dot',
                font: {
                    size: 12,
                    color: 'var(--b3-theme-on-background)'
                },
                borderWidth: 2,
                shadow: true
            },
            edges: {
                font: {
                    size: 10,
                    align: 'middle',
                    color: 'var(--b3-theme-on-surface)'
                },
                shadow: true,
                smooth: {
                    type: 'continuous'
                }
            },
            physics: {
                enabled: true,
                barnesHut: {
                    gravitationalConstant: -2000,
                    centralGravity: 0.3,
                    springLength: 95,
                    springConstant: 0.04,
                    damping: 0.09
                },
                stabilization: {
                    enabled: true,
                    iterations: 100
                }
            },
            interaction: {
                hover: true,
                tooltipDelay: 300,
                zoomView: true,
                dragView: true
            },
            groups: {
                document: {
                    color: {
                        background: 'var(--b3-theme-primary)',
                        border: 'var(--b3-theme-primary)',
                        highlight: {
                            background: 'var(--b3-theme-primary-container)',
                            border: 'var(--b3-theme-primary)'
                        }
                    }
                },
                current: {
                    color: {
                        background: 'var(--b3-theme-secondary)',
                        border: 'var(--b3-theme-secondary)',
                        highlight: {
                            background: 'var(--b3-theme-secondary-container)',
                            border: 'var(--b3-theme-secondary)'
                        }
                    },
                    size: 25
                }
            }
        };

        // Create the network
        this.network = new vis.Network(container, { nodes, edges }, options);

        // Set up event listeners
        this.network.on('selectNode', (params) => {
            this.onNodeSelected(params);
        });

        this.network.on('deselectNode', () => {
            this.onNodeDeselected();
        });
    }

    /**
     * Create tooltip for a node
     */
    createNodeTooltip(node) {
        return `
            <div>
                <strong>${node.label}</strong><br>
                <small>ID: ${node.id}</small><br>
                <small>Type: ${node.group}</small>
            </div>
        `;
    }

    /**
     * Get node size based on properties
     */
    getNodeSize(node) {
        if (node.id === this.currentDocumentId) {
            return 25; // Larger for current document
        }
        return 20;
    }

    /**
     * Get node color based on properties
     */
    getNodeColor(node) {
        if (node.id === this.currentDocumentId) {
            return {
                background: 'var(--b3-theme-secondary)',
                border: 'var(--b3-theme-secondary)',
                highlight: {
                    background: 'var(--b3-theme-secondary-container)',
                    border: 'var(--b3-theme-secondary)'
                }
            };
        }
        return {
            background: 'var(--b3-theme-primary)',
            border: 'var(--b3-theme-primary)',
            highlight: {
                background: 'var(--b3-theme-primary-container)',
                border: 'var(--b3-theme-primary)'
            }
        };
    }

    /**
     * Get edge width based on confidence
     */
    getEdgeWidth(edge) {
        const strength = edge.strength || 0.5;
        return Math.max(1, Math.min(5, strength * 5));
    }

    /**
     * Get edge color based on relationship type
     */
    getEdgeColor(edge) {
        const typeColors = {
            'similar': '#4CAF50',      // Green
            'contrasts': '#F44336',    // Red
            'builds_on': '#2196F3',    // Blue
            'related': '#FF9800'       // Orange
        };

        const color = typeColors[edge.type] || '#9E9E9E'; // Gray fallback
        return {
            color: color,
            highlight: color,
            hover: color
        };
    }

    /**
     * Handle node selection
     */
    onNodeSelected(params) {
        const nodeId = params.nodes[0];
        if (!nodeId) return;

        // Update info display
        const node = this.graph.nodes.find(n => n.id === nodeId);
        if (node) {
            const info = document.getElementById('selected-info');
            info.textContent = `Selected: ${node.label} (${node.group})`;
        }

        // Highlight connected edges
        this.network.selectEdges(this.network.getConnectedEdges(nodeId));
    }

    /**
     * Handle node deselection
     */
    onNodeDeselected() {
        const info = document.getElementById('selected-info');
        info.textContent = 'Click on nodes to see details';

        // Clear edge selection
        this.network.selectEdges([]);
    }

    /**
     * Setup event listeners for controls
     */
    setupEventListeners() {
        // Refresh button
        document.getElementById('refresh-graph').addEventListener('click', () => {
            this.loadRelationshipData();
        });

        // Expand button
        document.getElementById('expand-graph').addEventListener('click', () => {
            this.expandGraph();
        });

        // Focus button
        document.getElementById('focus-central').addEventListener('click', () => {
            this.focusOnCurrentDocument();
        });

        // Filter checkboxes
        ['filter-similar', 'filter-contrasts', 'filter-builds-on', 'filter-related'].forEach(id => {
            document.getElementById(id).addEventListener('change', () => {
                this.applyFilters();
            });
        });

        // Confidence threshold slider
        const thresholdSlider = document.getElementById('confidence-threshold');
        const thresholdValue = document.getElementById('confidence-value');

        thresholdSlider.addEventListener('input', (e) => {
            thresholdValue.textContent = e.target.value;
            this.applyFilters();
        });
    }

    /**
     * Apply filters to the graph
     */
    applyFilters() {
        if (!this.network) return;

        const filters = {
            similar: document.getElementById('filter-similar').checked,
            contrasts: document.getElementById('filter-contrasts').checked,
            builds_on: document.getElementById('filter-builds-on').checked,
            related: document.getElementById('filter-related').checked
        };

        const threshold = parseFloat(document.getElementById('confidence-threshold').value);

        // Filter edges based on type and confidence
        const visibleEdges = this.graph.edges.filter(edge => {
            const typeAllowed = filters[edge.type] !== false;
            const confidenceOk = (edge.strength || 0) >= threshold;
            return typeAllowed && confidenceOk;
        });

        // Update the network with filtered edges
        const edges = new vis.DataSet(visibleEdges.map(edge => ({
            from: edge.from,
            to: edge.to,
            label: edge.label,
            title: edge.context || edge.label,
            width: this.getEdgeWidth(edge),
            color: this.getEdgeColor(edge),
            arrows: 'to',
            smooth: true
        })));

        this.network.setData({ nodes: this.network.body.data.nodes, edges });
        this.updateStats();
    }

    /**
     * Expand the graph by loading more relationships
     */
    async expandGraph() {
        // This would load additional relationship data
        // For now, just refresh
        await this.loadRelationshipData();
    }

    /**
     * Focus the view on the current document
     */
    focusOnCurrentDocument() {
        if (!this.network || !this.currentDocumentId) return;

        this.network.focus(this.currentDocumentId, {
            scale: 1.0,
            animation: {
                duration: 1000,
                easingFunction: 'easeInOutQuad'
            }
        });
    }

    /**
     * Update graph statistics display
     */
    updateStats() {
        if (!this.graph) return;

        const stats = document.getElementById('graph-stats');
        const nodeCount = this.graph.nodes ? this.graph.nodes.length : 0;
        const edgeCount = this.graph.edges ? this.graph.edges.length : 0;

        stats.textContent = `Nodes: ${nodeCount} | Edges: ${edgeCount}`;
    }

    /**
     * Show/hide loading indicator
     */
    showLoading(show) {
        const loading = document.getElementById('graph-loading');
        if (loading) {
            loading.style.display = show ? 'flex' : 'none';
        }
    }

    /**
     * Show error message
     */
    showError(message) {
        const container = document.getElementById('graph-container');
        container.innerHTML = `
            <div style="
                display: flex;
                align-items: center;
                justify-content: center;
                height: 100%;
                color: var(--b3-theme-error);
                text-align: center;
                padding: 20px;
            ">
                <div>
                    <div style="font-size: 24px; margin-bottom: 8px;">⚠️</div>
                    <div>${message}</div>
                </div>
            </div>
        `;
    }

    /**
     * Get current document ID from SiYuan
     */
    async getCurrentDocumentId() {
        // This would integrate with SiYuan's API to get the current document
        // For now, return a placeholder
        return 'current_doc_id';
    }

    /**
     * Destroy the widget and clean up resources
     */
    destroy() {
        if (this.network) {
            this.network.destroy();
            this.network = null;
        }
        this.container.innerHTML = '';
    }
}

// Export for use in SiYuan plugin
if (typeof module !== 'undefined' && module.exports) {
    module.exports = RelationshipGraphWidget;
} else if (typeof window !== 'undefined') {
    window.RelationshipGraphWidget = RelationshipGraphWidget;
}
