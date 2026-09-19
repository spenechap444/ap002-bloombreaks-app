#!/bin/bash
set -e
if [ ! -x /opt/certbot/bin/certbot ]; then
  python3 -m venv /opt/certbot
  /opt/certbot/bin/pip install certbot certbot-nginx
  ln -sf /opt/certbot/bin/certbot /usr/bin/certbot
fi
certbot -n --nginx -d api.bloom55breaks.com --agree-tos \
  --email you@example.com --keep-until-expiring --redirect