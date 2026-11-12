---
trigger: always_on
---

# Ключевые правила проекта YouTube Clone MVP

1. **Стек:** Python 3.12+, FastAPI (async), SQLAlchemy 2.0 (asyncpg), Alembic, Pydantic v2, PostgreSQL 16, Redis, MinIO, FFmpeg (Arq worker), React + TypeScript + Vite + Tailwind CSS, Docker Compose + Nginx.
2. **Слоистая архитектура:** `api/v1/routers` -> `services` -> `repositories` -> `models`. Никакой бизнес-логики и прямых SQL-запросов в роутерах.
3. **Видео и хранилище:** Стриминговая загрузка в MinIO без вычитывания файла в RAM; раздача строго с поддержкой HTTP `Range` (`206 Partial Content`); транскодирование в H.264/AAC (`faststart`) и генерация превью в фоне через FFmpeg.
4. **ИБ:** JWT (`access` + `refresh` в `httpOnly` cookies), Argon2/bcrypt, RBAC (`user`, `moderator`, `admin`), проверка magic bytes / MIME при загрузке, защита от IDOR (включая `private` видео), rate-limiting на `auth` и `upload`.
5. **Документация API:** Подробные docstrings, Pydantic v2 схемы и описания кодов ошибок для Swagger (`/docs`).
6. **Workflow:** После каждого этапа — остановка, запуск тестов/проверок в терминале, отчет и ожидание ревью. Каждый этап — атомарный коммит по Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`).
