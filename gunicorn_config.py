"""
Gunicorn 프로덕션 서버 설정
"""

# 바인드 주소 (Nginx가 프록시할 포트)
bind = "127.0.0.1:8000"

# 워커 수 (e2-micro: CPU 0.25 + RAM 1GB → 2개가 적정)
workers = 2

# 워커 타임아웃 (스크래핑이 오래 걸릴 수 있으므로 여유있게)
timeout = 120

# 로그
accesslog = "-"  # stdout
errorlog = "-"   # stderr
loglevel = "info"

# 프로세스 이름
proc_name = "redeemvault"

# Graceful restart
graceful_timeout = 30
