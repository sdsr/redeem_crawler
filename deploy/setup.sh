#!/bin/bash
# ==============================================
# Redeem Vault - GCP VM 초기 셋업 스크립트
# Ubuntu 24.04 LTS 기준
# ==============================================
set -e

APP_NAME="redeemvault"
APP_DIR="/home/$USER/redeem_scroll"
VENV_DIR="$APP_DIR/venv"

echo "=========================================="
echo "  Redeem Vault 서버 셋업 시작"
echo "=========================================="

# 1. 시스템 패키지 업데이트 및 설치
echo "[1/6] 시스템 패키지 설치..."
sudo apt update
sudo apt install -y python3 python3-pip python3-venv nginx git

# 2. Python 가상환경 생성 및 패키지 설치
echo "[2/6] Python 가상환경 설정..."
cd "$APP_DIR"
python3 -m venv venv
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt

# 3. DB 초기화 (첫 실행)
echo "[3/6] DB 초기화..."
python -c "from database.models import init_db; init_db()"
echo "  DB 초기화 완료"

# 4. systemd 서비스 등록
echo "[4/6] systemd 서비스 등록..."
sudo tee /etc/systemd/system/${APP_NAME}.service > /dev/null <<SERVICEEOF
[Unit]
Description=Redeem Vault Flask App
After=network.target

[Service]
User=$USER
Group=$USER
WorkingDirectory=$APP_DIR
ExecStart=$VENV_DIR/bin/gunicorn -c gunicorn_config.py web_app:app
Restart=always
RestartSec=5
Environment="PATH=$VENV_DIR/bin:/usr/bin"

[Install]
WantedBy=multi-user.target
SERVICEEOF

sudo systemctl daemon-reload
sudo systemctl enable ${APP_NAME}
sudo systemctl start ${APP_NAME}
echo "  서비스 시작 완료"

# 5. Nginx 설정
echo "[5/6] Nginx 설정..."
sudo tee /etc/nginx/sites-available/${APP_NAME} > /dev/null <<NGINXEOF
server {
    listen 80;
    server_name _;

    # 정적 파일
    location /static/ {
        alias $APP_DIR/static/;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    # 프록시
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
    }
}
NGINXEOF

# 기본 사이트 비활성화, 새 설정 활성화
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/${APP_NAME} /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
echo "  Nginx 설정 완료"

# 6. cron 등록 (매 6시간마다 스크래핑)
echo "[6/6] cron 등록..."
CRON_CMD="0 */6 * * * cd $APP_DIR && $VENV_DIR/bin/python main.py >> $APP_DIR/scrape.log 2>&1"
(crontab -l 2>/dev/null | grep -v "redeem_scroll"; echo "$CRON_CMD") | crontab -
echo "  cron 등록 완료 (매 6시간 스크래핑)"

# 완료
echo ""
echo "=========================================="
echo "  셋업 완료!"
echo "=========================================="
echo ""
echo "  서비스 상태:  sudo systemctl status ${APP_NAME}"
echo "  로그 확인:    sudo journalctl -u ${APP_NAME} -f"
echo "  Nginx 상태:   sudo systemctl status nginx"
echo "  수동 스크래핑: cd $APP_DIR && source venv/bin/activate && python main.py"
echo ""
EXTERNAL_IP=$(curl -s http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip -H "Metadata-Flavor: Google" 2>/dev/null || echo "<외부IP>")
echo "  접속 주소:    http://$EXTERNAL_IP"
echo ""
