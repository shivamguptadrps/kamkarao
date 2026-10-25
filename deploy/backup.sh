#!/bin/sh
# Daily database + photo backup. Add to the server's crontab:
#   0 3 * * * cd /home/ubuntu/kamkarao && sh deploy/backup.sh
set -e
STAMP=$(date +%Y-%m-%d)
mkdir -p backups
docker compose exec -T db pg_dump -U kamkarao kamkarao | gzip > "backups/db-$STAMP.sql.gz"
docker run --rm -v kamkarao_media:/m -v "$(pwd)/backups:/b" alpine tar czf "/b/media-$STAMP.tgz" -C /m .
# keep 14 days
find backups -type f -mtime +14 -delete
echo "Backup done: backups/db-$STAMP.sql.gz"
