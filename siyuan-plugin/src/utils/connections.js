/**
 * Connection utilities for the SiYuan plugin.
 *
 * Provides functions for:
 * - Calculating connection strength indicators
 * - Formatting connection data for display
 * - Managing connection visualization state
 */

/**
 * Calculate visual strength indicator based on connection strength
 * @param {number} strength - Connection strength (0.0 to 1.0)
 * @returns {object} Visual indicator properties
 */
function getStrengthIndicator(strength) {
    if (strength >= 0.8) {
        return {
            level: 'strong',
            color: '#10b981', // green-500
            icon: '🔗',
            label: 'Strong connection',
            opacity: 1.0
        };
    } else if (strength >= 0.6) {
        return {
            level: 'medium',
            color: '#f59e0b', // amber-500
            icon: '🔗',
            label: 'Medium connection',
            opacity: 0.8
        };
    } else if (strength >= 0.3) {
        return {
            level: 'weak',
            color: '#ef4444', // red-500
            icon: '🔗',
            label: 'Weak connection',
            opacity: 0.6
        };
    } else {
        return {
            level: 'very_weak',
            color: '#9ca3af', // gray-400
            icon: '🔗',
            label: 'Very weak connection',
            opacity: 0.4
        };
    }
}

/**
 * Get connection type display properties
 * @param {string} connectionType - Type of connection
 * @returns {object} Display properties
 */
function getConnectionTypeDisplay(connectionType) {
    const types = {
        'reference': {
            icon: '📖',
            label: 'Reference',
            description: 'Direct reference to another document'
        },
        'follow_up': {
            icon: '➡️',
            label: 'Follow-up',
            description: 'Continues or builds upon previous work'
        },
        'related_concept': {
            icon: '💡',
            label: 'Related Concept',
            description: 'Conceptually related but not directly connected'
        }
    };

    return types[connectionType] || {
        icon: '❓',
        label: 'Unknown',
        description: 'Unknown connection type'
    };
}

/**
 * Format connection for display in UI
 * @param {object} connection - Raw connection data
 * @returns {object} Formatted connection data
 */
function formatConnectionForDisplay(connection) {
    const strengthIndicator = getStrengthIndicator(connection.strength);
    const typeDisplay = getConnectionTypeDisplay(connection.connection_type);

    return {
        ...connection,
        display: {
            strength: strengthIndicator,
            type: typeDisplay,
            // Truncate context if too long
            contextPreview: connection.context.length > 100
                ? connection.context.substring(0, 100) + '...'
                : connection.context,
            // Format creation date
            createdAtFormatted: new Date(connection.created_at).toLocaleDateString()
        }
    };
}

/**
 * Sort connections by strength (highest first)
 * @param {Array} connections - Array of connection objects
 * @returns {Array} Sorted connections
 */
function sortConnectionsByStrength(connections) {
    return [...connections].sort((a, b) => b.strength - a.strength);
}

/**
 * Filter connections by minimum strength
 * @param {Array} connections - Array of connection objects
 * @param {number} minStrength - Minimum strength threshold
 * @returns {Array} Filtered connections
 */
function filterConnectionsByStrength(connections, minStrength = 0.1) {
    return connections.filter(conn => conn.strength >= minStrength);
}

/**
 * Group connections by type
 * @param {Array} connections - Array of connection objects
 * @returns {object} Connections grouped by type
 */
function groupConnectionsByType(connections) {
    const groups = {
        reference: [],
        follow_up: [],
        related_concept: []
    };

    connections.forEach(conn => {
        const type = conn.connection_type;
        if (groups[type]) {
            groups[type].push(conn);
        } else {
            groups.other = groups.other || [];
            groups.other.push(conn);
        }
    });

    return groups;
}

/**
 * Calculate connection statistics
 * @param {Array} connections - Array of connection objects
 * @returns {object} Statistics
 */
function calculateConnectionStats(connections) {
    if (!connections || connections.length === 0) {
        return {
            total: 0,
            averageStrength: 0,
            typeCounts: {},
            strengthDistribution: {}
        };
    }

    const typeCounts = {};
    const strengthDistribution = {
        strong: 0,    // >= 0.8
        medium: 0,    // 0.6-0.8
        weak: 0,      // 0.3-0.6
        very_weak: 0  // < 0.3
    };

    let totalStrength = 0;

    connections.forEach(conn => {
        // Count by type
        typeCounts[conn.connection_type] = (typeCounts[conn.connection_type] || 0) + 1;

        // Count by strength
        if (conn.strength >= 0.8) {
            strengthDistribution.strong++;
        } else if (conn.strength >= 0.6) {
            strengthDistribution.medium++;
        } else if (conn.strength >= 0.3) {
            strengthDistribution.weak++;
        } else {
            strengthDistribution.very_weak++;
        }

        totalStrength += conn.strength;
    });

    return {
        total: connections.length,
        averageStrength: totalStrength / connections.length,
        typeCounts: typeCounts,
        strengthDistribution: strengthDistribution
    };
}

/**
 * Create connection visualization data
 * @param {Array} connections - Array of connection objects
 * @param {string} currentDocId - ID of current document
 * @returns {object} Visualization data
 */
function createConnectionVisualization(connections, currentDocId) {
    const nodes = new Map();
    const links = [];

    // Add current document as central node
    nodes.set(currentDocId, {
        id: currentDocId,
        type: 'current',
        label: 'Current Document',
        size: 20
    });

    // Process connections
    connections.forEach(conn => {
        const sourceId = conn.source_doc_id;
        const targetId = conn.target_doc_id;

        // Add source node if not exists
        if (!nodes.has(sourceId)) {
            nodes.set(sourceId, {
                id: sourceId,
                type: sourceId === currentDocId ? 'current' : 'source',
                label: `Doc ${sourceId.slice(-4)}`,
                size: sourceId === currentDocId ? 20 : 15
            });
        }

        // Add target node if not exists
        if (!nodes.has(targetId)) {
            nodes.set(targetId, {
                id: targetId,
                type: 'target',
                label: `Doc ${targetId.slice(-4)}`,
                size: 15
            });
        }

        // Add link
        links.push({
            source: sourceId,
            target: targetId,
            strength: conn.strength,
            type: conn.connection_type,
            context: conn.context
        });
    });

    return {
        nodes: Array.from(nodes.values()),
        links: links
    };
}

// Export functions for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        getStrengthIndicator,
        getConnectionTypeDisplay,
        formatConnectionForDisplay,
        sortConnectionsByStrength,
        filterConnectionsByStrength,
        groupConnectionsByType,
        calculateConnectionStats,
        createConnectionVisualization
    };
} else if (typeof window !== 'undefined') {
    window.ConnectionUtils = {
        getStrengthIndicator,
        getConnectionTypeDisplay,
        formatConnectionForDisplay,
        sortConnectionsByStrength,
        filterConnectionsByStrength,
        groupConnectionsByType,
        calculateConnectionStats,
        createConnectionVisualization
    };
}
