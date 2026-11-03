# Render PostgreSQL 사용
set -e

cd "$(dirname "$0")"

if [ ! -f ".env.render" ]; then
  echo ".env.render 파일이 없습니다."
  exit 1
fi

echo "================================"
echo " RENDER DATABASE MODE"
echo " WARNING: PRODUCTION DATABASE"
echo "================================"

docker compose \
  --env-file .env.render \
  -f compose.yaml \
  -f docker-compose.render.yml \
  up -d --force-recreate web nginx

echo ""
echo "Backend is using RENDER PostgreSQL."
