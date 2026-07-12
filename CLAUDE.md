# AOI Studio

## フロントエンド型定義

`frontend/src/types/index.ts` の型は `frontend/src/types/api-generated.ts`（openapi-typescriptによる自動生成）のエイリアスになっている。backendのPydanticスキーマ（`app/schemas/`配下）を変更した場合は、以下の手順で型を再生成してからコミットすること。

```
cd backend && ./.venv/bin/python scripts/export_openapi.py > openapi.json
cd frontend && npm run gen:types
```

`backend/openapi.json` と `frontend/src/types/api-generated.ts` はどちらもコミット対象（静的スナップショット）。再生成を忘れると、フロントエンドの型がbackendの実際のスキーマと乖離する。
