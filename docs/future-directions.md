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

