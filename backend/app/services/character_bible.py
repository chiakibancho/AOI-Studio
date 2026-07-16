import re

_PLACEHOLDER_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")

_CHARACTER_BIBLE_V1 = """\
You are generating a character reference sheet for use as a consistent visual identity \
across multiple illustrated shots. Follow every instruction below precisely.

## Character Definition

A person with a {{FACE_SHAPE}} face shape, {{EYE_COLOR}} eyes, and {{HAIR_STYLE}} hair. \
Build: {{BODY_TYPE}}. Wearing: {{TOP}}, primarily in {{PRIMARY_COLOR}}. \
Overall art style: {{ART_STYLE}}.

## Consistency Instructions

This character must look identical across every panel: same face shape, same eye color, \
same hairstyle, same build, same outfit and color palette, same art style. Do not introduce \
variation in these attributes between panels. Treat this description as a fixed identity, \
not a suggestion.

## Model Sheet Instructions

Generate a character reference sheet (model sheet / turnaround) showing the character from \
6 angles: front view, 3/4 front view, side view, back view, 3/4 back view, and a close-up \
portrait. Neutral standing pose (T-pose or A-pose), arms relaxed, no dynamic action. Plain \
white background, even studio lighting, no shadows on the background. Consistent scale and \
eye-line across all views. Clean line art, character sheet layout, no text or labels.
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
