# Инструкция: Nginx + SSL для nord-city.online

## 1. Подготовка .env

Добавьте в `infrastructure/.env` переменные для Nginx:

```env
# Nginx / SSL (добавьте к существующему .env)
NGINX_DOMAIN=nord-city.online
NGINX_SSL_CERT=/etc/letsencrypt/live/nord-city.online/fullchain.pem
NGINX_SSL_KEY=/etc/letsencrypt/live/nord-city.online/privkey.pem
SITE_PORT=3000
```

**Учёт текущего .env:**
- `WEB_SERVICE_PORT=8003` — API (уже есть)
- `SITE_PORT=3000` — Next.js фронтенд (добавить)

---

## 2. DNS у провайдера

В панели управления доменом nord-city.online создайте **A-запись**:

| Тип | Имя | Значение        | TTL   |
|-----|-----|-----------------|-------|
| A   | @   | IP вашего сервера | 3600 |
| A   | www | IP вашего сервера | 3600 |

Подождите 5–30 минут, пока DNS обновится:
```bash
dig nord-city.online +short
```

---

## 3. Установка Certbot и SSL-сертификата

### Ubuntu / Debian

```bash
sudo apt update
sudo apt install -y certbot
```

### Получение сертификата

Nginx на этот момент ещё не должен работать на 443 (или должен быть остановлен):

```bash
sudo certbot certonly --standalone -d nord-city.online
```

Если нужен и www:
```bash
sudo certbot certonly --standalone -d nord-city.online -d www.nord-city.online
```

Certbot спросит email для уведомлений от Let's Encrypt — введите свой.

Сертификаты будут сохранены в:
- Сертификат: `/etc/letsencrypt/live/nord-city.online/fullchain.pem`
- Ключ: `/etc/letsencrypt/live/nord-city.online/privkey.pem`

### Автообновление

```bash
sudo certbot renew --dry-run
```

Добавьте в cron (если ещё нет):
```bash
echo "0 3 * * * certbot renew --quiet" | sudo tee -a /etc/cron.d/certbot
```

---

## 4. Генерация nginx.conf

Из директории проекта выполните:

```bash
cd infrastructure/nginx
./generate_conf.sh
```

Либо из `infrastructure`:
```bash
./nginx/generate_conf.sh
```

Скрипт использует переменные из `infrastructure/.env` и создаёт `nginx/nginx.conf`.

---

## 5. Установка и запуск Nginx

### Ubuntu / Debian

```bash
sudo apt install -y nginx
```

Скопируйте конфиг в место, откуда Nginx его подхватит:

```bash
sudo cp infrastructure/nginx/nginx.conf /etc/nginx/sites-available/nord-city
sudo ln -sf /etc/nginx/sites-available/nord-city /etc/nginx/sites-enabled/
```

Отключите дефолтный сайт, если он мешает:
```bash
sudo rm -f /etc/nginx/sites-enabled/default
```

Проверьте конфигурацию:
```bash
sudo nginx -t
```

Запуск:
```bash
sudo systemctl enable nginx
sudo systemctl start nginx
sudo systemctl status nginx
```

Перезагрузка после изменений:
```bash
sudo systemctl reload nginx
```

---

## 6. Запуск приложения

Перед Nginx должны работать:

1. **PostgreSQL** (если не в Docker — локально)
2. **Orchestrator** (API):
   ```bash
   cd infrastructure && python orchestrator.py --no-dashboard
   ```
3. **Next.js**:
   ```bash
   cd web && npm run build && npm start
   ```

После этого Nginx проксирует:
- `https://nord-city.online/api/` → API (порт 8003)
- `https://nord-city.online/` → Next.js (порт 3000)

---

## 7. Редирект HTTP → HTTPS (по желанию)

Добавьте в начало `nginx.conf` (перед блоком `server`):

```nginx
server {
    listen 80;
    server_name nord-city.online www.nord-city.online;
    return 301 https://$server_name$request_uri;
}
```

---

## Чек-лист

- [ ] A-запись DNS указывает на IP сервера
- [ ] Certbot установлен, сертификат получен
- [ ] Переменные NGINX в .env
- [ ] nginx.conf сгенерирован
- [ ] Конфиг скопирован в /etc/nginx/sites-enabled/
- [ ] `nginx -t` — OK
- [ ] PostgreSQL, orchestrator, Next.js запущены
- [ ] Nginx запущен
- [ ] https://nord-city.online открывается
