# AOI Studio — アーキテクチャ設計書

**Version**: 0.1  
**Date**: 2026-07-05  
**Status**: Draft（承認待ち）

---

## 目次

1. [プロダクト概要](#1-プロダクト概要)
2. [全体アーキテクチャ](#2-全体アーキテクチャ)
3. [技術選定](#3-技術選定)
4. [データモデル設計](#4-データモデル設計)
5. [AIエージェント構成](#5-aiエージェント構成)
6. [Premiere Pro 連携方式](#6-premiere-pro-連携方式)
7. [画面構成（IA）](#7-画面構成ia)
8. [ロードマップ](#8-ロードマップ)
9. [非機能要件](#9-非機能要件)
10. [未解決の設計課題](#10-未解決の設計課題)

---

## 1. プロダクト概要

### ミッション

> 動画を編集するのではなく、動画を設計する。

AOI Studio は、AIがクリエイティブディレクターとして機能する動画制作プラットフォームです。従来の「撮影 → 編集 → 書き出し」という事後処理型のワークフローを、「企画 → 設計 → 撮影 → 編集 → 納品」という設計駆動型ワークフローに変えます。

### 対象ユーザー（MVP時点）

- 動画制作を外注しているが内製化したい中小企業の担当者
- 動画制作の経験が浅いクリエイター（1〜3年目）
- 動画制作会社の若手ディレクター

### 解決する課題

| 課題 | 現状 | AOI Studio での解決 |
|------|------|-------------------|
| 撮影漏れ | 現場で気づく | 事前に撮影リストを自動生成 |
| 構成の属人化 | ベテランの経験に依存 | AIが客観的な構成を提案 |
| 音楽とカット割りの不一致 | 編集中に試行錯誤 | 音楽解析を先行させカット数を設計 |
| Premiere作業の長時間化 | 全工程を手動 | ジャンプカット・テロップ・BGMをAIが処理 |

---

## 2. 全体アーキテクチャ

### システム構成図

```
┌─────────────────────────────────────────────────────────────────┐
│                        ユーザーブラウザ                           │
│                    Next.js (App Router)                         │
│        ┌──────────┬──────────┬──────────┬──────────┐           │
│        │ Project  │ Design   │ Storyboard│ Timeline │           │
│        │ Wizard   │ Canvas   │ Editor   │ View     │           │
│        └────┬─────┴────┬─────┴────┬─────┴────┬─────┘           │
└────────────┼──────────┼──────────┼──────────┼──────────────────┘
             │ HTTPS/WSS │          │          │
┌────────────▼──────────▼──────────▼──────────▼──────────────────┐
│                      API Gateway (FastAPI)                      │
│   /api/v1/projects  /api/v1/ai  /api/v1/media  /api/v1/export  │
└──────┬──────────────┬───────────────┬──────────────┬───────────┘
       │              │               │              │
┌──────▼──────┐ ┌─────▼──────┐ ┌─────▼──────┐ ┌────▼──────────┐
│  Project    │ │  AI Agent  │ │   Media    │ │   Export      │
│  Service   │ │  Orchestr. │ │  Service   │ │   Service     │
│  (CRUD)    │ │  (LangGraph)│ │  (Upload)  │ │  (PPro/EDL)   │
└──────┬──────┘ └─────┬──────┘ └─────┬──────┘ └────┬──────────┘
       │              │               │              │
┌──────▼──────────────▼───────────────▼──────────────▼──────────┐
│                       Data Layer                               │
│   PostgreSQL        Redis          S3/R2        Vector DB      │
│   (主データ)       (セッション/    (メディア)   (Qdrant:       │
│                    キャッシュ)                  参考事例検索)   │
└───────────────────────────────────────────────────────────────┘
       │
┌──────▼──────────────────────────────────────────────────────┐
│                    外部サービス                              │
│   Anthropic Claude API  |  Essentia (音楽解析)              │
│   Whisper (文字起こし)  |  FFmpeg (動画処理)                │
│   Adobe UXP API         |  SendGrid (メール通知)            │
└─────────────────────────────────────────────────────────────┘
```

### データフロー（制作フロー別）

```
[Phase 1-2: 企画・仕様設計]
User Input → API → Claude Agent → Project Spec (JSON) → DB保存

[Phase 3: 音楽解析]
音楽ファイル → Media Service → Essentia解析 → Beat/Section情報 → DB保存
                                ↓
                         タイムライン骨格生成

[Phase 4: 構成提案]
Project Spec + Timeline骨格 → Claude Agent → 構成案 (JSON) → フロント表示

[Phase 5: 絵コンテ生成]
構成案 → Claude Agent → 絵コンテ (JSON) → SVGレンダリング → 表示

[Phase 6: 撮影リスト]
絵コンテ → Claude Agent → 撮影リスト (JSON) → PDF/CSV出力

[Phase 7: 素材照合]
アップロード素材 → Whisper/FFmpeg解析 → 絵コンテ照合 → 不足通知

[Phase 8: Premiere連携]
編集データ (JSON) → Export Service → .prproj / XML / EDL → Premiere Pro
```

---

## 3. 技術選定

### Frontend

| 技術 | 採用理由 |
|------|---------|
| **Next.js 14 (App Router)** | SSR/SSGの柔軟性、Server Actions によるフォーム処理簡素化、将来的なSEO対応 |
| **TypeScript** | 複数人開発での型安全性、AIが生成するJSONとの型整合性管理 |
| **Tailwind CSS** | デザインシステム構築の速度、カスタムUIコンポーネントとの親和性 |
| **Zustand** | 軽量な状態管理。Redux より低学習コスト、制作フローの進捗状態管理に最適 |
| **React Query (TanStack)** | サーバー状態とキャッシュ管理。AI処理の非同期ポーリングに活用 |
| **Framer Motion** | 制作フロー遷移のアニメーション（クリエイティブツールとしての体験品質） |

### Backend

| 技術 | 採用理由 |
|------|---------|
| **FastAPI (Python)** | AI/ML ライブラリとの親和性が最高。async対応、自動OpenAPI生成 |
| **PostgreSQL** | 構造化データ（プロジェクト、構成、絵コンテ）の管理。JSONBでスキーマ柔軟性を確保 |
| **Redis** | AIエージェントの処理状態管理、WebSocketセッション、レート制限 |
| **SQLAlchemy 2.0 + Alembic** | 型安全なORM、スキーママイグレーション管理 |
| **Celery** | 音楽解析・動画処理などの重い非同期タスク処理 |

### AI

| 技術 | 用途 | 採用理由 |
|------|------|---------|
| **Claude API (claude-sonnet-4-6)** | 構成提案・絵コンテ生成・撮影リスト | 長文構造化出力、日本語品質、tool use |
| **LangGraph** | AIエージェントのオーケストレーション | ステート管理、複数エージェント協調、条件分岐 |
| **Essentia** | 音楽解析（BPM・セクション検出） | オープンソース、精度高、Python対応 |
| **OpenAI Whisper** | 動画内音声の文字起こし | ローカル実行可、多言語対応 |
| **Qdrant** | 参考動画・ブランド事例のベクトル検索 | 軽量、セルフホスト可、フィルタリング機能 |

### Infrastructure

| 技術 | 採用理由 |
|------|---------|
| **Docker / Docker Compose** | ローカル開発環境の再現性、本番移行の容易さ |
| **Cloudflare R2** | S3互換、egress無料、動画ファイルのコスト最適化 |
| **GitHub Actions** | CI/CD。テスト自動化、Dockerイメージビルド |
| **Render / Railway** (初期) | 低コストでFastAPI + PostgreSQLをホスト。スケール時にAWSへ移行 |

---

## 4. データモデル設計

### 主要エンティティ

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────────┐
│    User     │──┬──│    Project      │──┬──│   VideoSpec      │
│─────────────│  │  │─────────────────│  │  │──────────────────│
│ id          │  │  │ id              │  │  │ id               │
│ email       │  │  │ user_id (FK)    │  │  │ project_id (FK)  │
│ name        │  │  │ title           │  │  │ duration_sec     │
│ created_at  │  │  │ video_type      │  │  │ target_audience  │
└─────────────┘  │  │ status          │  │  │ message          │
                 │  │ created_at      │  │  │ mood             │
                 │  └─────────────────┘  │  │ color_palette    │
                 │                       │  │ reference_urls   │
                 │  ┌─────────────────┐  │  └──────────────────┘
                 └──│    Music        │  │
                    │─────────────────│  │  ┌──────────────────┐
                    │ id              │  └──│   Structure      │
                    │ project_id (FK) │     │──────────────────│
                    │ file_url        │     │ id               │
                    │ bpm             │     │ project_id (FK)  │
                    │ duration_sec    │     │ scenes (JSONB)   │
                    │ sections (JSONB)│     │ version          │
                    │ beat_map (JSONB)│     │ approved_at      │
                    └─────────────────┘     └──────────────────┘

┌─────────────────────┐     ┌──────────────────────┐
│    Storyboard       │     │    ShootingList       │
│─────────────────────│     │──────────────────────│
│ id                  │     │ id                    │
│ project_id (FK)     │     │ project_id (FK)       │
│ scenes (JSONB)      │     │ shots (JSONB)         │
│ version             │     │ generated_at          │
│ generated_at        │     └──────────────────────┘
└─────────────────────┘

┌─────────────────────┐     ┌──────────────────────┐
│    MediaAsset       │     │    EditTimeline       │
│─────────────────────│     │──────────────────────│
│ id                  │     │ id                    │
│ project_id (FK)     │     │ project_id (FK)       │
│ file_url            │     │ tracks (JSONB)        │
│ file_type           │     │ exported_at           │
│ duration_sec        │     │ export_format         │
│ transcript (JSONB)  │     └──────────────────────┘
│ matched_scene_id    │
│ uploaded_at         │
└─────────────────────┘
```

### scenes (JSONB) スキーマ例

```json
{
  "scenes": [
    {
      "id": "scene_001",
      "order": 1,
      "time_start": 0,
      "time_end": 3,
      "title": "冒頭フック",
      "intent": "視聴者の興味を引く",
      "composition": "人物クローズアップ + テキストオーバーレイ",
      "camera_work": "静止 → ゆっくりズームイン",
      "text_overlay": "あなたの仕事を、もっと自由に。",
      "required_shots": ["shot_003", "shot_007"]
    }
  ]
}
```

---

## 5. AIエージェント構成

### エージェント全体図（LangGraph）

```
                    ┌─────────────────┐
                    │  Orchestrator   │
                    │    Agent        │
                    └────────┬────────┘
                             │ ルーティング
          ┌──────────────────┼──────────────────┐
          │                  │                  │
  ┌───────▼────────┐ ┌───────▼────────┐ ┌──────▼─────────┐
  │  Spec Analyst  │ │ Music Analyzer │ │ Structure Agent│
  │  (仕様整理)    │ │ (音楽解析)     │ │ (構成提案)     │
  └───────┬────────┘ └───────┬────────┘ └──────┬─────────┘
          │                  │                  │
          └──────────────────▼──────────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
  ┌───────▼────────┐ ┌───────▼────────┐ ┌──────▼─────────┐
  │  Storyboard    │ │ Shooting List  │ │  Edit Agent    │
  │  Agent         │ │ Agent          │ │  (編集指示生成) │
  │ (絵コンテ生成) │ │ (撮影リスト)   │ │               │
  └───────┬────────┘ └───────┬────────┘ └──────┬─────────┘
          │                  │                  │
          └──────────────────▼──────────────────┘
                             │
                    ┌────────▼────────┐
                    │  Export Agent  │
                    │ (Premiere連携)  │
                    └─────────────────┘
```

### 各エージェントの役割

| エージェント | 入力 | 出力 | 使用モデル |
|------------|------|------|----------|
| **Orchestrator** | ユーザーアクション | 次エージェントへのルーティング | claude-sonnet-4-6 |
| **Spec Analyst** | 自然言語の動画目的 | VideoSpec JSON | claude-sonnet-4-6 |
| **Music Analyzer** | 音楽ファイル | BPM・セクション・ビートマップ | Essentia (非LLM) |
| **Structure Agent** | VideoSpec + 音楽解析結果 | 構成案 JSON (scenes配列) | claude-sonnet-4-6 |
| **Storyboard Agent** | 構成案 | 絵コンテ JSON（構図・カメラ・テキスト） | claude-sonnet-4-6 |
| **Shooting List Agent** | 絵コンテ | 撮影リスト JSON + PDF | claude-sonnet-4-6 |
| **Edit Agent** | 素材 + 絵コンテ | 編集タイムライン JSON | claude-sonnet-4-6 |
| **Export Agent** | 編集タイムライン | .prproj / XML / EDL | ルールベース |

### エージェント間の状態管理

```python
# LangGraph State（概念）
class AOIStudioState(TypedDict):
    project_id: str
    video_spec: VideoSpec
    music_analysis: MusicAnalysis | None
    structure: VideoStructure | None
    storyboard: Storyboard | None
    shooting_list: ShootingList | None
    media_assets: list[MediaAsset]
    edit_timeline: EditTimeline | None
    current_phase: Phase
    errors: list[str]
    human_feedback: str | None  # ユーザーの修正指示
```

---

## 6. Premiere Pro 連携方式

### 方式比較

| 方式 | 概要 | メリット | デメリット | 採用判断 |
|------|------|---------|----------|---------|
| **ExtendScript** | 旧API（JSX） | 枯れた技術、情報多い | 2023年以降非推奨、非同期弱い | ❌ 不採用 |
| **CEP Extension** | HTML+JSパネル | 現行サポート、柔軟 | 廃止予定（2025年末〜） | ❌ 不採用 |
| **UXP + PPro API** | 新公式API | Adobe公式推奨、将来性 | ドキュメント少、まだ機能限定 | ✅ **採用**（主軸） |
| **XML/EDL Import** | 標準ファイル形式 | Premireに依存しない | 細かい制御不可 | ✅ **採用**（フォールバック） |

### 採用アーキテクチャ

```
AOI Studio Web
     │
     │ JSON (EditTimeline)
     ▼
Export Service (Python)
     │
     ├── UXP Plugin (.ccx) ──→ Premiere Pro (ネイティブ操作)
     │    └── シーケンス生成、クリップ配置、テロップ挿入
     │
     └── XML / EDL エクスポート ──→ Premiere Pro (ファイルインポート)
          └── フォールバック or UXP非対応環境向け
```

### MVP での Premiere 連携スコープ

- **MVP**: XML/EDL 形式でのエクスポートのみ（UXP は Phase 3 以降）
- **Phase 3**: UXP プラグイン開発（シーケンス自動生成）
- **Phase 5**: UXP による完全自動編集（ジャンプカット・テロップ・BGM）

---

## 7. 画面構成（IA）

### サイトマップ

```
AOI Studio
│
├── / (Landing)
│
├── /auth
│   ├── /login
│   └── /signup
│
├── /dashboard
│   ├── プロジェクト一覧
│   └── 新規プロジェクト作成ボタン
│
└── /projects/:id
    ├── /setup        ← Phase 1-2: 動画仕様入力
    ├── /music        ← Phase 3: 音楽選択・解析
    ├── /structure    ← Phase 4: 構成確認・編集
    ├── /storyboard   ← Phase 5: 絵コンテ確認・編集
    ├── /shooting     ← Phase 6: 撮影リスト
    ├── /upload       ← Phase 7: 素材アップロード・照合
    └── /export       ← Phase 8: Premiere 書き出し
```

### 主要画面の概要

#### `/dashboard`
- プロジェクトカード一覧（サムネイル・進捗ステータス・最終更新日）
- 新規プロジェクト作成（動画タイプ選択から開始）
- フィルタ：動画タイプ / ステータス / 日付

#### `/projects/:id/setup`
- **Step 1**: 動画タイプ選択（ブランド動画 / SNS広告 / 採用動画 など）
- **Step 2**: 動画仕様フォーム（尺・ターゲット・メッセージ・世界観・参考URL）
- **Step 3**: AI が仕様を整理してサマリーを表示 → 承認 or 修正

#### `/projects/:id/music`
- 音楽ファイルアップロード（または楽曲検索 ※将来）
- 解析結果の可視化：波形 + BPM + セクション（イントロ/サビ/アウトロ）
- タイムライン骨格のプレビュー

#### `/projects/:id/structure`
- AIが提案した構成案（シーン一覧）
- ドラッグ&ドロップでシーン並び替え
- 各シーンの秒数・意図を編集
- 「再提案」ボタン（AIに別案を要求）

#### `/projects/:id/storyboard`
- 横スクロールのコマ割り表示
- 各コマ：構図イメージ（SVG）・カメラワーク・テキスト・撮影意図
- コメント追加・承認ワークフロー（将来：チーム機能）

#### `/projects/:id/shooting`
- カテゴリ別撮影リスト（外観 / 人物 / 商品 / Bロール など）
- チェックリスト形式（撮影完了マーク）
- PDF / CSV エクスポート

#### `/projects/:id/upload`
- ドラッグ&ドロップ素材アップロード
- AI照合結果：「このカットは scene_003 に対応」「scene_007 の素材が不足」
- 不足カット一覧と再撮影推奨

#### `/projects/:id/export`
- 編集タイムラインのプレビュー
- エクスポート形式選択（XML / EDL / UXP）
- Premiere Pro 起動ボタン（UXP 経由）

---

## 8. ロードマップ

### MVP（目標: 設計後4週間）

**スコープ**: 動作する骨格を作る

- [ ] Docker Compose でのローカル開発環境
- [ ] FastAPI 基盤（ヘルスチェック、CORS、認証ミドルウェア）
- [ ] PostgreSQL マイグレーション基盤（Alembic）
- [ ] Next.js 基盤（認証画面、ダッシュボード、ルーティング）
- [ ] ユーザー認証（JWT）
- [ ] プロジェクト CRUD API
- [ ] `GET /health` が返る状態を本番環境にデプロイ

**完了条件**: ログイン → プロジェクト作成 → 一覧表示 が動作すること

---

### Phase 1（目標: MVP後3週間）

**スコープ**: AI構成提案の最小動作

- [ ] 動画仕様入力フォーム（`/setup`）
- [ ] Spec Analyst Agent 実装
- [ ] Structure Agent 実装
- [ ] 構成案表示画面（`/structure`）
- [ ] 構成案の承認・修正フロー

**完了条件**: 動画タイプと仕様を入力するとAIが構成を提案し、ユーザーが承認できること

---

### Phase 2（目標: Phase 1後3週間）

**スコープ**: 音楽解析とタイムライン連携

- [ ] 音楽ファイルアップロード（R2）
- [ ] Essentia による音楽解析パイプライン
- [ ] 音楽解析結果の可視化
- [ ] 音楽ベースの構成案改善（Structure Agent のアップデート）
- [ ] 絵コンテ生成（`/storyboard`）
- [ ] 撮影リスト生成・PDF出力（`/shooting`）

**完了条件**: 音楽をアップロードすると構成にタイミングが反映され、絵コンテと撮影リストが生成されること

---

### Phase 3（目標: Phase 2後4週間）

**スコープ**: 素材照合とPremiere連携

- [ ] 動画素材アップロード・解析
- [ ] 絵コンテとの照合ロジック
- [ ] 不足カット通知
- [ ] XML/EDL エクスポート
- [ ] UXP Plugin プロトタイプ

**完了条件**: 素材をアップロードすると不足カットが通知され、XML形式でPremiere Proにインポートできること

---

## 9. 非機能要件

| 項目 | 要件 | 備考 |
|------|------|------|
| **レスポンスタイム** | 通常API: < 300ms | AI処理は非同期（WebSocket通知） |
| **AI処理時間** | 構成提案: < 30秒 | ストリーミングで進捗表示 |
| **ファイルサイズ上限** | 動画: 4GB / 音楽: 100MB | MVP時点 |
| **同時ユーザー** | MVP: 〜50名 | スケール時にWorker数増加 |
| **データ保持** | プロジェクトデータ: 無期限 | メディアファイル: 90日（MVP） |
| **セキュリティ** | JWT認証、HTTPS必須、S3署名付きURL | |
| **ブラウザ対応** | Chrome 最新版、Safari 最新版 | |

---

## 10. 未解決の設計課題

以下は設計上未決定の項目です。実装前に合意が必要です。

### 高優先度（解決済み 2026-07-06）

1. **音楽の著作権処理** ✅  
   MVPはアップロード時に著作権警告を表示するのみ。著作権フリーライブラリ連携はPhase 2以降。

2. **AIの提案スタイル** ✅  
   **段階絞り込み方式**を採用。構成案は3案を同時提示してユーザーが選択し、選択後に絵コンテを1案生成する。APIコスト削減と選択の質を両立する。

3. **チーム機能** ✅  
   MVPは1ユーザー1人用。ただし**データモデルは将来の複数人対応を見据えた設計**（Organizationエンティティを初期から含める）。チーム共有機能はPhase 2以降。

4. **モバイル対応** ✅  
   **撮影リスト画面（`/shooting`）のみ**を早期にモバイル対応。他の画面はデスクトップ優先で開発。

### 低優先度（Phase 2以降で判断）

5. **絵コンテの画像生成**  
   テキスト説明 + SVG での簡易表現か、画像生成AI（Firefly等）で実際の絵コンテ画像を生成するか。

6. **楽曲検索機能**  
   Artlist / Epidemic Sound などのAPIと連携して、プラットフォーム内で楽曲選定まで完結させるか。

7. **テンプレート機能**  
   過去の制作事例を再利用できるテンプレートライブラリ。

---

*このドキュメントは承認後、`docs/` 配下に詳細仕様書として分割される予定です。*
