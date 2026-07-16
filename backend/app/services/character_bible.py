import re

_PLACEHOLDER_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")

_CHARACTER_BIBLE_V1 = """
# ============================
# FLUX CHARACTER BIBLE v1
# ============================

## CHARACTER DEFINITION
A single character with the following fixed appearance:

Face: {{FACE_SHAPE}}, {{EYE_SHAPE}}, {{EYE_COLOR}} eyes, {{EYEBROWS}}, {{NOSE}}, {{MOUTH}}, {{SKIN}} skin tone.
Hair: {{HAIR_STYLE}}, {{HAIR_LENGTH}}, {{HAIR_COLOR}}, {{BANGS}}.
Body: {{HEIGHT}}, {{BODY_TYPE}} build, {{SHOULDER_WIDTH}} shoulders, {{HAND_SIZE}} hands, {{LEG_LENGTH}} legs.
Outfit: {{TOP}}, {{BOTTOM}}, {{SHOES}}, {{ACCESSORIES}}.
Color palette: primary {{PRIMARY_COLOR}}, secondary {{SECONDARY_COLOR}}, accent {{ACCENT_COLOR}}.
Art style: {{ART_STYLE}}.

## CONSISTENCY RULES
The exact same character in every panel.
Identical facial proportions.
Identical hairstyle and hairline.
Identical clothing design and accessory placement.
Identical body proportions and color palette.
Same age, same ethnicity, same eye shape, same skin tone.
No redesign. No variation. Maintain character identity.

Always preserve:
facial structure, eye distance, eye size, nose shape, mouth shape, jaw line,
hairstyle, hairline, body proportions, clothing design, accessory placement, color palette.
Never change character identity.

## MODEL SHEET
Character turnaround reference sheet.
Front view, left side view, back view, right side view, three-quarter view.
Neutral pose. Arms relaxed. Legs shoulder width apart.
Orthographic layout. Clean white background.
Concept art. Character sheet. Model sheet.
Ultra detailed. Professional animation reference.
"""

CHARACTER_BIBLE_TEMPLATES: dict[str, str] = {
    "v1": _CHARACTER_BIBLE_V1,
}

CURRENT_TEMPLATE_VERSION = "v1"


def extract_template_variables(template: str) -> list[str]:
    """テンプレート内の {{PLACEHOLDER}} を出現順・重複なしで抽出する。"""
    seen: dict[str, None] = {}
    for match in _PLACEHOLDER_RE.finditer(template):
        seen.setdefault(match.group(1), None)
    return list(seen.keys())


def render_template(template: str, variables: dict[str, str]) -> str:
    """テンプレートのプレースホルダーを variables で置換したプロンプト文字列を返す。"""
    rendered = template
    for key, value in variables.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)

    remaining = _PLACEHOLDER_RE.findall(rendered)
    if remaining:
        raise ValueError(f"未置換のプレースホルダーが残っています: {sorted(set(remaining))}")

    return rendered
