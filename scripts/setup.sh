#!/usr/bin/env bash
set -e

echo "=== AOI Studio Setup ==="

# .env ファイルの作成
if [ ! -f .env ]; then
  cp .env.example .env
  echo "✅ .env を作成しました（必要に応じて編集してください）"
fi

# Docker Compose でサービス起動
echo "🐳 Docker Compose でサービスを起動中..."
docker compose up -d postgres redis

echo "⏳ PostgreSQL の起動を待機中..."
until docker compose exec postgres pg_isready -U aoi -d aoi_studio > /dev/null 2>&1; do
  sleep 1
done

echo "📦 Alembic マイグレーションを実行中..."
docker compose run --rm backend alembic upgrade head

echo ""
echo "✅ セットアップ完了！"
echo ""
echo "サービスを起動するには:"
echo "  docker compose up"
echo ""
echo "アクセス先:"
echo "  Frontend: http://localhost:3000"
echo "  Backend:  http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
