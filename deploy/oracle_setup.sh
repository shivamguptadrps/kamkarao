#!/bin/bash
# One-shot setup of KamKarao on a fresh Oracle Cloud server (Ubuntu 22.04/24.04 or Oracle Linux 8/9).
#
#   cd ~/kamkarao && bash deploy/oracle_setup.sh              # free address: <your-ip>.sslip.io
#   cd ~/kamkarao && bash deploy/oracle_setup.sh kamkarao.com  # your own domain (DNS must point here first)
#
# Safe to run again: it keeps an existing .env and only rebuilds and restarts.
set -euo pipefail
cd "$(dirname "$0")/.."

say() { printf '\n\033[1;32m==> %s\033[0m\n' "$*"; }

# 0. Which Linux? ------------------------------------------------------------------
if command -v apt-get >/dev/null 2>&1; then OS=debian; else OS=rhel; fi   # Ubuntu vs Oracle Linux
say "Detected: $(. /etc/os-release && echo "$PRETTY_NAME"), $(nproc) CPU, $(free -m | awk '/Mem:/{print $2}') MB RAM"

# 0b. Small servers (1 GB): add 2 GB swap so the build does not run out of memory ---
MEM_MB=$(free -m | awk '/Mem:/{print $2}')
if [ "$MEM_MB" -lt 2500 ] && [ ! -f /swapfile ]; then
  say "Adding 2 GB swap (small server)"
  sudo fallocate -l 2G /swapfile || sudo dd if=/dev/zero of=/swapfile bs=1M count=2048
  sudo chmod 600 /swapfile && sudo mkswap /swapfile >/dev/null && sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi
WORKERS=3; [ "$MEM_MB" -lt 2500 ] && WORKERS=2

# 1. Docker -------------------------------------------------------------------
if ! command -v docker >/dev/null 2>&1; then
  say "Installing Docker"
  if [ "$OS" = debian ]; then
    curl -fsSL https://get.docker.com | sudo sh
  else
    sudo dnf -y install dnf-plugins-core >/dev/null
    sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
    sudo dnf -y install docker-ce docker-ce-cli containerd.io docker-compose-plugin
  fi
  sudo systemctl enable --now docker
  sudo usermod -aG docker "$USER"
fi
DOCKER="docker"
if ! docker info >/dev/null 2>&1; then DOCKER="sudo docker"; fi

# 2. Open ports 80 and 443 in the server's own firewall --------------------------
# Oracle images block everything except SSH (iptables on Ubuntu, firewalld on Oracle
# Linux), in addition to the cloud "security list". Both must allow 80/443.
say "Opening ports 80 and 443 on this server"
if command -v firewall-cmd >/dev/null 2>&1 && sudo firewall-cmd --state >/dev/null 2>&1; then
  sudo firewall-cmd --permanent --add-service=http --add-service=https >/dev/null
  sudo firewall-cmd --reload >/dev/null
else
  for port in 80 443; do
    if ! sudo iptables -C INPUT -p tcp --dport "$port" -m state --state NEW -j ACCEPT 2>/dev/null; then
      sudo iptables -I INPUT 1 -p tcp --dport "$port" -m state --state NEW -j ACCEPT
    fi
  done
  if [ "$OS" = debian ]; then
    command -v netfilter-persistent >/dev/null 2>&1 || sudo DEBIAN_FRONTEND=noninteractive apt-get install -y iptables-persistent >/dev/null
    sudo netfilter-persistent save >/dev/null
  fi
fi

# cron (for nightly backups) is not always installed on minimal images
if ! command -v crontab >/dev/null 2>&1; then
  if [ "$OS" = debian ]; then sudo apt-get install -y cron >/dev/null; else sudo dnf -y install cronie >/dev/null && sudo systemctl enable --now crond; fi
fi

# 3. .env with strong secrets -----------------------------------------------------
if [ ! -f .env ]; then
  IP=$(curl -fsS https://api.ipify.org || curl -fsS https://ifconfig.me)
  DOMAIN="${1:-${IP//./-}.sslip.io}"
  say "Creating .env for https://$DOMAIN"
  SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
  PGPASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
  cat > .env <<EOF
DEBUG=False
SECRET_KEY=$SECRET
DOMAIN=$DOMAIN
ALLOWED_HOSTS=$DOMAIN,www.$DOMAIN
CSRF_TRUSTED_ORIGINS=https://$DOMAIN,https://www.$DOMAIN
SITE_URL=https://$DOMAIN
POSTGRES_PASSWORD=$PGPASS
# none = customers just enter their number (no SMS cost). Switch to msg91 or WhatsApp later.
OTP_PROVIDER=none
SUPPORT_WHATSAPP=
DAILY_REVEAL_LIMIT=20
NEARBY_ONLY_KM=2.5
WEB_WORKERS=$WORKERS
EOF
  chmod 600 .env
else
  say "Keeping existing .env"
  DOMAIN=$(grep '^DOMAIN=' .env | cut -d= -f2)
fi

# 4. Build and start --------------------------------------------------------------
say "Building and starting (first time takes 3–6 minutes)"
$DOCKER compose up -d --build

say "Waiting for the site to come up"
for i in $(seq 1 60); do
  CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://$DOMAIN/" || true)
  if [ "$CODE" != "000" ] && [ "$CODE" != "502" ]; then break; fi
  sleep 3
done
$DOCKER compose ps

# 5. Nightly backups --------------------------------------------------------------
if ! crontab -l 2>/dev/null | grep -q "deploy/backup.sh"; then
  (crontab -l 2>/dev/null; echo "0 3 * * * cd $(pwd) && sh deploy/backup.sh >> backups.log 2>&1") | crontab -
fi

say "Done!"
cat <<EOF

  Website : https://$DOMAIN
  Admin   : https://$DOMAIN/admin/

  Next, create your admin login:
      $DOCKER compose exec web python manage.py createsuperuser

  If the site does not open, check the Oracle "Security List" allows TCP 80 and 443
  (see DEPLOY_ORACLE.md, step 3). HTTPS can take a minute to appear the first time.

EOF
