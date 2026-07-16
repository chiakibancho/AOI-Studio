import re

# shot_type（フレーミング指示）のマッピング。未知の値はそのまま素通しする。
_SHOT_TYPE_MAP: dict[str, str] = {
    "クローズアップ": "extreme close-up, face only",
    "ミディアムショット": "medium shot, upper body",
    "ミディアムクローズアップ": "medium close-up, face and upper chest",
    "ロングショット": "long shot, full body in environment",
    "バストショット": "bust shot, chest and above",
}

# location（背景・環境）の変換。複合語を先に置くことで、部分文字列の二重マッチを防ぐ。
_LOCATION_KEYWORDS: list[tuple[str, str]] = [
    ("高層階の夜景", "high-rise night cityscape background"),
    ("室内スタジオ", "indoor studio"),
    ("窓セット", "window set"),
    ("高層階", "high-rise"),
    ("夜景", "night cityscape background"),
    ("オフィスエントランス", "office entrance"),
    ("会議室", "meeting room"),
    ("ビル前", "in front of a building"),
    ("屋外", "outdoor"),
    ("屋内", "indoor"),
]

# equipmentの照明表現（レンズ以外）の変換。複合語を先に置く。
_LIGHTING_KEYWORDS: list[tuple[str, str]] = [
    ("暖色・ゴールデンアワー調", "warm golden hour window light, 3200-3800K"),
    ("冷色・低輝度", "cold low-intensity lighting, blue-toned shadows"),
    ("暖色", "warm-toned lighting"),
    ("冷色", "cold-toned lighting"),
    ("ゴールデンアワー", "golden hour lighting"),
    ("低輝度", "low-intensity lighting"),
    ("高輝度", "high-intensity lighting"),
    ("逆光", "backlit"),
    ("順光", "front-lit"),
]

_LENS_LABELS: dict[str, str] = {
    "24": "24mm wide-angle lens",
    "35": "35mm wide-normal lens",
    "50": "50mm standard lens",
    "85": "85mm portrait lens, shallow depth of field",
    "135": "135mm telephoto lens",
}

_MM_RE = re.compile(r"(\d+)\s*mm")
_F_STOP_RE = re.compile(r"F(\d+(?:\.\d+)?)", re.IGNORECASE)


def _translate_by_keywords(text: str, keyword_map: list[tuple[str, str]]) -> list[str]:
    """text中に含まれる既知キーワードを出現順(マップの並び順)に英訳して集める。

    マッチした部分文字列は remaining から取り除き、より短い/一般的な語による
    二重マッチ（例: "高層階の夜景" とマッチ後に "高層階" が再度マッチする）を防ぐ。
    """
    matched: list[str] = []
    remaining = text
    for jp, en in keyword_map:
        if jp in remaining:
            matched.append(en)
            remaining = remaining.replace(jp, "")
    return matched


def _translate_location(location: str) -> str:
    if not location:
        return ""
    matched = _translate_by_keywords(location, _LOCATION_KEYWORDS)
    return ", ".join(matched) if matched else location


def _translate_equipment(equipment: str) -> str:
    if not equipment:
        return ""
    parts: list[str] = []

    mm_match = _MM_RE.search(equipment)
    f_match = _F_STOP_RE.search(equipment)
    if mm_match:
        lens = _LENS_LABELS.get(mm_match.group(1), f"{mm_match.group(1)}mm lens")
        if f_match:
            lens = f"{lens} F{f_match.group(1)}"
        parts.append(lens)
    elif f_match:
        parts.append(f"shallow depth of field F{f_match.group(1)}")

    lighting = _translate_by_keywords(equipment, _LIGHTING_KEYWORDS)
    parts.extend(lighting[:1])  # 最も具体的な(最初にマッチした)照明表現のみ採用する

    return ", ".join(parts)


def generate_flux_prompt(shot: dict, character_prompt: str = "", style: str = "") -> str:
    """撮影リストのshot dictからFLUXプロンプトを組み立てる（ルールベース、Claude API不使用）。

    構成: character_prompt（あれば） → shot情報から生成した英語プロンプト → style（あれば）。
    """
    segments: list[str] = []

    if character_prompt.strip():
        segments.append(character_prompt.strip())

    shot_type = shot.get("shot_type", "")
    subject = shot.get("subject") or shot.get("title", "")
    framing = _SHOT_TYPE_MAP.get(shot_type, shot_type)
    if framing and subject:
        segments.append(f"{framing} of {subject}")
    elif framing:
        segments.append(framing)
    elif subject:
        segments.append(subject)

    location_en = _translate_location(shot.get("location", ""))
    if location_en:
        segments.append(f"Background: {location_en}")

    equipment_en = _translate_equipment(shot.get("equipment", ""))
    if equipment_en:
        segments.append(equipment_en)

    notes = shot.get("notes", "")
    if notes.strip():
        segments.append(notes.strip())

    if style.strip():
        segments.append(style.strip())

    return "\n".join(segments)
