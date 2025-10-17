/**
 * Export Utilities for SiYuan Plugin
 *
 * Provides functionality to export search results, citations, and traces
 * in various formats (JSON, Markdown, CSV, PDF).
 */

class Exporter {
    constructor(apiClient) {
        this.apiClient = apiClient;
    }

    /**
     * Export search results to different formats
     */
    async exportResults(results, format = 'markdown', options = {}) {
        switch (format.toLowerCase()) {
            case 'markdown':
                return this.exportToMarkdown(results, options);
            case 'json':
                return this.exportToJson(results, options);
            case 'csv':
                return this.exportToCsv(results, options);
            case 'pdf':
                return this.exportToPdf(results, options);
            default:
                throw new Error(`Unsupported export format: ${format}`);
        }
    }

    /**
     * Export to Markdown format
     */
    exportToMarkdown(results, options = {}) {
        const { includeMetadata = true, includeCitations = true } = options;

        let markdown = `# Результаты поиска\n\n`;
        markdown += `**Запрос:** ${results.query || 'Не указан'}\n\n`;
        markdown += `**Найдено результатов:** ${results.total_found || 0}\n\n`;
        markdown += `**Дата экспорта:** ${new Date().toLocaleString('ru-RU')}\n\n`;

        if (results.results && results.results.length > 0) {
            markdown += `## Результаты\n\n`;

            results.results.forEach((result, index) => {
                markdown += `### ${index + 1}. ${result.title || 'Без названия'}\n\n`;

                if (result.content) {
                    markdown += `${result.content}\n\n`;
                }

                if (includeMetadata && result.metadata) {
                    markdown += `**Метаданные:**\n`;
                    Object.entries(result.metadata).forEach(([key, value]) => {
                        markdown += `- ${key}: ${value}\n`;
                    });
                    markdown += `\n`;
                }

                if (includeCitations && result.citations) {
                    markdown += `**Цитаты:**\n`;
                    result.citations.forEach(citation => {
                        markdown += `- ${citation}\n`;
                    });
                    markdown += `\n`;
                }

                markdown += `---\n\n`;
            });
        }

        return {
            content: markdown,
            filename: `search_results_${Date.now()}.md`,
            mimeType: 'text/markdown'
        };
    }

    /**
     * Export to JSON format
     */
    exportToJson(results, options = {}) {
        const exportData = {
            query: results.query,
            total_found: results.total_found,
            exported_at: new Date().toISOString(),
            results: results.results || [],
            metadata: {
                exporter: 'SiYuan RAG Plugin',
                version: '1.0.0'
            }
        };

        return {
            content: JSON.stringify(exportData, null, 2),
            filename: `search_results_${Date.now()}.json`,
            mimeType: 'application/json'
        };
    }

