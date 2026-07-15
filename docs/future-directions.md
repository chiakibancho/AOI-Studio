# AOI Studio 設計方針追加仕様
## Obsidian Knowledge Vault連携

AOI Studioの設計思想を一部見直します。

## 最重要方針

AOI Studioは「AIがブランド映像を考えるアプリ」ではありません。

AOI Studioは

**クリエイターの思考を蓄積し、必要な時に呼び出せるクリエイティブOS**

を目指します。

AIは考える主体ではなく、
クリエイターの思考を整理・検索・再利用するアシスタントとして設計してください。

---

# Reference Analysisの考え方

Reference Analysisは自動分析を目的としません。

ユーザー自身がブランド映像を分析し、
その知識を蓄積することを目的とします。

つまり

手書き
↓
Markdown化
↓
Obsidianへ保存

というワークフローを基本とします。

AIはMarkdown化や整理を支援します。

---

# ObsidianをSingle Source of Truthにする

AOI Studio内にもデータは保持しますが、

クリエイティブ知識の保存先はObsidianを基本とします。

将来的にはObsidian Vaultを読み込み、

Reference Analysis
Video Spec
過去のブランド分析

などを検索・参照できる構造を目指します。

---

# 推奨フォルダ構成

AOI Studio/

Architecture Meetings/

Reference Analysis/

Video Specs/

Product Decisions/

Ideas/

Knowledge/

Brands/

Moodboards/

---

# Reference Analysisテンプレート

各分析はMarkdownで保存します。

例

# タイトル

## Reference

URL:

Brand:

Length:

Platform:

Date:

---

## Story Structure

---

## Emotion Curve

---

## Scene Breakdown

---

## Camera

---

## Music

---

## Brand Message

---

## Learned Principles

---

## AOI Studioへの反映

Video Spec候補

再利用できるブランド構造

---

# Product Meeting

AOI Studio開発では

Architecture Meetings

を残します。

毎回

・議題

・検討内容

・採用理由

・見送った案

をMarkdownとして保存してください。

後から

「なぜこの設計になったのか」

を追跡できることを重視します。

---

# 将来的な実装

将来的には

Analyze Notebook

機能を追加し、

手書きノート写真

↓

OCR

↓

Markdown化

↓

Reference Analysisテンプレートへ変換

↓

Obsidian保存

までをサポートできる設計を検討してください。

ただし、

AIがReference Analysisを自動生成することは目的ではありません。

ユーザー自身の思考を蓄積することを最優先にしてください。

---

# プロダクト哲学

AIはクリエイターの代わりに考えません。

AIは

・整理する

・検索する

・比較する

・思い出させる

ことに集中します。

考えるのはクリエイターです。

AOI Studioは

「ブランド映像を作るAI」

ではなく、

「ブランド映像を考え続けられるクリエイティブOS」

を目指してください。

---

# 判断: Obsidian連携の見送り(2026-07-13)

今回のスコープではObsidian Knowledge Vault連携の実装は見送り、Phase 3以降の検討事項として残す。

## 理由

Phase 1で計画しているAI主導の3案提示ワークフロー(Spec Analyst Agent、Structure Agentによる3案同時提示)と、本メモが掲げる思想が逆方向になるため。

本メモの思想は「AIは考える主体ではなく、クリエイターの思考を整理・検索・再利用するアシスタント」であり、ユーザー自身の手書き・分析をMarkdown化してObsidianへ蓄積するワークフローを前提とする。一方Phase 1のAgentはAIが複数案を能動的に生成・提示する設計であり、両者は同時には成立しない。

## 今後の扱い

Phase 1〜2ではAI主導のAgentワークフローを優先して実装する。Obsidian連携の再検討は、Phase 3以降でプロダクトの方向性を再度見直すタイミングで行う。

---

# 動画生成AI連携の検討(Phase 3以降)

## 背景

現在のAOI Studioは、「テキストの設計書(構成案・絵コンテ)を生成し、クリエイターが撮影・編集する」という路線で設計されている。これはAPIコストを最小限に抑えつつクリエイターの判断と技術を活かす方針であり、「クリエイティブOSとしてのAOI Studio」という設計思想とも一致している。

## 将来の選択肢

動画生成AIとの連携を将来的に検討する。主な候補:

- Runway Gen-4(約$0.05/秒)
- Kling AI(約$0.03/秒)
- Together AI(Wan2.1等、コスパ重視)
- Adobe Firefly Video(CCプランのクレジット制。Premiere Proとの親和性が高く、Phase 3のPremiere連携と組み合わせると最も自然なワークフローになる可能性がある)

90秒動画を初稿+3回修正で生成した場合、$11〜$18程度が目安(2026年時点)。

## 実装方針(検討事項)

- Phase 3のPremiere連携(XML/EDL書き出し)を先に完成させ、「設計書→編集指示書」の流れを確立してから検討する
- 動画生成を導入する場合も、「AIが全部作る」ではなく「クリエイターが絵コンテを承認してからAIが動画化する」という人間主導のフローを維持する
- コスト管理として、1プロジェクトあたりの生成回数に上限を設ける設計を検討する

## 関連

手描き絵コンテ→画像生成(本ドキュメント既出の「Analyze Notebook」構想)と組み合わせると、「手描きラフ→AI動画化」という現場感覚に近いワークフローが実現できる可能性がある。

