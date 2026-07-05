# AOI Studio

> 動画を編集するのではなく、動画を設計する。

AOI Studio は、AIがクリエイティブディレクターとして機能する動画制作プラットフォームです。企画・設計・撮影・編集・納品までの全工程をAIが支援し、誰でも高品質な動画を制作できる世界を目指します。

## Vision

従来の動画制作フロー（撮影 → 編集 → 書き出し）を根本から変え、**完成した動画を最初に設計し、その設計図から逆算して制作全体を導く**新しいワークフローを実現します。

```
企画 → 設計 → 撮影 → 編集 → 納品
```

## Core Features（ロードマップ）

| Phase | 機能 | 状態 |
|-------|------|------|
| MVP | プロジェクト基盤・認証・UI骨格 | 🚧 開発中 |
| Phase 1 | 動画仕様入力・AI構成提案 | 📋 計画中 |
| Phase 2 | 音楽解析・タイムライン生成 | 📋 計画中 |
| Phase 3 | 絵コンテ生成・撮影リスト | 📋 計画中 |
| Phase 4 | 素材アップロード・AI編集 | 📋 計画中 |
| Phase 5 | Premiere Pro 連携 | 📋 計画中 |

## Tech Stack

- **Frontend**: Next.js 14 (App Router) + TypeScript + Tailwind CSS
- **Backend**: FastAPI (Python) + PostgreSQL + Redis
- **AI**: Claude API (Anthropic) + Whisper + Music Analysis
- **Storage**: AWS S3 / Cloudflare R2
- **Infrastructure**: Docker + GitHub Actions

## Getting Started

```bash
# リポジトリをクローン
git clone https://github.com/chiakibancho/AOI-Studio.git
cd AOI-Studio

# 依存関係のインストール（詳細は各ディレクトリのREADMEを参照）
```

## Project Structure

```
AOI-Studio/
├── docs/           # 設計書・仕様書
├── frontend/       # Next.js フロントエンド
├── backend/        # FastAPI バックエンド
├── ai/             # AIエージェント・モデル
├── infra/          # インフラ設定（Docker, CI/CD）
└── scripts/        # 開発用スクリプト
```

## License

MIT License — see [LICENSE](LICENSE) for details.
