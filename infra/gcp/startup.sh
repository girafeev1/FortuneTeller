#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${app_dir}"
REPO_URL="${repo_url}"
SERVICE_USER="${service_user}"

export DEBIAN_FRONTEND=noninteractive

apt-get update -y
apt-get install -y --no-install-recommends git python3 python3-venv python3-pip ca-certificates

if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
  useradd -m -s /bin/bash "$SERVICE_USER"
fi

mkdir -p "$(dirname "$APP_DIR")"
chown -R "$SERVICE_USER":"$SERVICE_USER" "$(dirname "$APP_DIR")"

if [[ -d "$APP_DIR/.git" ]]; then
  sudo -u "$SERVICE_USER" git -C "$APP_DIR" fetch --all --prune
  sudo -u "$SERVICE_USER" git -C "$APP_DIR" reset --hard origin/main
else
  sudo -u "$SERVICE_USER" git clone "$REPO_URL" "$APP_DIR"
fi

sudo -u "$SERVICE_USER" python3 -m venv "$APP_DIR/.venv"
sudo -u "$SERVICE_USER" bash -lc "source \"$APP_DIR/.venv/bin/activate\" && pip install -U pip && pip install -r \"$APP_DIR/requirements.txt\""

if [[ ! -f /etc/mark6-bot.env ]]; then
  cat >/etc/mark6-bot.env <<'EOF'
TELEGRAM_BOT_TOKEN=
EOF
  chmod 600 /etc/mark6-bot.env
fi

cat >/etc/systemd/system/mark6-bot.service <<EOF
[Unit]
Description=Mark6 Telegram Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$APP_DIR
EnvironmentFile=/etc/mark6-bot.env
ExecStart=$APP_DIR/.venv/bin/python $APP_DIR/telegram_bot.py
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload

if systemctl is-enabled --quiet mark6-bot; then
  systemctl restart mark6-bot || true
fi

