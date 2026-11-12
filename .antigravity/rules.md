# Правила проекта (Antigravity Rules)

## Стек и архитектура
- **Backend:** Python 3.12+, FastAPI (async), SQLAlchemy 2.0 (`asyncpg`), Alembic, Pydantic v2.
- **Слои:** строго `api/v1/routers` -> `services` -> `repositories` -> `models`. Никакой бизнес-логики и SQL в роутерах.
- **БД / Очереди / Хранилище:** PostgreSQL 16, Redis, MinIO (S3).
- **Медиа:** FFmpeg (H.264/AAC + `faststart`, превью, метаданные) в фоновом воркере (Arq).
- **Frontend:** React + TypeScript + Vite + Tailwind CSS (темная/светлая тема, UX/UI YouTube).
- **Инфра:** Docker, Docker Compose, Nginx (единая точка входа, статика, `/api`, HTTP `Range` стриминг).

## Информационная безопасность (ИБ)
- JWT (`access` + `refresh`) в `httpOnly` cookies; пароли — Argon2/bcrypt.
- RBAC (`user`, `moderator`, `admin`).
- Проверка реального MIME-типа и magic bytes при загрузке файлов; стриминговая загрузка в MinIO без загрузки файла целиком в RAM.
- Раздача видео строго с поддержкой `Range` (`206 Partial Content`).
- Защита от IDOR (особенно для `private` видео).
- Rate-limiting на `auth` и `upload`.

## Протокол работы
- Строго по этапам: после каждого этапа — запуск проверок/тестов в терминале, демонстрация результата и ожидание ревью.
- Атомарные коммиты по Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `test:`).
- Подробные docstrings, Pydantic-схемы и описания ошибок для Swagger (`/docs`).
