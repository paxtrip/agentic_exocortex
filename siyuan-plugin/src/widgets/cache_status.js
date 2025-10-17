/**
 * Cache Status Widget for SiYuan Plugin
 *
 * Displays caching indicators and refresh functionality for the Unified RAG System.
 * Shows when results are from cache vs fresh queries, with manual refresh options.
 */

class CacheStatusWidget {
    constructor(apiClient) {
        this.apiClient = apiClient;
        this.currentQuery = null;
        this.cacheStatus = 'unknown'; // 'cached', 'fresh', 'stale', 'unknown'
        this.lastUpdate = null;
        this.container = null;
    }

    /**
     * Render the cache status widget
     */
    render(container) {
        this.container = container;

        const widgetHtml = `
            <div class="cache-status-widget">
                <div class="cache-indicator">
                    <span class="cache-icon" id="cache-icon">⏳</span>
                    <span class="cache-text" id="cache-text">Проверка кэша...</span>
                </div>
                <div class="cache-controls">
                    <button class="refresh-btn" id="refresh-btn" title="Обновить результаты">
                        🔄
                    </button>
                    <button class="clear-cache-btn" id="clear-cache-btn" title="Очистить кэш для этого запроса">
                        🗑️
                    </button>
                </div>
                <div class="cache-details" id="cache-details" style="display: none;">
                    <small id="cache-timestamp"></small>
                </div>
            </div>
        `;

        container.innerHTML = widgetHtml;
        this.attachEventListeners();
        this.updateDisplay();
    }

    /**
     * Attach event listeners to buttons
     */
    attachEventListeners() {
        const refreshBtn = this.container.querySelector('#refresh-btn');
        const clearCacheBtn = this.container.querySelector('#clear-cache-btn');

        refreshBtn.addEventListener('click', () => this.handleRefresh());
        clearCacheBtn.addEventListener('click', () => this.handleClearCache());
    }

    /**
     * Update the cache status and display
     */
    updateStatus(status, timestamp = null, query = null) {
        this.cacheStatus = status;
        this.lastUpdate = timestamp;
        this.currentQuery = query;
        this.updateDisplay();
    }

    /**
     * Update the visual display based on current status
     */
    updateDisplay() {
        if (!this.container) return;

        const icon = this.container.querySelector('#cache-icon');
        const text = this.container.querySelector('#cache-text');
        const details = this.container.querySelector('#cache-details');
        const timestamp = this.container.querySelector('#cache-timestamp');

        // Update icon and text based on status
        switch (this.cacheStatus) {
            case 'cached':
                icon.textContent = '💾';
                text.textContent = 'Из кэша';
                text.style.color = '#28a745'; // Green
                break;
            case 'fresh':
                icon.textContent = '🆕';
                text.textContent = 'Свежие данные';
                text.style.color = '#007bff'; // Blue
                break;
            case 'stale':
                icon.textContent = '⚠️';
                text.textContent = 'Устаревшие данные';
                text.style.color = '#ffc107'; // Yellow
                break;
            case 'unknown':
            default:
                icon.textContent = '❓';
                text.textContent = 'Статус неизвестен';
                text.style.color = '#6c757d'; // Gray
                break;
        }

        // Show timestamp if available
        if (this.lastUpdate) {
            const timeAgo = this.getTimeAgo(this.lastUpdate);
            timestamp.textContent = `Обновлено ${timeAgo}`;
            details.style.display = 'block';
        } else {
            details.style.display = 'none';
        }
    }

    /**
     * Handle refresh button click
     */
    async handleRefresh() {
        if (!this.currentQuery) {
            this.showNotification('Нет активного запроса для обновления', 'warning');
            return;
        }

        try {
            // Disable button during refresh
            const refreshBtn = this.container.querySelector('#refresh-btn');
            refreshBtn.disabled = true;
            refreshBtn.textContent = '⏳';

            // Trigger new search (this would call the parent component's search method)
            if (this.onRefresh) {
                await this.onRefresh(this.currentQuery);
            }

            this.showNotification('Результаты обновлены', 'success');

        } catch (error) {
            console.error('Refresh failed:', error);
            this.showNotification('Ошибка обновления', 'error');
        } finally {
            // Re-enable button
            const refreshBtn = this.container.querySelector('#refresh-btn');
            refreshBtn.disabled = false;
            refreshBtn.textContent = '🔄';
        }
    }

    /**
     * Handle clear cache button click
     */
    async handleClearCache() {
        if (!this.currentQuery) {
            this.showNotification('Нет кэша для очистки', 'warning');
            return;
        }

        try {
            // Call API to clear cache for this query
            await this.apiClient.clearCache(this.currentQuery);

            this.updateStatus('unknown');
            this.showNotification('Кэш очищен', 'success');

        } catch (error) {
            console.error('Clear cache failed:', error);
            this.showNotification('Ошибка очистки кэша', 'error');
        }
    }

    /**
     * Set callback for refresh action
     */
    setRefreshCallback(callback) {
        this.onRefresh = callback;
    }

    /**
     * Get human-readable time ago string
     */
    getTimeAgo(timestamp) {
        if (!timestamp) return '';

        const now = new Date();
        const time = new Date(timestamp);
        const diffMs = now - time;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);

        if (diffMins < 1) return 'только что';
        if (diffMins < 60) return `${diffMins} мин назад`;
        if (diffHours < 24) return `${diffHours} ч назад`;
        return `${diffDays} д назад`;
    }

    /**
     * Show notification to user
     */
    showNotification(message, type = 'info') {
        // This would integrate with SiYuan's notification system
        // For now, just log to console
        console.log(`[${type.toUpperCase()}] ${message}`);

        // You could also dispatch a custom event for the parent component
        if (this.container) {
            const event = new CustomEvent('cache-notification', {
                detail: { message, type }
            });
            this.container.dispatchEvent(event);
        }
    }

    /**
     * Check if results are stale (older than threshold)
     */
    isStale(thresholdMinutes = 30) {
        if (!this.lastUpdate) return false;

        const now = new Date();
        const updateTime = new Date(this.lastUpdate);
        const diffMs = now - updateTime;
        const diffMins = diffMs / 60000;

        return diffMins > thresholdMinutes;
    }

    /**
     * Auto-update status if stale
     */
    checkAndUpdateStaleStatus() {
        if (this.cacheStatus === 'cached' && this.isStale()) {
            this.updateStatus('stale', this.lastUpdate, this.currentQuery);
        }
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CacheStatusWidget;
}
