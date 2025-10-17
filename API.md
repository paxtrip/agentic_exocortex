# API Documentation - Unified RAG System

## Обзор

API системы Unified RAG предоставляет доступ к функциям поиска и генерации ответов на основе персональной базы знаний SiYuan.

**Базовый URL:** `https://api.${DOMAIN_NAME}`

**Формат данных:** JSON

**Аутентификация:** Через SiYuan auth code (опционально)

## Основные эндпоинты

### POST `/ask`

Выполняет интеллектуальный поиск с генерацией ответа через LLM.

#### Запрос

```http
POST /ask
Content-Type: application/json

{
  "query": "Как оптимизировать производительность векторного поиска?",
  "context_limit": 5,
  "generate_answer": true,
  "language": "ru"
}
```

#### Параметры

| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| `query` | string | Да | Поисковый запрос |
| `context_limit` | integer | Нет | Максимальное количество источников (1-20, по умолчанию 5) |
| `generate_answer` | boolean | Нет | Генерировать ли ответ через LLM (по умолчанию true) |
| `language` | string | Нет | Язык ответа: "ru" или "en" (по умолчанию "ru") |

#### Успешный ответ (200)

```json
{
  "answer": "Для оптимизации производительности векторного поиска рекомендуется использовать следующие подходы...",
  "sources": [
    {
      "id": "20231201120000-abc123",
      "title": "Оптимизация баз данных",
      "url": "siyuan://blocks/20231201120000-abc123",
      "confidence": 0.89,
      "citations": ["стр. 45-47", "стр. 52"],
      "snippet": "Использование индексов позволяет значительно ускорить поиск..."
    }
  ],
  "trace_id": "trace-abc-123-def",
  "processing_time_ms": 1250,
  "level": "llm",
  "model_used": "gemini-pro"
}
```

#### Ответ с graceful degradation (200)

```json
{
  "answer": "На основе найденных документов: Использование индексов позволяет значительно ускорить поиск в векторных базах данных...",
  "sources": [...],
  "trace_id": "trace-abc-123-def",
  "processing_time_ms": 450,
  "level": "qa",
  "fallback_reason": "llm_unavailable"
}
```

### GET `/search`

Выполняет поиск без генерации ответа.

#### Запрос

```http
GET /search?q=векторный%20поиск&limit=10&sort_by=relevance
```

#### Параметры

| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| `q` | string | Да | Поисковый запрос |
| `limit` | integer | Нет | Максимальное количество результатов (1-50, по умолчанию 10) |
| `offset` | integer | Нет | Смещение для пагинации (по умолчанию 0) |
| `sort_by` | string | Нет | Сортировка: "relevance", "recency", "title" (по умолчанию "relevance") |
| `min_confidence` | float | Нет | Минимальная уверенность (0.0-1.0, по умолчанию 0.1) |

#### Ответ (200)

```json
{
  "query": "векторный поиск",
  "total_results": 24,
  "results": [
    {
      "id": "20231201120000-abc123",
      "title": "Векторные базы данных и их оптимизация",
      "content_preview": "Векторный поиск основан на вычислении схожести между векторами...",
      "url": "siyuan://blocks/20231201120000-abc123",
      "confidence": 0.92,
      "last_modified": "2023-12-01T12:00:00Z",
      "word_count": 1250
    }
  ],
  "processing_time_ms": 85
}
```

### GET `/connections/{block_id}`

Получает связи документа с другими документами.

#### Запрос

```http
GET /connections/20231201120000-abc123?depth=2
```

#### Параметры

| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| `depth` | integer | Нет | Глубина связей (1-5, по умолчанию 2) |

#### Ответ (200)

```json
{
  "block_id": "20231201120000-abc123",
  "connections": [
    {
      "target_id": "20231201130000-def456",
      "relationship": "references",
      "strength": 0.85,
      "context": "упоминается в разделе о оптимизации"
    }
  ]
}
```

## Мониторинг и здоровье

### GET `/health/live`

Проверка живости приложения (liveness probe).

#### Ответ (200)

