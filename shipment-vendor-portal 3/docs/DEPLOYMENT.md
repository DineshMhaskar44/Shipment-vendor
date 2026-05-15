# Deployment Guide

The same codebase deploys to a Mac Mini, AWS EC2, DigitalOcean droplet, or any generic VPS — only the OS package commands differ.

## 1. Production WSGI

We use `gunicorn` behind nginx. The WSGI entry point is `wsgi:app`.

```bash
gunicorn --workers 4 --bind 127.0.0.1:8000 --access-logfile - wsgi:app
```

Tune workers to `(2 × CPU cores) + 1`.

## 2. systemd unit (Linux / Mac Mini with Linux)

`/etc/systemd/system/svp.service`:

```ini
[Unit]
Description=Shipment & Vendor Portal
After=network.target mysql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/srv/svp/shipment-vendor-portal
Environment="PATH=/srv/svp/shipment-vendor-portal/.venv/bin"
EnvironmentFile=/srv/svp/shipment-vendor-portal/.env
ExecStart=/srv/svp/shipment-vendor-portal/.venv/bin/gunicorn \
          --workers 4 --bind 127.0.0.1:8000 wsgi:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now svp
sudo journalctl -u svp -f
```

## 3. nginx reverse proxy + TLS

`/etc/nginx/sites-available/svp.conf`:

```nginx
server {
    listen 80;
    server_name svp.yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name svp.yourdomain.com;

    ssl_certificate     /etc/letsencrypt/live/svp.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/svp.yourdomain.com/privkey.pem;

    client_max_body_size 25M;

    location /static/ {
        alias /srv/svp/shipment-vendor-portal/app/static/;
        expires 30d;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/svp.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d svp.yourdomain.com
```

## 4. Mac Mini (macOS-native)

If running natively on macOS instead of Linux, use **launchd** instead of systemd:

`~/Library/LaunchAgents/com.mosambee.svp.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.mosambee.svp</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/svc/svp/.venv/bin/gunicorn</string>
    <string>--workers</string><string>4</string>
    <string>--bind</string><string>127.0.0.1:8000</string>
    <string>wsgi:app</string>
  </array>
  <key>WorkingDirectory</key><string>/Users/svc/svp</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>/Users/svc/svp/logs/svp.log</string>
  <key>StandardErrorPath</key><string>/Users/svc/svp/logs/svp.err</string>
</dict>
</plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.mosambee.svp.plist
```

Use a Caddy or nginx reverse proxy for TLS.

## 5. AWS EC2 / DigitalOcean / VPS

Standard recipe:

```bash
sudo apt update && sudo apt install -y python3-venv python3-pip mysql-server nginx certbot python3-certbot-nginx
# Then follow Quick start in README, plus the systemd + nginx blocks above.
```

For AWS RDS / DigitalOcean Managed MySQL, point `DATABASE_URL` to the managed endpoint and skip the local MySQL install.

## 6. Backups

```bash
# Daily DB dump (cron)
mysqldump -u svp_user -p shipment_vendor_portal | gzip > /backups/svp_$(date +\%F).sql.gz

# Uploads — sync to S3 nightly (or rsync to backup host)
aws s3 sync app/static/uploads s3://your-bucket/svp-uploads --delete
```

## 7. Hardening checklist

- Set `FLASK_ENV=production` in `.env`
- Rotate `SECRET_KEY` and `JWT_SECRET_KEY` (a rotation invalidates active sessions)
- Enable HTTPS-only cookies (already on in `ProductionConfig`)
- Lock the MySQL user to `localhost` only
- Run gunicorn behind a non-root user
- Set up `fail2ban` for SSH and nginx auth bruteforce
- Snapshot the server weekly
