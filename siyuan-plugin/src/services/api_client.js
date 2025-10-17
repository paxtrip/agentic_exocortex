/**
 * API client for communicating with the Unified RAG System backend.
 *
 * Handles HTTP requests to the backend API with proper error handling
 * and connection management for the SiYuan plugin.
 */

class ApiClient {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl.replace(/\/$/, ''); // Remove trailing slash
        this.timeout = 10000; // 10 second timeout
    }

    /**
     * Make HTTP request to backend API
     * @param {string} endpoint - API endpoint (e.g., '/timeline')
     * @param {object} data - Request data
     * @param {string} method - HTTP method (default: 'POST')
     * @returns {Promise<object>} Response data
     */
    async request(endpoint, data = {}, method = 'POST') {
        const url = `${this.baseUrl}${endpoint}`;

        try {
            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                },
                body: method !== 'GET' ? JSON.stringify(data) : undefined,
                signal: AbortSignal.timeout(this.timeout)
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API request failed for ${endpoint}:`, error);

            // Return graceful degradation response
            return {
                error: true,
                message: error.message,
                data: []
            };
        }
    }

    /**
     * Get research timeline for a topic
     * @param {string} topic - Research topic
     * @param {object} options - Additional query options
     * @returns {Promise<object>} Timeline data
     */
    async getTimeline(topic, options = {}) {
        const query = {
            topic: topic,
            max_connections: options.maxConnections || 50,
            ...options
        };

        return await this.request('/timeline', query);
    }

    /**
     * Get connections for a specific document
     * @param {string} docId - Document ID
     * @param {object} options - Query options
     * @returns {Promise<object>} Connection data
     */
    async getConnections(docId, options = {}) {
        const query = {
            max_hops: options.maxHops || 3,
            min_strength: options.minStrength || 0.1
        };

        return await this.request(`/connections/${encodeURIComponent(docId)}`, query, 'GET');
    }

    /**
     * Ingest a document into the system
     * @param {object} document - Document data
     * @returns {Promise<object>} Ingestion result
     */
    async ingestDocument(document) {
        return await this.request('/documents/ingest', document);
    }

    /**
     * Health check for backend
     * @returns {Promise<object>} Health status
     */
    async healthCheck() {
        return await this.request('/health', {}, 'GET');
    }

    /**
     * Test connection to backend
     * @returns {Promise<boolean>} Connection status
     */
    async testConnection() {
        try {
            const health = await this.healthCheck();
            return !health.error && health.status === 'healthy';
        } catch (error) {
            return false;
        }
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ApiClient;
} else if (typeof window !== 'undefined') {
    window.ApiClient = ApiClient;
}
