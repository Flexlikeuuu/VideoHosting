# YouTube Clone MVP — Видеохостинг

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://www.docker.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D.svg)](https://redis.io/)
[![MinIO](https://img.shields.io/badge/MinIO-S3_Compatible-C72C48.svg)](https://min.io/)

Production-ready MVP видеохостинга (аналог YouTube) с чистой слоистой архитектурой, надежной потоковой обработкой медиа, строгой моделью информационной безопасности (RBAC, IDOR-защита, httpOnly cookies, rate-limiting) и развертыванием одной командой на чистой Ubuntu.

---

## 📌 Архитектурный обзор

Проект спроектирован по принципам чистой слоистой архитектуры и модульного монолита:

```
[ Frontend SPA (React + TS + Vite + Tailwind) ]
                     │  (HTTP / API / Range requests)
                     ▼
             [ Nginx Reverse Proxy ]
              │                   │
  (API / Static Proxy)     (X-Accel-Redirect / Media Stream)
              ▼                   ▼
    [ FastAPI Backend ]     [ MinIO Object Storage (S3) ]
         │          │                   ▲
         ▼          ▼                   │
   [ PostgreSQL ] [ Redis ] ────► [ FFmpeg Worker (Arq) ]
```

### Слои Backend:
1. **Routers (`app/api/v1/routers/`):** Только HTTP-слой (валидация входных Pydantic v2 схем, внедрение зависимостей `Depends`, маппинг доменных исключений в статусы ответа). Бизнес-логика и прямые SQL-запросы в роутерах запрещены.
2. **Services (`app/services/`):** Вся бизнес-логика, оркестрация репозиториев, проверка прав доступа (`VideoAccessService`), постановка задач в очередь обработки.
3. **Repositories (`app/repositories/`):** Инкапсуляция всех запросов к БД через SQLAlchemy 2.0 Async Session.
4. **Models (`app/models/`):** Декларативные модели SQLAlchemy 2.0, индексы, внешние ключи, enum-типы.

Подробная документация:
- 📖 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — топология системы, sequence-диаграммы загрузки и Range-стриминга приватных видео, обоснование `X-Accel-Redirect`.
- 🗄️ [docs/DATABASE.md](docs/DATABASE.md) — ER-диаграмма, схемы таблиц, индексы, триграммный поиск GIN.

---

## 🚀 Быстрый запуск одной командой (Clean Ubuntu)

### Предварительные требования:
- Установленные `docker` и `docker compose` (Docker Engine 24+ / Compose v2).
- Наличие свободных портов `80` (HTTP) и `9001` (MinIO Console, опционально).

### Запуск проекта:
Склонируйте репозиторий и выполните скрипт автоматического развертывания:

```bash
git clone <repository_url>
cd YoutubeTask
./deploy.sh
```
*Или через Makefile:*
```bash
make up
```

### Что происходит автоматически во время `deploy.sh`:
1. Копируется конфигурация окружения из шаблона `.env.example` в `.env` (если файл не создан).
2. Поднимаются контейнеры `postgres`, `redis`, `minio`.
3. Контейнер `minio-init` автоматически создает бакеты `videos` и `thumbnails`.
4. Бэкенд автоматически накатывает все миграции Alembic (`alembic upgrade head`).
5. Multi-stage Dockerfile для `nginx` компилирует React-фронтенд и монтирует production-билд.
6. Идемпотентный скрипт `scripts/seed.py` генерирует видеоролики через FFmpeg, загружает их в S3 и наполняет БД пользователями, комментариями, лайками и жалобами.

---

## 🔑 Тестовые учетные записи

Все учетные записи создаются скриптом сидинга с единым паролем: `Password123!`

| Логин (username) | Email | Пароль | Роль (RBAC) | Назначение и доступ |
| :--- | :--- | :--- | :--- | :--- |
| **`admin`** | `admin@example.com` | `Password123!` | `admin` | Администратор платформы: полный доступ, панель модерации, снятие скрытия видео |
| **`moderator`** | `moderator@example.com` | `Password123!` | `moderator` | Модератор: просмотр очереди жалоб (`/moderation`), отклонение жалоб, скрытие видео |
| **`creator`** | `creator@example.com` | `Password123!` | `user` | Автор контента: загружено 6 видео, создан плейлист, управление списком доступа к приватному видео |
| **`viewer`** | `viewer@example.com` | `Password123!` | `user` | Зритель: подписка на `creator`, доступ к приватному видео `creator`, лайки, комментарии |

---

## 🌐 Ссылки на сервисы

После успешного запуска доступны следующие интерфейсы:

| Сервис | URL | Описание |
| :--- | :--- | :--- |
| **Web-интерфейс (Frontend SPA)** | [http://localhost/](http://localhost/) | Клиент YouTube Clone (темная/светлая тема, плеер, загрузка, поиск, комментарии) |
| **Swagger / OpenAPI Документация** | [http://localhost/docs](http://localhost/docs) | Интерактивная документация REST API со всеми схемами и статус-кодами |
| **ReDoc** | [http://localhost/redoc](http://localhost/redoc) | Альтернативная спецификация API |
| **Healthcheck API** | [http://localhost/api/v1/health](http://localhost/api/v1/health) | Проверка работоспособности PostgreSQL, Redis и MinIO |
| **Панель модерации** | [http://localhost/moderation](http://localhost/moderation) | Доступна под аккаунтами `admin` и `moderator` |

---

## 🔒 Практики информационной безопасности (ИБ)

1. **Аутентификация и сессии:**
   - Короткоживущий JWT `access_token` (15 минут) и ротируемый `refresh_token` (7 дней) хранятся исключительно в `httpOnly`, `SameSite=Lax` cookies (недоступны для XSS через `document.cookie`).
   - Пароли хэшируются с использованием стойкого алгоритма **Argon2id**.
2. **Защита от IDOR (Insecure Direct Object Reference):**
   - Централизованный `VideoAccessService` выполняет строгую проверку прав владельца при изменении/удалении ресурсов.
   - Для `private` видео доступ разрешен строго: владельцу, пользователям из явного `video_access_list` и модераторам при наличии активной жалобы. Пользователям без прав возвращается `403 Forbidden`.
3. **Безопасность загрузки медиа:**
   - Потоковая проверка сигнатуры файла (magic bytes видеоконтейнеров MP4/WebM/MKV/MOV и изображений JPEG/PNG/WebP). Исполняемые файлы и скрипты с расширением `.mp4` гарантированно отклоняются со статусом `400 Bad Request`.
   - Потоковая передача чанками напрямую в S3 без вычитывания всего файла в оперативную память процесса (защита от DoS по памяти).
4. **Rate Limiting:**
   - Ограничение частоты запросов на базе Redis (скользящее/фиксированное окно) для эндпоинтов авторизации (`/auth/login`, `/auth/register`) и загрузки видео (`/videos/upload`).
5. **Безопасная конфигурация:**
   - Все секреты изолированы в файле `.env`, который добавлен в `.gitignore`. В репозитории опубликован только безопасный шаблон `.env.example`.

---

## 🧪 Автоматическое тестирование

Проект покрыт автоматическими тестами на `pytest` и `httpx.AsyncClient` с проверкой критических сценариев:

- **E2E основной путь:** регистрация -> загрузка реального MP4 -> фоновая обработка FFmpeg до статуса `ready` -> стриминг через `X-Accel-Redirect` и `Range: bytes=...` -> лайк -> комментарий -> проверка счетчиков.
- **ИБ-тесты:** попытка неавторизованного доступа к `private` видео (IDOR), попытка вызова модерации обычным пользователем (RBAC), попытка загрузки текстовых/исполняемых файлов с расширением `.mp4` (проверка magic bytes).
- **Социальные механики и модерация:** подписки, лайки/дизлайки, комментарии, создание и наполнение плейлистов, рассмотрение жалоб модератором со скрытием видео (`is_hidden=True`).

### Запуск тестов:

```bash
make test
```
*Или напрямую через docker compose:*
```bash
docker compose exec -T -e PYTHONPATH=/app backend pytest tests/ -v
```

---

## 🛠️ Полезные команды (Makefile)

```bash
make up        # Запуск и развертывание проекта (build + healthcheck + seed)
make down      # Остановка всех контейнеров
make test      # Запуск всех автотестов (pytest)
make seed      # Повторный запуск идемпотентного сидинга БД и S3
make health    # Проверка состояния сервисов (/api/v1/health)
make logs      # Просмотр логов всех контейнеров в реальном времени
make migrate   # Применение миграций Alembic
make build     # Пересборка всех Docker-образов
```
