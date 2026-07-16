"""撮影リストのshotからFLUXプロンプトを組み立てる（ルールベース、Claude API不使用）。"""

CATEGORY_FRAMING: dict[str, str] = {
    "people": "medium shot, person as main subject",
    "exterior": "wide establishing shot, outdoor environment",
    "product": "close-up, product detail shot",
    "broll": "cinematic b-roll, atmospheric shot",
    "other": "cinematic shot",
}

LOCATION_MAP: dict[str, str] = {
    "室内スタジオ": "indoor studio",
    "窓セット": "window set",
    "高層階": "high-rise",
    "夜景": "night cityscape",
    "屋外": "outdoor",
    "オフィス": "office",
}

EQUIPMENT_MAP: dict[str, str] = {
    "85mm": "85mm portrait lens",
    "135mm": "135mm telephoto lens",
    "50mm": "50mm standard lens",
    "F1.4": "shallow depth of field F1.4",
    "F1.8": "shallow depth of field F1.8",
    "F2.0": "shallow depth of field F2.0",
    "冷色": "cold blue-toned lighting",
    "暖色": "warm amber lighting",
    "ゴールデンアワー調": "golden hour quality light",
    "低輝度": "low intensity lighting",
    "サイドライト": "side lighting",
    "逆光": "backlight",
}

# notesは表情・演技・光の指示などの自由記述だが、Claude APIを使わないルールベース変換の
# 対象外（未知語）は日本語のまま出力に混ざってしまう（前回revertの根本原因）。
# 既知のフレーズだけを英訳し、マッチしなかった部分はプロンプトに含めない。
NOTES_MAP: dict[str, str] = {
    "柔らかい表情で": "soft, gentle expression",
    "笑顔で": "with a smile",
    "真剣な表情で": "serious expression",
    "逆光に注意": "backlit, handle exposure carefully",
    "順光": "front-lit",
    "逆光": "backlit",
}


def _translate_by_keywords(text: str, keyword_map: dict[str, str]) -> str:
    """text中に含まれる既知キーワードをmapの並び順に英訳し、カンマ結合して返す。

    マッチした部分文字列は remaining から取り除いてから次のキーを検索することで、
    複合語（例: "逆光に注意"）とその部分文字列（例: "逆光"）が二重にマッチして
    翻訳語が重複する（例: "backlit" が2回出力される）のを防ぐ。
    """
    matched: list[str] = []
    remaining = text
    for jp, en in keyword_map.items():
        if jp in remaining:
            matched.append(en)
            remaining = remaining.replace(jp, "")
    return ", ".join(matched)


def translate_location(location: str) -> str:
    """例: "室内スタジオ（窓セット）" → "indoor studio, window set" """
    return _translate_by_keywords(location, LOCATION_MAP)


def translate_equipment(equipment: str) -> str:
    """例: "85mm F1.4、暖色・ゴールデンアワー調"
    → "85mm portrait lens, shallow depth of field F1.4, warm amber lighting, golden hour quality light"
    """
    return _translate_by_keywords(equipment, EQUIPMENT_MAP)


def translate_notes(notes: str) -> str:
    """例: "柔らかい表情で、逆光に注意" → "soft, gentle expression, backlit, handle exposure carefully" """
    return _translate_by_keywords(notes, NOTES_MAP)


def generate_flux_prompt(shot: dict, character_prompt: str = "", style: str = "") -> str:
    """撮影リストのshot dict（実際のShootingListShotの9フィールド）からFLUXプロンプトを組み立てる。

    構成: character_prompt（あれば） → category起点のフレーミング →
    location/equipment/notesの英訳 → 汎用の品質タグ → style（あれば）。
    title（shotの日本語見出し）はFLUXに渡す英語プロンプトには含めない
    （翻訳されない日本語がそのまま混ざり、誤った画像生成の原因になるため）。
    """
    parts: list[str] = []

    if character_prompt:
        parts.append(character_prompt)

    framing = CATEGORY_FRAMING.get(shot.get("category", "other"), "cinematic shot")
    parts.append(framing)

    if shot.get("location"):
        location_en = translate_location(shot["location"])
        if location_en:
            parts.append(location_en)

    if shot.get("equipment"):
        equipment_en = translate_equipment(shot["equipment"])
        if equipment_en:
            parts.append(equipment_en)

    if shot.get("notes"):
        notes_en = translate_notes(shot["notes"])
        if notes_en:
            parts.append(f"Direction: {notes_en}")

    parts.append("cinematic, highly detailed, professional photography")

    if style:
        parts.append(style)

    return "\n".join(parts)