    /**
     * Export to CSV format
     */
    exportToCsv(results, options = {}) {
        const { includeMetadata = false } = options;

        let csv = 'Title,Content,Score,Source\n';

        if (results.results && results.results.length > 0) {
            results.results.forEach(result => {
                const title = (result.title || '').replace(/"/g, '""');
                const content = (result.content || '').replace(/"/g, '""').substring(0, 500); // Limit content length
                const score = result.score || 0;
                const source = result.source || '';

                csv += `"${title}","${content}",${score},"${source}"\n`;

                if (includeMetadata && result.metadata) {
                    // Add metadata rows
                    Object.entries(result.metadata).forEach(([key, value]) => {
                        csv += `"Metadata: ${key}","${value}",,\n`;
                    });
                }
            });
        }

        return {
            content: csv,
            filename: `search_results_${Date.now()}.csv`,
            mimeType: 'text/csv'
        };
    }

    /**
     * Export to PDF format (placeholder - would require PDF library)
     */
    exportToPdf(results, options = {}) {
        // This would require a PDF generation library like jsPDF
        // For now, return markdown that can be converted to PDF
        const markdownExport = this.exportToMarkdown(results, options);

        return {
            content: markdownExport.content,
            filename: `search_results_${Date.now()}.pdf`,
            mimeType: 'application/pdf',
            note: 'PDF export requires additional library. Use markdown version for now.'
        };
    }

    /**
     * Export thinking trace to readable format
     */
    async exportTrace(traceId, format = 'markdown') {
        try {
            const trace = await this.apiClient.getTrace(traceId);
            if (!trace) {
                throw new Error(`Trace ${traceId} not found`);
            }

            switch (format.toLowerCase()) {
                case 'markdown':
                    return this.exportTraceToMarkdown(trace);
                case 'json':
                    return this.exportTraceToJson(trace);
                default:
                    throw new Error(`Unsupported trace export format: ${format}`);
            }
        } catch (error) {
            console.error('Failed to export trace:', error);
            throw error;
        }
    }

    /**
     * Export trace to Markdown
     */
    exportTraceToMarkdown(trace) {
        let markdown = `# Анализ рассуждений\n\n`;
        markdown += `**ID трассировки:** ${trace.trace_id}\n\n`;
        markdown += `**Запрос:** ${trace.query}\n\n`;
        markdown += `**Итоговый ответ:** ${trace.final_answer}\n\n`;
        markdown += `**Общая уверенность:** ${(trace.overall_confidence * 100).toFixed(1)}%\n\n`;
        markdown += `**Уровень уверенности:** ${this.translateConfidenceLevel(trace.confidence_level)}\n\n`;
        markdown += `**Провайдер:** ${trace.provider_used || 'Не указан'}\n\n`;
        markdown += `**Уровень деградации:** ${this.translateDegradationLevel(trace.degradation_level)}\n\n`;
        markdown += `**Общее время:** ${trace.total_duration_ms}ms\n\n`;
        markdown += `**Время создания:** ${new Date(trace.created_at).toLocaleString('ru-RU')}\n\n`;

        if (trace.steps && trace.steps.length > 0) {
            markdown += `## Шаги рассуждений\n\n`;

            trace.steps.forEach((step, index) => {
                markdown += `### Шаг ${index + 1}: ${this.translateStepType(step.step_type)}\n\n`;
                markdown += `**Описание:** ${step.description}\n\n`;
                markdown += `**Уверенность:** ${(step.confidence * 100).toFixed(1)}%\n\n`;
                markdown += `**Время выполнения:** ${step.duration_ms}ms\n\n`;
                markdown += `**Время:** ${new Date(step.timestamp).toLocaleString('ru-RU')}\n\n`;

                if (step.input_data && Object.keys(step.input_data).length > 0) {
                    markdown += `**Входные данные:**\n\`\`\`json\n${JSON.stringify(step.input_data, null, 2)}\n\`\`\`\n\n`;
                }

                if (step.output_data && Object.keys(step.output_data).length > 0) {
                    markdown += `**Выходные данные:**\n\`\`\`json\n${JSON.stringify(step.output_data, null, 2)}\n\`\`\`\n\n`;
                }

                if (step.metadata) {
                    markdown += `**Метаданные:**\n\`\`\`json\n${JSON.stringify(step.metadata, null, 2)}\n\`\`\`\n\n`;
                }

                markdown += `---\n\n`;
            });
        }

        return {
            content: markdown,
            filename: `thinking_trace_${trace.trace_id}.md`,
            mimeType: 'text/markdown'
        };
    }

    /**
     * Export trace to JSON
     */
    exportTraceToJson(trace) {
        return {
            content: JSON.stringify(trace, null, 2),
            filename: `thinking_trace_${trace.trace_id}.json`,
            mimeType: 'application/json'
        };
    }

    /**
     * Export citations in various formats
     */
    exportCitations(results, format = 'markdown', style = 'apa') {
        const citations = this.extractCitations(results);

        switch (format.toLowerCase()) {
            case 'markdown':
                return this.exportCitationsToMarkdown(citations, style);
            case 'bibtex':
                return this.exportCitationsToBibTeX(citations);
            default:
                throw new Error(`Unsupported citation format: ${format}`);
        }
    }

    /**
     * Extract citations from results
     */
    extractCitations(results) {
        const citations = [];

        if (results.results) {
            results.results.forEach(result => {
                if (result.citations) {
                    citations.push(...result.citations);
                }
                // Generate citation from result metadata
                if (result.title && result.source) {
                    citations.push({
                        title: result.title,
                        source: result.source,
                        url: result.url,
                        accessed: new Date().toISOString().split('T')[0]
                    });
                }
            });
        }

        return citations;
    }

    /**
     * Export citations to Markdown
     */
    exportCitationsToMarkdown(citations, style) {
        let markdown = `# Список литературы\n\n`;
        markdown += `**Стиль цитирования:** ${style.toUpperCase()}\n\n`;
        markdown += `**Дата экспорта:** ${new Date().toLocaleString('ru-RU')}\n\n`;

        citations.forEach((citation, index) => {
            markdown += `${index + 1}. ${this.formatCitation(citation, style)}\n\n`;
        });

        return {
            content: markdown,
            filename: `citations_${Date.now()}.md`,
            mimeType: 'text/markdown'
        };
    }

    /**
     * Export citations to BibTeX
     */
    exportCitationsToBibTeX(citations) {
        let bibtex = '% BibTeX citations\n\n';

        citations.forEach((citation, index) => {
            const key = `citation_${index + 1}`;
            bibtex += `@misc{${key},\n`;
            bibtex += `  title={${citation.title || 'Untitled'}},\n`;
            if (citation.source) bibtex += `  author={${citation.source}},\n`;
            if (citation.url) bibtex += `  url={${citation.url}},\n`;
            bibtex += `  year={${new Date().getFullYear()}}\n`;
            bibtex += `}\n\n`;
        });

        return {
            content: bibtex,
            filename: `citations_${Date.now()}.bib`,
            mimeType: 'application/x-bibtex'
        };
    }

    /**
     * Format a single citation
     */
    formatCitation(citation, style) {
        const title = citation.title || 'Без названия';
        const source = citation.source || 'Неизвестный источник';
        const year = citation.year || new Date().getFullYear();

        switch (style.toLowerCase()) {
            case 'apa':
                return `${source} (${year}). ${title}.`;
            case 'mla':
                return `${source}. "${title}." ${year}.`;
            case 'chicago':
                return `${source}. "${title}." ${year}.`;
            default:
                return `${source}. ${title} (${year}).`;
        }
    }

    /**
     * Helper methods for translations
     */
    translateConfidenceLevel(level) {
        const translations = {
            'high': 'Высокая',
            'medium': 'Средняя',
            'low': 'Низкая'
        };
        return translations[level] || level;
    }

    translateDegradationLevel(level) {
        const translations = {
            'llm': 'LLM генерация',
            'qa': 'Извлечение ответов',
            'search': 'Поиск результатов'
        };
        return translations[level] || level;
    }

    translateStepType(stepType) {
        const translations = {
            'llm_generation': 'Генерация LLM',
            'extractive_qa': 'Извлечение ответов',
            'vector_search': 'Векторный поиск',
            'fts_search': 'Полнотекстовый поиск',
            'reranking': 'Переранжирование',
            'connection_discovery': 'Поиск связей',
            'semantic_analysis': 'Семантический анализ'
        };
        return translations[stepType] || stepType;
    }

    /**
     * Download exported content
     */
    download(exportResult) {
        const blob = new Blob([exportResult.content], { type: exportResult.mimeType });
        const url = URL.createObjectURL(blob);

        const a = document.createElement('a');
        a.href = url;
        a.download = exportResult.filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);

        URL.revokeObjectURL(url);
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Exporter;
}
