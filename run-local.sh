# local PostgreSQL 사용
set -e

cd "$(dirname "$0")"

echo "================================"
echo " LOCAL DATABASE MODE"
echo " DB_HOST = db"
echo "================================"

docker compose \
  --env-file .env \
  up -d --force-recreate web nginx

echo ""
echo "Backend is using LOCAL PostgreSQL."
