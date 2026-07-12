import json
import re

import anthropic
from fastapi import HTTPException

from app.core.config import settings

VIDEO_TYPE_LABELS: dict[str, str] = {
    "brand": "ブランド動画",
    "corporate": "会社紹介動画",
    "recruitment": "採用動画",
    "sns_ad": "SNS広告",
    "youtube": "YouTube動画",
    "short": "ショート動画",
    "product_pr": "製品PR動画",
}

MOOD_VALUES: list[str] = [
    "professional",
    "casual",
    "emotional",
    "energetic",
    "luxury",
    "friendly",
    "serious",
    "playful",
]

_SHORT_DURATION_VIDEO_TYPES = {"sns_ad", "short"}


def _build_prompt(project, spec) -> str:
    video_type_label = VIDEO_TYPE_LABELS.get(
        project.video_type.value if hasattr(project.video_type, "value") else str(project.video_type),
        str(project.video_type),
    )

    style_notes_line = (
        f"- スタイルメモ: {spec.style_notes}" if spec.style_notes else ""
    )
    ref_urls_line = (
        f"- 参考URL: {', '.join(spec.reference_urls)}" if spec.reference_urls else ""
    )

    return f"""あなたはプロの映像ディレクターです。以下の動画仕様に基づいて、映像の構成（シーンリスト）を提案してください。

## プロジェクト情報
- タイトル: {project.title}
- 動画タイプ: {video_type_label}

## 動画仕様
- 目標尺: {spec.duration_sec}秒
- ターゲット層: {spec.target_audience}
- 伝えたいメッセージ: {spec.message}
- 雰囲気・トーン: {spec.mood}
{style_notes_line}
{ref_urls_line}

## 出力形式（必ず以下のJSON形式のみで出力してください。説明文は不要です）

{{
  "scenes": [
    {{
      "number": 1,
      "title": "シーン名",
      "duration_sec": 秒数,
      "description": "シーンの内容説明（2〜3文）",
      "shot_type": "カット種別（例: タイトルカード、インタビュー、Bロール、製品クローズアップ）",
      "mood": "このシーンの雰囲気",
      "notes": "撮影・編集上の注意点"
    }}
  ],
  "total_duration_sec": 合計秒数,
  "rationale": "この構成にした理由・意図（3〜5文）"
}}

シーン数は目標尺に合わせて適切に設定し（短尺なら3〜5シーン、長尺なら8〜15シーン）、各シーンが論理的な流れになるよう設計してください。"""


def _parse_json_response(text: str) -> dict:
    # コードブロック内の JSON を抽出する
    code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if code_block_match:
        json_text = code_block_match.group(1).strip()
    else:
        # コードブロックがなければテキスト全体を試みる
        json_text = text.strip()

    try:
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI レスポンスの JSON パースに失敗しました: {e}",
        )


async def generate_structure(project, spec) -> dict:
    """Claude API を使って動画構成を生成する。"""
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="ANTHROPIC_API_KEY が設定されていません。",
        )

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    prompt = _build_prompt(project, spec)

    try:
        message = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
            timeout=60,
        )
    except anthropic.APIError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Claude API エラー: {e}",
        )

    response_text = message.content[0].text
    return _parse_json_response(response_text)


def _build_spec_prompt(project, raw_input: str) -> str:
    video_type_value = project.video_type.value if hasattr(project.video_type, "value") else str(project.video_type)
    video_type_label = VIDEO_TYPE_LABELS.get(video_type_value, video_type_value)
    default_duration = 60 if video_type_value in _SHORT_DURATION_VIDEO_TYPES else 90
    mood_values_line = ", ".join(MOOD_VALUES)

    return f"""あなたはプロの映像ディレクターです。以下はユーザーが自由な文章で書いた、作りたい動画についての説明です。この内容を整理し、動画仕様（VideoSpec）として構造化してください。

## プロジェクト情報
- タイトル: {project.title}
- 動画タイプ: {video_type_label}

## ユーザーの入力（自然言語）
{raw_input}

## 出力形式（必ず以下のJSON形式のみで出力してください。説明文は不要です）

{{
  "duration_sec": 目標尺（秒、整数、5〜3600の範囲。ユーザーが尺を明言していない場合は {default_duration} を使う）,
  "target_audience": "ターゲット層（文章から読み取れない場合は動画タイプから妥当な内容を推測する）",
  "message": "伝えたいメッセージ（ユーザーの入力から要約・整理する）",
  "mood": "雰囲気・トーン。必ず次のいずれか1つの値を英語のまま出力する: {mood_values_line}",
  "style_notes": "スタイルに関する補足（特に言及がなければ空文字列）",
  "reference_urls": ["ユーザーが本文中で言及したURLのみを含める配列。最大5件まで。言及がなければ空配列"],
  "rationale": "ユーザーの入力をこのように解釈した理由・整理の意図（2〜4文）"
}}

ユーザーの入力に無い情報を大きく創作しないこと。読み取れない項目は、動画タイプや文脈から常識的に推測して埋め、rationale でその推測について触れてください。"""


async def analyze_spec(project, raw_input: str) -> dict:
    """Claude API を使って自然言語の入力から VideoSpec を整理する。"""
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="ANTHROPIC_API_KEY が設定されていません。",
        )

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    prompt = _build_spec_prompt(project, raw_input)

    try:
        message = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
            timeout=60,
        )
    except anthropic.APIError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Claude API エラー: {e}",
        )

    response_text = message.content[0].text
    return _parse_json_response(response_text)
