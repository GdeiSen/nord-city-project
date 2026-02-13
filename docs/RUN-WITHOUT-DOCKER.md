# Запуск Nord City Infrastructure

Все Python-сервисы запускаются на хосте через единый оркестратор.
Docker и RabbitMQ не используются — связь между сервисами по HTTP.

---

## Архитектура запуска

```
infrastructure/
├── .env                  ← единый файл переменных окружения
├── requirements.txt      ← единый файл зависимостей (все сервисы + оркестратор)
├── orchestrator.py       ← главная точка входа
├── shared/               ← общие модули (клиенты, модели, утилиты)
└── services/
    ├── database_service/  ← FastAPI HTTP RPC (порт 8001)
    ├── web_service/       ← FastAPI REST API (порт 8003)
    └── bot_service/       ← Telegram bot
```

Оркестратор **не управляет** PostgreSQL и Next.js — они запускаются отдельно.

---

## 1. Подготовка

### Требования
- Python 3.11+
- PostgreSQL 15+ (работает отдельно)
- Node.js 18+ (для Next.js сайта, работает отдельно)

### Установка зависимостей

```bash
cd infrastructure
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Один `venv` и один `requirements.txt` для всех сервисов.

---

## 2. Настройка окружения

Единственный файл переменных — `infrastructure/.env`:

```env
# Telegram
BOT_TOKEN=<ваш_токен>
ADMIN_CHAT_ID=<id_чата>
CHIEF_ENGINEER_CHAT_ID=<id_чата>

# PostgreSQL
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=bot_database
DB_USER=bot_user
DB_PASSWORD=bot_password

# Database Service HTTP
DATABASE_SERVICE_HOST=0.0.0.0
DATABASE_SERVICE_PORT=8001
DATABASE_SERVICE_HTTP_URL=http://127.0.0.1:8001

# Web Service
WEB_SERVICE_HOST=0.0.0.0
WEB_SERVICE_PORT=8003
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

---

## 3. Запуск через оркестратор (рекомендуется)

```bash
cd infrastructure
source venv/bin/activate

# Все сервисы (db → web → bot)
python orchestrator.py

# Только выбранные (зависимости подключаются автоматически)
python orchestrator.py --services db,web
python orchestrator.py --services bot        # автоматически запустит db

# Список доступных сервисов
python orchestrator.py --list
```

### Что делает оркестратор

- Загружает `.env` и передаёт переменные дочерним процессам
- Запускает каждый сервис в отдельном процессе (subprocess)
- Автоматически разрешает зависимости (web и bot зависят от db)
- Отображает **live-дашборд** через `rich`:
  - Статус каждого сервиса (RUNNING / CRASHED / STOPPED)
  - PID, порт, время работы
  - Последние строки логов
- Обрабатывает **Ctrl+C** — graceful shutdown в обратном порядке
- Если сервис падает — оркестратор останавливает остальные и завершается

### Доступные сервисы

| Alias | Сервис           | Порт  | Зависит от |
|-------|------------------|-------|------------|
| `db`  | Database Service | 8001  | —          |
| `web` | Web Service      | 8003  | db         |
| `bot` | Bot Service      | —     | db         |

---

## 4. Запуск отдельного сервиса (foreground)

Для разработки и отладки — запуск одного сервиса напрямую,
без дашборда, с прямым выводом в терминал:

```bash
python orchestrator.py --service db
python orchestrator.py --service web
python orchestrator.py --service bot
```

В этом режиме оркестратор **не запускает зависимости** — убедитесь, что
`database_service` уже работает, если запускаете `web` или `bot`.

---

## 5. Ручной запуск (без оркестратора)

Если оркестратор не нужен, сервисы запускаются вручную в разных терминалах.
Один и тот же `venv` и `.env`.

**Database Service** (порт 8001):
```bash
cd infrastructure
source venv/bin/activate
set -a && source .env && set +a
cd services/database_service/src
python main.py
```

**Web Service** (порт 8003):
```bash
cd infrastructure
source venv/bin/activate
set -a && source .env && set +a
cd services/web_service/src
python main.py
```

**Bot Service**:
```bash
cd infrastructure
source venv/bin/activate
set -a && source .env && set +a
cd services/bot_service/src
python main.py
```

> В каждом `main.py` корень `infrastructure/` добавляется в `sys.path`,
> поэтому `PYTHONPATH` задавать не нужно.

---

## 6. PostgreSQL (вне оркестратора)

Оркестратор не управляет PostgreSQL.
Установите и запустите отдельно:

```bash
sudo systemctl start postgresql
```

Создайте базу и пользователя:
```sql
CREATE USER bot_user WITH PASSWORD 'bot_password';
CREATE DATABASE bot_database OWNER bot_user;
```

Параметры подключения прописаны в `infrastructure/.env`.

---

## 7. Next.js сайт (вне оркестратора)

Фронтенд — отдельный проект в каталоге `web/`:

```bash
cd web
cp .env.example .env.local   # если нужно
# Убедитесь что NEXT_PUBLIC_API_URL=http://localhost:8003/api/v1
npm install
npm run dev
```

---

## 8. systemd (автозапуск)

Пример юнита для запуска всех сервисов через оркестратор:

```ini
[Unit]
Description=Nord City Services Orchestrator
After=postgresql.service

[Service]
Type=simple
WorkingDirectory=/opt/001_project_nord_city/infrastructure
EnvironmentFile=/opt/001_project_nord_city/infrastructure/.env
ExecStart=/opt/001_project_nord_city/infrastructure/venv/bin/python orchestrator.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Или отдельные юниты для каждого сервиса:

```ini
[Unit]
Description=Nord City Database Service
After=postgresql.service

[Service]
Type=simple
WorkingDirectory=/opt/001_project_nord_city/infrastructure/services/database_service/src
EnvironmentFile=/opt/001_project_nord_city/infrastructure/.env
Environment=PYTHONPATH=/opt/001_project_nord_city/infrastructure
ExecStart=/opt/001_project_nord_city/infrastructure/venv/bin/python main.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

---

## Итог

- **Один `.env`** — `infrastructure/.env`
- **Один `venv`** — `infrastructure/venv/`
- **Один `requirements.txt`** — `infrastructure/requirements.txt`
- **Один оркестратор** — `python orchestrator.py` (главная точка входа)
- PostgreSQL и Next.js запускаются отдельно
- Связь между сервисами — HTTP (без RabbitMQ, без Docker)
