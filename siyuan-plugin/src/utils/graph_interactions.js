/**
 * Graph Interaction Controls for SiYuan Plugin
 *
 * This utility provides advanced interaction controls for relationship graphs,
 * enabling writers to explore and manipulate idea connections effectively.
 *
 * Supports User Story 3: Writer Discovering Idea Connections
 */

class GraphInteractionControls {
    constructor(network, graphWidget) {
        this.network = network;
        this.graphWidget = graphWidget;
        this.selectedNodes = new Set();
        this.selectedEdges = new Set();
        this.interactionMode = 'explore'; // 'explore', 'select', 'connect'
        this.history = [];
        this.historyIndex = -1;
    }

    /**
     * Initialize interaction controls
     */
    init() {
        this.setupKeyboardShortcuts();
        this.setupMouseInteractions();
        this.setupContextMenu();
        this.createInteractionToolbar();
    }

    /**
     * Setup keyboard shortcuts for graph interactions
     */
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (event) => {
            // Only handle shortcuts when graph is focused
            if (!this.isGraphFocused()) return;

            switch (event.key) {
                case 'Escape':
                    this.clearSelection();
                    break;
                case 'Delete':
                case 'Backspace':
                    this.deleteSelected();
                    break;
                case 'z':
                    if (event.ctrlKey || event.metaKey) {
                        event.preventDefault();
                        this.undo();
                    }
                    break;
                case 'y':
                    if (event.ctrlKey || event.metaKey) {
                        event.preventDefault();
                        this.redo();
                    }
                    break;
                case 'a':
                    if (event.ctrlKey || event.metaKey) {
                        event.preventDefault();
                        this.selectAll();
                    }
                    break;
                case 'f':
                    if (event.ctrlKey || event.metaKey) {
                        event.preventDefault();
                        this.fitToView();
                    }
                    break;
                case '1':
                    this.setInteractionMode('explore');
                    break;
                case '2':
                    this.setInteractionMode('select');
                    break;
                case '3':
                    this.setInteractionMode('connect');
                    break;
            }
        });
    }

    /**
     * Setup enhanced mouse interactions
     */
    setupMouseInteractions() {
        // Double-click to expand node relationships
        this.network.on('doubleClick', (params) => {
            if (params.nodes.length > 0) {
                this.expandNodeRelationships(params.nodes[0]);
            }
        });

        // Right-click for context menu
        this.network.on('oncontext', (params) => {
            params.event.preventDefault();
            this.showContextMenu(params);
        });

        // Drag selection for multiple nodes
        let dragStart = null;
        this.network.on('dragStart', (params) => {
            if (this.interactionMode === 'select') {
                dragStart = params.pointer.canvas;
            }
        });

        this.network.on('dragEnd', (params) => {
            if (this.interactionMode === 'select' && dragStart) {
                const dragEnd = params.pointer.canvas;
                this.selectNodesInRectangle(dragStart, dragEnd);
                dragStart = null;
            }
        });

        // Hover effects
        this.network.on('hoverNode', (params) => {
            this.highlightConnectedNodes(params.node, true);
        });

        this.network.on('blurNode', (params) => {
            this.highlightConnectedNodes(params.node, false);
        });
    }

    /**
     * Setup context menu for graph interactions
     */
    setupContextMenu() {
        // Create context menu element
        this.contextMenu = document.createElement('div');
        this.contextMenu.className = 'graph-context-menu';
        this.contextMenu.style.cssText = `
            position: absolute;
            background: var(--b3-theme-surface);
            border: 1px solid var(--b3-theme-surface-lighter);
            border-radius: 4px;
            padding: 4px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            z-index: 1000;
            display: none;
            font-size: 12px;
            min-width: 150px;
        `;
        document.body.appendChild(this.contextMenu);

        // Hide context menu when clicking elsewhere
        document.addEventListener('click', () => {
            this.hideContextMenu();
        });
    }

    /**
     * Create interaction toolbar
     */
    createInteractionToolbar() {
        const toolbar = document.createElement('div');
        toolbar.className = 'graph-interaction-toolbar';
        toolbar.innerHTML = `
            <div class="toolbar-section">
                <button id="mode-explore" class="toolbar-btn active" title="Explore Mode">
                    🔍 Explore
                </button>
                <button id="mode-select" class="toolbar-btn" title="Select Mode">
                    □ Select
                </button>
                <button id="mode-connect" class="toolbar-btn" title="Connect Mode">
                    ➕ Connect
                </button>
            </div>
            <div class="toolbar-section">
                <button id="zoom-in" class="toolbar-btn" title="Zoom In">+</button>
                <button id="zoom-out" class="toolbar-btn" title="Zoom Out">−</button>
                <button id="fit-view" class="toolbar-btn" title="Fit to View">⛶</button>
            </div>
            <div class="toolbar-section">
                <button id="undo" class="toolbar-btn" title="Undo">↶</button>
                <button id="redo" class="toolbar-btn" title="Redo">↷</button>
            </div>
        `;

        // Add styles
        const style = document.createElement('style');
        style.textContent = `
            .graph-interaction-toolbar {
                display: flex;
                gap: 12px;
                padding: 8px;
                background: var(--b3-theme-surface-lighter);
                border-radius: 4px;
                margin-bottom: 8px;
            }

            .toolbar-section {
                display: flex;
                gap: 4px;
            }

            .toolbar-btn {
                padding: 4px 8px;
                border: 1px solid var(--b3-theme-surface-lighter);
                background: var(--b3-theme-background);
                color: var(--b3-theme-on-background);
                border-radius: 3px;
                cursor: pointer;
                font-size: 11px;
                min-width: 24px;
            }

            .toolbar-btn:hover {
                background: var(--b3-theme-surface);
            }

            .toolbar-btn.active {
                background: var(--b3-theme-primary);
                color: var(--b3-theme-on-primary);
                border-color: var(--b3-theme-primary);
            }

            .graph-context-menu {
                position: absolute;
                background: var(--b3-theme-surface);
                border: 1px solid var(--b3-theme-surface-lighter);
                border-radius: 4px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.15);
                z-index: 1000;
                font-size: 12px;
                min-width: 150px;
            }

            .context-menu-item {
                padding: 6px 12px;
                cursor: pointer;
                color: var(--b3-theme-on-surface);
            }

            .context-menu-item:hover {
                background: var(--b3-theme-surface-lighter);
            }

            .context-menu-separator {
                height: 1px;
                background: var(--b3-theme-surface-lighter);
                margin: 2px 0;
            }
        `;
        document.head.appendChild(style);

        // Insert toolbar before the graph container
        const graphContainer = document.getElementById('graph-container');
        graphContainer.parentNode.insertBefore(toolbar, graphContainer);

        // Setup toolbar event listeners
        this.setupToolbarListeners();
    }

    /**
     * Setup toolbar button listeners
     */
    setupToolbarListeners() {
        // Mode buttons
        document.getElementById('mode-explore').addEventListener('click', () => {
            this.setInteractionMode('explore');
        });

        document.getElementById('mode-select').addEventListener('click', () => {
            this.setInteractionMode('select');
        });

        document.getElementById('mode-connect').addEventListener('click', () => {
            this.setInteractionMode('connect');
        });

        // Zoom buttons
        document.getElementById('zoom-in').addEventListener('click', () => {
            this.zoomIn();
        });

        document.getElementById('zoom-out').addEventListener('click', () => {
            this.zoomOut();
        });

        document.getElementById('fit-view').addEventListener('click', () => {
            this.fitToView();
        });

        // History buttons
        document.getElementById('undo').addEventListener('click', () => {
            this.undo();
        });

        document.getElementById('redo').addEventListener('click', () => {
            this.redo();
        });
    }

    /**
     * Set interaction mode
     */
    setInteractionMode(mode) {
        this.interactionMode = mode;

        // Update toolbar button states
        ['mode-explore', 'mode-select', 'mode-connect'].forEach(id => {
            const btn = document.getElementById(id);
            btn.classList.remove('active');
        });

        document.getElementById(`mode-${mode}`).classList.add('active');

        // Update network interaction settings
        this.updateNetworkInteraction();
    }

    /**
     * Update network interaction settings based on mode
     */
    updateNetworkInteraction() {
        const options = {
            interaction: {
                dragNodes: this.interactionMode !== 'explore',
                dragView: true,
                zoomView: true,
                selectConnectedEdges: this.interactionMode === 'select'
            }
        };

        this.network.setOptions(options);
    }

    /**
     * Check if graph container is focused
     */
    isGraphFocused() {
        const graphContainer = document.getElementById('graph-container');
        return graphContainer && graphContainer.contains(document.activeElement);
    }

    /**
     * Clear current selection
     */
    clearSelection() {
        this.selectedNodes.clear();
        this.selectedEdges.clear();
        this.network.selectNodes([]);
        this.network.selectEdges([]);
        this.updateSelectionInfo();
    }

    /**
     * Delete selected nodes and edges
     */
    deleteSelected() {
        if (this.selectedNodes.size === 0 && this.selectedEdges.size === 0) return;

        this.saveToHistory();

        // Remove selected nodes and their edges
        const nodesToRemove = Array.from(this.selectedNodes);
        const edgesToRemove = Array.from(this.selectedEdges);

        this.network.deleteSelected();

        // Update graph data
        this.graphWidget.graph.nodes = this.graphWidget.graph.nodes.filter(
            node => !nodesToRemove.includes(node.id)
        );
        this.graphWidget.graph.edges = this.graphWidget.graph.edges.filter(
            edge => !edgesToRemove.includes(edge.id)
        );

        this.clearSelection();
        this.graphWidget.updateStats();
    }

    /**
     * Select all nodes
     */
    selectAll() {
        const allNodeIds = this.network.body.data.nodes.getIds();
        this.network.selectNodes(allNodeIds);
        this.selectedNodes = new Set(allNodeIds);
        this.updateSelectionInfo();
    }

    /**
     * Fit graph to view
     */
    fitToView() {
        this.network.fit({
            animation: {
                duration: 1000,
                easingFunction: 'easeInOutQuad'
            }
        });
    }

    /**
     * Zoom in
     */
    zoomIn() {
        const scale = this.network.getScale();
        this.network.moveTo({
            scale: scale * 1.2,
            animation: {
                duration: 300,
                easingFunction: 'easeInOutQuad'
            }
        });
    }

    /**
     * Zoom out
     */
    zoomOut() {
        const scale = this.network.getScale();
        this.network.moveTo({
            scale: scale / 1.2,
            animation: {
                duration: 300,
                easingFunction: 'easeInOutQuad'
            }
        });
    }

    /**
     * Expand relationships for a node
     */
    async expandNodeRelationships(nodeId) {
        try {
            // Fetch additional relationships for this node
            const response = await fetch(`/api/relationships/${nodeId}`);
            if (!response.ok) return;

            const data = await response.json();

            // Add new relationships to graph
            for (const rel of data.relationships) {
                const newEdge = {
                    from: nodeId,
                    to: rel.target_id,
                    label: `${rel.relationship_type} (${rel.confidence.toFixed(2)})`,
                    context: rel.context,
                    strength: rel.confidence,
                    type: rel.relationship_type
                };

                // Check if edge already exists
                const existingEdge = this.graphWidget.graph.edges.find(
                    e => e.from === newEdge.from && e.to === newEdge.to
                );

                if (!existingEdge) {
                    this.graphWidget.graph.edges.push(newEdge);
                }
            }

            // Update network
            this.graphWidget.initializeNetwork();
            this.graphWidget.updateStats();

        } catch (error) {
            console.error('Failed to expand node relationships:', error);
        }
    }

    /**
     * Select nodes within a rectangle
     */
    selectNodesInRectangle(start, end) {
        const canvas = this.network.canvas;
        const rect = {
            top: Math.min(start.y, end.y),
            left: Math.min(start.x, end.x),
            bottom: Math.max(start.y, end.y),
            right: Math.max(start.x, end.x)
        };

        const selectedNodes = [];
        const nodePositions = this.network.getPositions();

        for (const [nodeId, position] of Object.entries(nodePositions)) {
            if (position.x >= rect.left && position.x <= rect.right &&
                position.y >= rect.top && position.y <= rect.bottom) {
                selectedNodes.push(nodeId);
            }
        }

        this.network.selectNodes(selectedNodes);
        this.selectedNodes = new Set(selectedNodes);
        this.updateSelectionInfo();
    }

    /**
     * Highlight connected nodes
     */
    highlightConnectedNodes(nodeId, highlight) {
        if (!highlight) {
            // Reset all highlights
            this.network.body.data.nodes.update(
                this.network.body.data.nodes.get().map(node => ({
                    id: node.id,
                    color: this.graphWidget.getNodeColor(node)
                }))
            );
            return;
        }

        const connectedNodes = new Set([nodeId]);
        const connectedEdges = this.network.getConnectedEdges(nodeId);

        // Find all nodes connected to the hovered node
        for (const edgeId of connectedEdges) {
            const edge = this.network.body.data.edges.get(edgeId);
            connectedNodes.add(edge.from);
            connectedNodes.add(edge.to);
        }

        // Update node colors
        const updates = [];
        this.network.body.data.nodes.forEach(node => {
            const isConnected = connectedNodes.has(node.id);
            updates.push({
                id: node.id,
                color: isConnected ?
                    { background: 'var(--b3-theme-tertiary)', border: 'var(--b3-theme-tertiary)' } :
                    this.graphWidget.getNodeColor(node)
            });
        });

        this.network.body.data.nodes.update(updates);
    }

    /**
     * Show context menu
     */
    showContextMenu(params) {
        this.contextMenu.innerHTML = '';

        if (params.nodes.length > 0) {
            // Node context menu
            this.addContextMenuItem('Expand Relationships', () => {
                this.expandNodeRelationships(params.nodes[0]);
            });
            this.addContextMenuItem('Focus on Node', () => {
                this.network.focus(params.nodes[0]);
            });
            this.addContextMenuSeparator();
            this.addContextMenuItem('Delete Node', () => {
                this.network.deleteSelected();
            });
        } else if (params.edges.length > 0) {
            // Edge context menu
            this.addContextMenuItem('Delete Relationship', () => {
                this.network.deleteSelected();
            });
        } else {
            // Canvas context menu
            this.addContextMenuItem('Fit to View', () => this.fitToView());
            this.addContextMenuItem('Clear Selection', () => this.clearSelection());
        }

        // Position and show menu
        this.contextMenu.style.left = params.pointer.DOM.x + 'px';
        this.contextMenu.style.top = params.pointer.DOM.y + 'px';
        this.contextMenu.style.display = 'block';
    }

    /**
     * Hide context menu
     */
    hideContextMenu() {
        this.contextMenu.style.display = 'none';
    }

    /**
     * Add item to context menu
     */
    addContextMenuItem(label, callback) {
        const item = document.createElement('div');
        item.className = 'context-menu-item';
        item.textContent = label;
        item.addEventListener('click', () => {
            callback();
            this.hideContextMenu();
        });
        this.contextMenu.appendChild(item);
    }

    /**
     * Add separator to context menu
     */
    addContextMenuSeparator() {
        const separator = document.createElement('div');
        separator.className = 'context-menu-separator';
        this.contextMenu.appendChild(separator);
    }

    /**
     * Update selection info display
     */
    updateSelectionInfo() {
        const info = document.getElementById('selected-info');
        if (!info) return;

        const nodeCount = this.selectedNodes.size;
        const edgeCount = this.selectedEdges.size;

        if (nodeCount === 0 && edgeCount === 0) {
            info.textContent = 'Click on nodes to see details';
        } else {
            const parts = [];
            if (nodeCount > 0) parts.push(`${nodeCount} node${nodeCount > 1 ? 's' : ''}`);
            if (edgeCount > 0) parts.push(`${edgeCount} relationship${edgeCount > 1 ? 's' : ''}`);
            info.textContent = `Selected: ${parts.join(', ')}`;
        }
    }

    /**
     * Save current state to history
     */
    saveToHistory() {
        const state = {
            nodes: this.network.body.data.nodes.get(),
            edges: this.network.body.data.edges.get(),
            selectedNodes: Array.from(this.selectedNodes),
            selectedEdges: Array.from(this.selectedEdges)
        };

        // Remove future history if we're not at the end
        this.history = this.history.slice(0, this.historyIndex + 1);

        this.history.push(state);
        this.historyIndex = this.history.length - 1;

        // Limit history size
        if (this.history.length > 50) {
            this.history.shift();
            this.historyIndex--;
        }

        this.updateHistoryButtons();
    }

    /**
     * Undo last action
     */
    undo() {
        if (this.historyIndex > 0) {
            this.historyIndex--;
            this.restoreFromHistory();
        }
    }

    /**
     * Redo next action
     */
    redo() {
        if (this.historyIndex < this.history.length - 1) {
            this.historyIndex++;
            this.restoreFromHistory();
        }
    }

    /**
     * Restore state from history
     */
    restoreFromHistory() {
        const state = this.history[this.historyIndex];
        if (!state) return;

        this.network.body.data.nodes.update(state.nodes);
        this.network.body.data.edges.update(state.edges);

        this.selectedNodes = new Set(state.selectedNodes);
        this.selectedEdges = new Set(state.selectedEdges);

        this.network.selectNodes(state.selectedNodes);
        this.network.selectEdges(state.selectedEdges);

        this.updateHistoryButtons();
        this.updateSelectionInfo();
    }

    /**
     * Update history button states
     */
    updateHistoryButtons() {
        const undoBtn = document.getElementById('undo');
        const redoBtn = document.getElementById('redo');

        if (undoBtn) {
            undoBtn.disabled = this.historyIndex <= 0;
            undoBtn.style.opacity = undoBtn.disabled ? 0.5 : 1;
        }

        if (redoBtn) {
            redoBtn.disabled = this.historyIndex >= this.history.length - 1;
            redoBtn.style.opacity = redoBtn.disabled ? 0.5 : 1;
        }
    }

    /**
     * Destroy interaction controls
     */
    destroy() {
        // Remove event listeners
        document.removeEventListener('keydown', this.keyboardHandler);

        // Remove context menu
        if (this.contextMenu && this.contextMenu.parentNode) {
            this.contextMenu.parentNode.removeChild(this.contextMenu);
        }

        // Clear references
        this.network = null;
        this.graphWidget = null;
        this.selectedNodes.clear();
        this.selectedEdges.clear();
        this.history = [];
    }
}

// Export for use in SiYuan plugin
if (typeof module !== 'undefined' && module.exports) {
    module.exports = GraphInteractionControls;
} else if (typeof window !== 'undefined') {
    window.GraphInteractionControls = GraphInteractionControls;
}
