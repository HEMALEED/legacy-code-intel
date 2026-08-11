#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# LegacyLens — install systemd services for uvicorn + celery
# Run once as a user with sudo:  bash scripts/install-services.sh
# ─────────────────────────────────────────────────────────────────────────────
set -e

PROJECT=/ai-data/projects/legacy-code-intel
VENV=$PROJECT/backend/.venv
USER=$(whoami)

echo "Installing LegacyLens systemd services for user: $USER"
echo "Project root: $PROJECT"

# ── 1. legacylens-backend.service (uvicorn) ───────────────────────────────────
sudo tee /etc/systemd/system/legacylens-backend.service > /dev/null <<EOF
[Unit]
Description=LegacyLens FastAPI backend (uvicorn)
After=network.target docker.service
Wants=docker.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT/backend
Environment="PATH=$VENV/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$VENV/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# ── 2. legacylens-celery.service (celery worker) ─────────────────────────────
sudo tee /etc/systemd/system/legacylens-celery.service > /dev/null <<EOF
[Unit]
Description=LegacyLens Celery worker
After=network.target docker.service legacylens-backend.service
Wants=docker.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT/backend
Environment="PATH=$VENV/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$VENV/bin/celery -A celery_worker worker --loglevel=info --concurrency=2
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# ── 3. Enable docker to start on boot ────────────────────────────────────────
sudo systemctl enable docker 2>/dev/null || true

# ── 4. Reload systemd and enable services ────────────────────────────────────
sudo systemctl daemon-reload
sudo systemctl enable legacylens-backend.service
sudo systemctl enable legacylens-celery.service

echo ""
echo "✓ Services installed and enabled."
echo ""
echo "To start now:"
echo "  sudo systemctl start legacylens-backend legacylens-celery"
echo ""
echo "To check status:"
echo "  sudo systemctl status legacylens-backend legacylens-celery"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u legacylens-backend -f"
echo "  sudo journalctl -u legacylens-celery -f"
