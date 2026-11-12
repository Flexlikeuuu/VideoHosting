# Архитектура системы (YouTube Clone MVP)

## 1. Обзор и топология сервисов

Система построена по микросервисно-модульной схеме в Docker Compose с единой точкой входа через Nginx. Развертывание на чистой Ubuntu выполняется одной командой (`docker compose up -d --build`).

```mermaid
flowchart LR
    Client["Браузер (SPA)"] -->|HTTP :80| Nginx["Nginx (Reverse Proxy & Static)"]

    Nginx -->|"/ (SPA статика)"| Frontend["Frontend (React + Vite build)"]
    Nginx -->|"/api/*, /docs, /openapi.json"| Backend["Backend (FastAPI async)"]
    Nginx -->|"X-Accel-Redirect (Range 206)"| MinIO["MinIO (S3 Object Storage)"]

    Backend -->|"SQLAlchemy 2.0 (asyncpg)"| Postgres[("PostgreSQL 16")]
    Backend -->|"Очереди / Rate-limit / Кэш"| Redis[("Redis")]
    Backend -->|"S3 Streaming Upload"| MinIO

    Worker["Arq Worker (Python + FFmpeg)"] -->|"Чтение задач / Статус"| Redis
    Worker -->|"Download raw / Upload mp4+thumb"| MinIO
    Worker -->|"Обновление статуса и метаданных"| Postgres
```

### Границы ответственности сервисов

| Сервис | Технология | Ответственность |
| :--- | :--- | :--- |
| **nginx** | Nginx Alpine | Единая точка входа (порт 80). Отдает собранную статику SPA, проксирует `/api/*` и `/docs` на `backend`, выполняет стриминг видео/превью из MinIO по внутреннему `X-Accel-Redirect` с поддержкой `Range` (`206 Partial Content`). |
| **backend** | Python 3.12, FastAPI (async) | REST API (`/api/v1`), аутентификация (JWT в `httpOnly` cookies), RBAC, защита от IDOR, rate-limiting, валидация загрузок (magic bytes), потоковая загрузка в MinIO без буферизации в RAM, постановка задач в Redis. |
| **worker** | Arq + FFmpeg / ffprobe | Фоновая обработка видео: извлечение метаданных (длительность, разрешение), генерация превью (thumbnail), транскодирование в H.264/AAC MP4 с `-movflags +faststart`, обновление статуса видео в PostgreSQL. |
| **postgres** | PostgreSQL 16 | Основное хранилище данных: пользователи, видео, права доступа к `private` видео, плейлисты, комментарии, реакции, подписки, жалобы, refresh-токены. |
| **redis** | Redis 7 | Брокер очереди фоновых задач (Arq), счетчики rate-limiting (`/auth/*`, `/videos/upload`), опциональный кэш прав доступа/метаданных. |
| **minio** | MinIO (S3-compatible) | Объектное хранилище. Бакет `videos` (префиксы `raw/`, `processed/`, `thumbnails/`, `avatars/`). Доступен только во внутренней сети Docker (наружу не проброшен). |
| **frontend** | React, TypeScript, Vite, Tailwind CSS | SPA-клиент в стиле YouTube с поддержкой темной/светлой темы. |

---

## 2. Слоистая архитектура Backend

Внутри `backend/app/` соблюдается строгая однонаправленная зависимость слоев:

```text
api/v1/routers  ──▶  services  ──▶  repositories  ──▶  models
```

- **`api/v1/routers/`** — только HTTP-уровень: валидация входных данных (Pydantic v2), `Depends` для извлечения текущего пользователя/роли, маппинг доменных исключений в HTTP-статусы (`400`, `401`, `403`, `404`, `409`, `413`, `415`, `429`), формирование ответов и Swagger-документации. Прямые SQL-запросы, вызовы MinIO или Redis запрещены.
- **`services/`** — вся бизнес-логика: проверка прав доступа (ownership, `private` access list, RBAC), оркестрация репозиториев, вызовы S3-клиента, постановка задач в Arq, бизнес-валидации.
- **`repositories/`** — инкапсуляция всех запросов к PostgreSQL через `AsyncSession` SQLAlchemy 2.0. Без бизнес-логики и HTTP-исключений.
- **`models/`** — декларативные ORM-модели SQLAlchemy 2.0, Enum-типы, внешние ключи и индексы.
- **`core/`** — конфигурация (`pydantic-settings`), безопасность (JWT, Argon2), клиент MinIO, rate-limiter на Redis, доменные исключения.

---

## 3. Критичные потоки данных (Sequence-диаграммы)

### 3.1. Поток загрузки видео, сохранения в S3 и фоновой обработки FFmpeg

Загрузка выполняется потоково (chunked streaming), без вычитывания файла целиком в оперативную память.

```mermaid
sequenceDiagram
    autonumber
    actor User as Пользователь
    participant Nginx as Nginx
    participant API as FastAPI Router/Service
    participant Redis as Redis (RateLimit & Arq)
    participant DB as PostgreSQL
    participant S3 as MinIO (S3)
    participant Worker as Arq Worker + FFmpeg

    User->>Nginx: POST /api/v1/videos/upload (multipart stream + cookie)
    Nginx->>API: Проксирование потока (request_buffering off)
    API->>Redis: Проверка rate-limit на upload
    API->>API: Проверка JWT & чтение первых чанков (magic bytes / MIME)
    alt Невалидный формат или превышен размер
        API-->>User: 415 Unsupported Media Type / 413 Payload Too Large
    end
    API->>DB: INSERT videos (status='uploading', raw_object_key)
    API->>S3: Multipart streaming upload чанков в raw/{video_id}.bin
    S3-->>API: ETag / Upload OK
    API->>DB: UPDATE videos SET status='processing'
    API->>Redis: Enqueue task process_video(video_id)
    API-->>User: 201 Created (video_id, status='processing')

    Worker->>Redis: Получение задачи process_video(video_id)
    Worker->>S3: Скачивание raw/{video_id}.bin во временный файл
    Worker->>Worker: ffprobe (длительность, кодеки)
    Worker->>Worker: ffmpeg -> H.264/AAC MP4 (-movflags +faststart) + thumbnail.jpg
    Worker->>S3: Upload processed/{video_id}.mp4 & thumbnails/{video_id}.jpg
    Worker->>S3: Удаление raw/{video_id}.bin (cleanup)
    alt Успешная обработка
        Worker->>DB: UPDATE videos SET status='ready', duration_seconds=..., processed_object_key=..., thumbnail_object_key=...
    else Ошибка FFmpeg
        Worker->>DB: UPDATE videos SET status='failed', error_message=...
    end
```