```json
{
  "status": "healthy",
  "timestamp": "2023-12-01T12:00:00.123456",
  "version": "1.0.0",
  "uptime_seconds": 3600.5,
  "checks": {
    "process_alive": true,
    "memory_usage": {
      "rss_mb": 245.67,
      "vms_mb": 456.12,
      "percent": 12.3
    }
  }
}
```

### GET `/health/ready`

Проверка готовности приложения (readiness probe).

#### Ответ (200)

```json
{
  "status": "healthy",
  "timestamp": "2023-12-01T12:00:00.123456",
  "version": "1.0.0",
  "uptime_seconds": 3600.5,
  "checks": {
    "dependencies": {
      "qdrant": {
        "name": "qdrant",
        "status": "healthy",
        "response_time_ms": 12.5,
        "last_check": "2023-12-01T12:00:00.123456"
      },
      "sqlite": {
        "name": "sqlite",
        "status": "healthy",
        "response_time_ms": 1.2,
        "last_check": "2023-12-01T12:00:00.123456"
      }
    },
    "system": {
      "cpu_percent": 23.5,
      "memory_percent": 45.2,
      "memory_available_mb": 4096.0,
      "cpu_critical": false,
      "memory_critical": false
    }
  }
}
```

### GET `/health/metrics`

Детальные метрики системы.

#### Ответ (200)

```json
{
  "timestamp": "2023-12-01T12:00:00.123456",
  "system": {
    "cpu": {
      "percent": 23.5,
      "count": 4
    },
    "memory": {
      "total_mb": 8192.0,
      "available_mb": 4096.0,
      "percent": 50.0
    },
    "disk": {
      "total_mb": 102400.0,
      "free_mb": 51200.0,
      "percent": 50.0
    }
  },
  "application": {
    "requests_total": 1250,
    "requests_per_second": 0.35,
    "average_response_time": 1250.0,
    "error_rate": 0.02,
    "cache_hit_rate": 0.75,
    "active_connections": 3
  },
  "dependencies": [
    {
      "name": "qdrant",
      "status": "healthy",
      "response_time_ms": 12.5,
      "last_check": "2023-12-01T12:00:00.123456"
    }
  ]
}
```

## Коды ошибок

### 4xx Client Errors

#### 400 Bad Request

```json
{
  "error": "validation_error",
  "message": "Query parameter is required and cannot be empty",
  "trace_id": "trace-abc-123-def"
}
```

#### 404 Not Found

```json
{
  "error": "not_found",
  "message": "Document with ID 'invalid-id' not found",
  "trace_id": "trace-abc-123-def"
}
```

#### 429 Too Many Requests

```json
{
  "error": "rate_limit_exceeded",
  "message": "Too many requests. Try again in 60 seconds",
  "retry_after": 60,
  "trace_id": "trace-abc-123-def"
}
```

### 5xx Server Errors

#### 503 Service Unavailable

```json
{
  "error": "service_unavailable",
  "message": "Service temporarily unavailable due to high load",
  "retry_after": 30,
  "trace_id": "trace-abc-123-def"
}
```

#### 500 Internal Server Error

```json
{
  "error": "internal_error",
  "message": "An unexpected error occurred",
  "trace_id": "trace-abc-123-def"
}
```

## Rate Limiting

- **Authenticated requests**: 100 requests/minute
- **Anonymous requests**: 10 requests/minute
- **Headers**: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

## Tracing

Каждый запрос содержит `trace_id` для отслеживания в логах:

```
trace_id: trace-abc-123-def-456
```

## Versioning

API использует семантическое версионирование:

- **v1.0.0**: Стабильная версия
- Все изменения обратно совместимы в рамках мажорной версии

## SDK и примеры

### Python

```python
import requests

# Поиск с генерацией ответа
response = requests.post('https://api.example.com/ask', json={
    'query': 'Как настроить векторный поиск?',
    'context_limit': 5
})

result = response.json()
print(result['answer'])
```

### JavaScript

```javascript
// Поиск без генерации
const response = await fetch('https://api.example.com/search?q=векторный+поиск&limit=10');
const results = await response.json();
console.log(results.results);
```

## Поддержка

- **Email**: support@example.com
- **Документация**: https://docs.example.com
- **Статус API**: https://status.example.com
