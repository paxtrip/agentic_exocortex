# Unified RAG System

## Обзор

Единая система RAG (Retrieval-Augmented Generation) для персональной базы знаний с абсолютной приватностью. Поддерживает 1000-10000 документов из заметок SiYuan, реализует graceful degradation через три уровня и первоклассную поддержку русского языка.

## Архитектура

### Компоненты системы

- **Backend API** (`backend/`): FastAPI приложение с эндпоинтами поиска
- **SiYuan Plugin** (`siyuan-plugin/`): Плагин для интеграции с SiYuan
- **Qdrant** (`infrastructure/`): Векторная база данных для dense embeddings
- **SQLite**: База данных для sparse search с FTS5
- **Traefik**: Реверс-прокси для маршрутизации доменов

### Graceful Degradation

1. **LLM Level**: Полноценные ответы через LLM (Gemini → Groq → OpenRouter)
2. **QA Level**: Extractive QA с использованием RoBERTa
3. **Search Level**: Гибридный поиск (dense + sparse) с reranking

## Быстрый старт

### Предварительные требования

- Docker и Docker Compose
- Ubuntu 24.04/22.04 VPS с 4vCPU/8GB RAM
- Домены: `api.${DOMAIN_NAME}`, `qd.${DOMAIN_NAME}`, `siyuan.${DOMAIN_NAME}`

### Установка

1. **Клонируйте репозиторий:**
   ```bash
   git clone <repository-url>
   cd agentic_exocortex
   ```

2. **Настройте переменные окружения:**
   ```bash
   cp .env.example .env
   # Отредактируйте .env файл с вашими настройками
   ```

3. **Запустите систему:**
   ```bash
   docker compose -f infrastructure/docker-compose.yml up -d
   ```

4. **Проверьте здоровье системы:**
   ```bash
   curl https://api.${DOMAIN_NAME}/health/ready
   ```

## API Документация

### Основные эндпоинты

#### POST `/ask`
Выполняет поиск с генерацией ответа.

**Запрос:**
```json
{
  "query": "Как настроить векторный поиск?",
  "context_limit": 5,
  "generate_answer": true
}
```

**Ответ:**
```json
{
  "answer": "Для настройки векторного поиска...",
  "sources": [
    {
      "title": "Векторные базы данных",
      "url": "siyuan://blocks/20231201120000-abc123",
      "confidence": 0.87,
      "citations": ["стр. 15-17"]
    }
  ],
  "trace_id": "abc-123-def",
  "processing_time_ms": 1250
}
```

#### GET `/search`
Выполняет только поиск без генерации.

**Параметры:**
- `q`: Поисковый запрос
- `limit`: Максимальное количество результатов (по умолчанию 10)

#### GET `/health/*`
Эндпоинты мониторинга здоровья системы.

### Ошибки

- `400 Bad Request`: Некорректные параметры запроса
- `503 Service Unavailable`: Сервис временно недоступен
- `500 Internal Server Error`: Внутренняя ошибка сервера

## Конфигурация

### Переменные окружения

| Переменная | Описание | Значение по умолчанию |
|------------|----------|----------------------|
| `DOMAIN_NAME` | Основной домен | `localhost` |
| `SIYUAN_AUTH_CODE` | Код доступа SiYuan | пусто |
| `QDRANT_URL` | URL Qdrant | `http://qdrant:6333` |
| `SQLITE_PATH` | Путь к SQLite БД | `/app/data/knowledge.db` |

### Docker Compose

Система использует существующую сеть `traefik_network` для интеграции с Traefik.

## Мониторинг

### Health Checks

- `/health/live`: Проверка живости (liveness probe)
- `/health/ready`: Проверка готовности (readiness probe)
- `/health/metrics`: Детальные метрики системы
- `/health/dependencies`: Статус зависимостей

### Метрики

Система предоставляет метрики для:
- Времени отклика запросов
- Утилизации CPU/памяти
- Статуса зависимостей
- Кэш-хитов и промахов

### Резервное копирование

Автоматическое ежедневное резервное копирование:
- Qdrant snapshots
- SQLite dumps
- Хранение в `/opt/rag-backups/`

## Разработка

### Структура проекта

```
.
├── backend/                 # Backend API
│   ├── src/
│   │   ├── api/            # FastAPI роуты
│   │   ├── models/         # Модели данных
│   │   ├── services/       # Бизнес-логика
│   │   └── utils/          # Утилиты
│   └── tests/              # Тесты
├── siyuan-plugin/          # SiYuan плагин
├── infrastructure/         # Docker и инфраструктура
└── specs/                  # Спецификации
```

### Запуск тестов

```bash
# Backend тесты
cd backend
python -m pytest

# Интеграционные тесты
python -m pytest tests/integration/
```

## Безопасность

- **Приватность**: Данные никогда не покидают сервер
- **Аутентификация**: Через SiYuan auth code
- **HTTPS**: Обязательный для всех подключений
- **Rate limiting**: Защита от злоупотреблений

## Производительность

### Цели производительности

- **E2E LLM**: < 5-7 секунд
- **Кэшированные запросы**: < 150ms
- **Точность поиска**: Recall@15 ≥ 90%
- **Точность цитат**: ≥ 98%

### Оптимизации

- CPU-optimized embeddings (ONNX Runtime)
- Semantic caching с гибридной схожестью
- Connection pooling для внешних API
- ZRAM сжатие для экономии памяти

## Поддержка

### Языки

- **Русский**: Первоклассная поддержка
- **Английский**: Полная поддержка
- **Многоязычные документы**: Поддержка через BGE-M3

### Браузеры

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Лицензия

MIT License - см. файл LICENSE для деталей.

## Changelog

### v1.0.0 (2025-10-17)
- Первоначальный релиз
- Базовая функциональность RAG
- Интеграция с SiYuan
- Graceful degradation
- Мониторинг и резервное копирование