### 3.2. Поток просмотра `private` видео с проверкой прав и Range-стримингом

```mermaid
sequenceDiagram
    autonumber
    actor Client as Браузер (HTML5 Video)
    participant Nginx as Nginx
    participant API as FastAPI Backend
    participant DB as PostgreSQL
    participant S3 as MinIO (S3)

    Client->>Nginx: GET /api/v1/videos/{id}/stream (Range: bytes=0-1048575, Cookie)
    Nginx->>API: Проксирование запроса с заголовками Cookie и Range
    API->>API: Декодирование JWT из httpOnly cookie (user_id, role)
    API->>DB: SELECT video + проверка video_access_list
    alt Видео не готово или скрыто модератором (и не admin/moderator)
        API-->>Client: 404 Not Found / 403 Forbidden
    else visibility == 'private' и пользователь не владелец / не в access_list / не модератор
        API-->>Client: 403 Forbidden (защита от IDOR)
    else Доступ разрешен
        API->>API: Формирование внутреннего Presigned URL MinIO (TTL 60s) или пути
        API-->>Nginx: 200 OK + заголовок X-Accel-Redirect: /_internal_s3/...
        Nginx->>S3: Внутренний GET к MinIO с пробросом Range: bytes=0-1048575
        S3-->>Nginx: 206 Partial Content (Content-Range, Content-Length, Accept-Ranges: bytes)
        Nginx-->>Client: 206 Partial Content (потоковая отдача видеочанка)
    end
```

---

## 4. Обоснование выбора механизма защиты приватных видео

Для защиты `private` видео и раздачи медиафайлов выбран паттерн **Nginx `X-Accel-Redirect` (внутреннее перенаправление) поверх приватного бакета MinIO** вместо прямой выдачи Presigned URLs клиенту.

### Сравнение подходов

| Критерий | `X-Accel-Redirect` (выбран) | Прямой Presigned URL клиенту |
| :--- | :--- | :--- |
| **Изоляция хранилища** | MinIO полностью скрыт во внутренней сети Docker; клиент общается только с Nginx (`/api/v1/...`). | Порт MinIO или прокси на бакет должен быть доступен клиенту напрямую. |
| **Мгновенный отзыв прав** | Права (владелец, `video_access_list`, `is_hidden`) проверяются при каждом запросе/чанке на бэкенде. Отзыв доступа действует немедленно. | Выданный URL остается валидным до истечения TTL, даже если владелец уже забрал доступ или видео скрыл модератор. |
| **Поддержка `Range` и нагрузка на Python** | FastAPI выполняет только легкую проверку прав и возвращает пустой ответ с `X-Accel-Redirect`. Передачу байтов и `206 Partial Content` берет на себя Nginx (C/epoll). | Передача идет мимо FastAPI, но ценой потери контроля после выдачи ссылки. |
| **Совместимость с HTML5 `<video>` и CORS** | Один origin, нативная работа с `httpOnly` cookies без передачи токенов в query string и без проблем с CORS. | Требуются настройки CORS на S3 и обновление URL при истечении срока жизни во время длинного просмотра. |

**Дополнение по безопасности:** Внутренний location `/_internal_s3/` в Nginx помечен директивой `internal;`, поэтому клиент не может обратиться к нему напрямую, минуя проверку прав в FastAPI.

---

## 5. Стандарты информационной безопасности (ИБ)

1. **Аутентификация:** `access_token` (короткий TTL, например 15 мин) и `refresh_token` (7–30 дней) передаются исключительно в `httpOnly`, `SameSite=Lax` cookies (`Secure` при HTTPS). Refresh-токены хранятся в БД в виде SHA-256 хеша и ротируются при каждом обновлении.
2. **Пароли:** хеширование с помощью `Argon2id` (`argon2-cffi`).
3. **RBAC:** явные зависимости FastAPI `get_current_user`, `get_optional_user`, `require_roles(Role.MODERATOR, Role.ADMIN)`.
4. **Защита от IDOR:**
   - Изменение/удаление видео, плейлистов, комментариев и управление `video_access_list` разрешены только владельцу (или модератору/админу в рамках полномочий).
   - Доступ к `private` видео проверяется как на метаданных (`GET /videos/{id}`), так и на стриминге (`/stream`) и превью (`/thumbnail`).
5. **Безопасность загрузок:** проверка magic bytes контейнеров (MP4/MOV `ftyp`, WebM/MKV `1A 45 DF A3`, JPEG `FF D8 FF`, PNG `89 50 4E 47`, WebP `RIFF...WEBP`), ограничение максимального размера, хранение в S3 строго по UUID-ключам.
6. **Rate-limiting:** Redis-лимитер на `/api/v1/auth/*` (защита от брутфорса) и `/api/v1/videos/upload` (защита от исчерпания диска/очереди).
