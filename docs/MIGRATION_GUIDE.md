# Руководство по миграции Nord City (старая → новая версия)

Это руководство описывает переход с production‑сервера на новую версию Nord City с обновлённой структурой базы данных.

---

## Что меняется в миграции

| Изменение | Описание |
|-----------|----------|
| **guest_parking_requests** | Создаётся таблица (если нет), добавляется колонка `msid`, удаляется `reminder_sent` |
| **TIMESTAMPTZ** | Все колонки `timestamp` переводятся в `timestamp with time zone` (значения трактуются как UTC) |
| **Код** | ORM перенесён в `database_service`, обновлены сервисы, бот, веб‑API |

---

## Предварительные требования

1. **Резервная копия БД** — обязательно перед миграцией:
   ```bash
   pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME -Fc -f nordcity_backup_$(date +%Y%m%d_%H%M%S).dump
   ```

2. **Остановленные сервисы** — миграция должна выполняться при остановленных приложениях.

3. **Python 3.10+** и зависимости из `requirements.txt`.

---

## Пошаговая инструкция

### 1. Подготовка на production‑сервере

```bash
# Перейти в каталог проекта
cd /path/to/nord-city-project

# Активировать виртуальное окружение
source venv/bin/activate   # или: . venv/bin/activate

# Обновить код (git pull / загрузка архива)
git pull origin main
# или загрузить новый релиз архивом
```

### 2. Резервная копия базы данных

```bash
# Экспорт в custom format (для pg_restore при откате)
pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME -Fc -f nordcity_backup_$(date +%Y%m%d).dump

# Или в SQL (проще просматривать)
pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME -f nordcity_backup_$(date +%Y%m%d).sql
```

### 3. Остановка сервисов

```bash
# Если используется orchestrator:
python orchestrator.py --kill

# Если сервисы запущены через systemd:
sudo systemctl stop nordcity-db nordcity-web nordcity-bot nordcity-site
# (подставьте свои имена сервисов)
```

### 4. Обновление зависимостей

```bash
pip install -r requirements.txt
```

### 5. Проверка .env

Убедитесь, что в `.env` заданы переменные:

- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- Остальные переменные (BOT_TOKEN, ADMIN_CHAT_ID, CORS_ORIGINS и т.д.) — при необходимости обновите по `.env.example`

### 6. Запуск миграции

```bash
python infrastructure/scripts/migrate_all.py
```

Скрипт выполняет:

1. Создание таблицы `guest_parking_requests` (если её ещё нет)
2. Преобразование всех колонок `timestamp` в `timestamptz`
3. Добавление колонки `msid` в `guest_parking_requests`
4. Удаление колонки `reminder_sent` из `guest_parking_requests`

В логе будут сообщения `[OK]` или `[SKIP]` (например, для отсутствующих таблиц).

### 7. Развёртывание новой версии приложения

```bash
# Перезапуск через orchestrator:
python orchestrator.py --background

# Или через systemd:
sudo systemctl start nordcity-db nordcity-web nordcity-bot nordcity-site
```

### 8. Проверка работы

- Проверить, что бот отвечает на `/start`
- Проверить веб‑интерфейс (вход, сервисы, заявки)
- Проверить заявки на гостевую парковку (если функционал включён)

---

## Откат (если что‑то пошло не так)

### Откат базы данных

```bash
# Остановить сервисы
python orchestrator.py --kill

# Восстановить дамп (custom format)
pg_restore -h $DB_HOST -U $DB_USER -d $DB_NAME --clean --if-exists nordcity_backup_YYYYMMDD.dump

# Или для SQL-дампа:
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f nordcity_backup_YYYYMMDD.sql
```

### Откат кода

```bash
git checkout <старый-тег-или-коммит>
pip install -r requirements.txt
python orchestrator.py --background
```

---

## Запуск отдельных скриптов (опционально)

Если нужно выполнить миграции по одному:

```bash
# По порядку:
python infrastructure/scripts/migrate_guest_parking.py
python infrastructure/scripts/migrate_timestamptz.py
python infrastructure/scripts/add_guest_parking_msid.py
python infrastructure/scripts/drop_guest_parking_reminder_sent.py
```

Рекомендуется использовать единый скрипт `migrate_all.py`.

---

## Частые проблемы

| Проблема | Решение |
|----------|---------|
| `Ошибка: не заданы переменные окружения` | Проверьте `.env` в корне проекта |
| `relation "X" does not exist` | Таблица ещё не создана — скрипт пропустит такие колонки как `[SKIP]` |
| `column "Y" already has type timestamp with time zone` | Колонка уже мигрирована — пропустите или игнорируйте |
| `permission denied` | Запускайте от пользователя с правами на БД или под `postgres` |

---

## Краткая последовательность команд

```bash
# 1. Бэкап
pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME -Fc -f backup.dump

# 2. Остановка
python orchestrator.py --kill

# 3. Обновление кода и зависимостей
git pull && pip install -r requirements.txt

# 4. Миграция
python infrastructure/scripts/migrate_all.py

# 5. Запуск
python orchestrator.py --background
```
