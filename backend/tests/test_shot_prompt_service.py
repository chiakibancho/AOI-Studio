import re
from unittest.mock import AsyncMock

from app.core.config import settings
from app.services import together_ai_service
from app.services.shot_prompt_service import generate_flux_prompt

from tests.test_shooting_list_generation import _generate_and_approve_shooting_list

_JAPANESE_CHAR_RE = re.compile(r"[぀-ゟ゠-ヿ一-鿿]")

# 1x1 の透明PNG（テスト用のダミー生成結果）
FAKE_PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010802000000907753"
    "de0000000c4944415478da63640000060005fed88b0e0000000049454e44ae42"
    "6082"
)

# 実DBから取得した実際のShootingListShotと同じ構造（9フィールド）
REAL_SHOT = {
    "cut_number": 1,
    "scene_number": 1,
    "category": "people",
    "title": "主人公の紹介ショット",
    "location": "室内スタジオ（窓セット）",
    "equipment": "85mm F1.4、暖色・ゴールデンアワー調",
    "talent_props": "出演者A",
    "notes": "柔らかい表情で、逆光に注意",
    "completed": False,
}


# ---------------------------------------------------------------------------
# generate_flux_prompt: 実データ構造でのユニットテスト
# ---------------------------------------------------------------------------


def test_real_shot_maps_category_to_framing():
    prompt = generate_flux_prompt(REAL_SHOT)
    assert "medium shot" in prompt


def test_real_shot_translates_location():
    prompt = generate_flux_prompt(REAL_SHOT)
    assert "indoor studio" in prompt
    assert "window set" in prompt


def test_real_shot_translates_equipment():
    prompt = generate_flux_prompt(REAL_SHOT)
    assert "85mm portrait lens" in prompt
    assert "warm amber lighting" in prompt
    assert "golden hour quality light" in prompt


def test_real_shot_has_no_leftover_japanese():
    prompt = generate_flux_prompt(REAL_SHOT)
    assert "逆光" not in prompt
    assert "柔らかい" not in prompt
    assert "暖色" not in prompt
    assert "窓セット" not in prompt


def test_real_shot_prompt_contains_no_japanese_characters_at_all():
    """titleを含め、日本語（ひらがな/カタカナ/漢字）が一文字も残っていないこと。"""
    prompt = generate_flux_prompt(REAL_SHOT)
    assert not _JAPANESE_CHAR_RE.search(prompt), f"日本語が残っています: {prompt!r}"


def test_real_shot_excludes_title():
    """titleは翻訳されない日本語のためFLUXプロンプトに含めない。"""
    prompt = generate_flux_prompt(REAL_SHOT)
    assert "Scene:" not in prompt
    assert "主人公の紹介ショット" not in prompt


def test_real_shot_notes_translation_has_no_duplicate_backlit():
    """"逆光に注意"と部分文字列"逆光"の二重マッチでbacklitが重複しないこと。"""
    prompt = generate_flux_prompt(REAL_SHOT)
    assert prompt.count("backlit") == 1


# ---------------------------------------------------------------------------
# category マッピング（shot_typeが存在しないため category で代替）
# ---------------------------------------------------------------------------


def test_category_people():
    prompt = generate_flux_prompt({**REAL_SHOT, "category": "people"})
    assert "medium shot, person as main subject" in prompt


def test_category_exterior():
    prompt = generate_flux_prompt({**REAL_SHOT, "category": "exterior"})
    assert "wide establishing shot, outdoor environment" in prompt


def test_category_product():
    prompt = generate_flux_prompt({**REAL_SHOT, "category": "product"})
    assert "close-up, product detail shot" in prompt


def test_category_broll():
    prompt = generate_flux_prompt({**REAL_SHOT, "category": "broll"})
    assert "cinematic b-roll, atmospheric shot" in prompt


def test_category_other():
    prompt = generate_flux_prompt({**REAL_SHOT, "category": "other"})
    assert "cinematic shot" in prompt


def test_unknown_category_falls_back_to_cinematic_shot():
    prompt = generate_flux_prompt({**REAL_SHOT, "category": "unknown-value"})
    assert "cinematic shot" in prompt


# ---------------------------------------------------------------------------
# character_prompt / style の組み立て
# ---------------------------------------------------------------------------


def test_character_prompt_is_prepended_when_present():
    prompt = generate_flux_prompt(REAL_SHOT, character_prompt="A consistent character bible.")
    assert prompt.startswith("A consistent character bible.")


def test_character_prompt_omitted_when_empty():
    prompt = generate_flux_prompt(REAL_SHOT, character_prompt="")
    assert "character bible" not in prompt


def test_style_is_appended_at_the_end():
    prompt = generate_flux_prompt(REAL_SHOT, style="modern anime style, clean line art")
    assert prompt.rstrip().endswith("modern anime style, clean line art")


def test_quality_tags_always_included():
    prompt = generate_flux_prompt(REAL_SHOT)
    assert "cinematic, highly detailed, professional photography" in prompt


# ---------------------------------------------------------------------------
# generate-image エンドポイント
# ---------------------------------------------------------------------------


async def test_generate_shot_image_returns_503_without_together_api_key(
    auth_client, project_id, monkeypatch
):
    shooting_list = await _generate_and_approve_shooting_list(auth_client, project_id, monkeypatch)
    cut_number = shooting_list["shots"][0]["cut_number"]
    monkeypatch.setattr(settings, "TOGETHER_API_KEY", "")

    resp = await auth_client.post(
        f"/api/v1/projects/{project_id}/shooting-list/shots/{cut_number}/generate-image",
        json={},
    )
    assert resp.status_code == 503


async def test_generate_shot_image_404_unknown_cut_number(auth_client, project_id, monkeypatch):
    await _generate_and_approve_shooting_list(auth_client, project_id, monkeypatch)
    monkeypatch.setattr(settings, "TOGETHER_API_KEY", "fake-key")

    resp = await auth_client.post(
        f"/api/v1/projects/{project_id}/shooting-list/shots/999/generate-image",
        json={},
    )
    assert resp.status_code == 404


async def test_generate_shot_image_completes_and_serves_image(auth_client, project_id, monkeypatch):
    shooting_list = await _generate_and_approve_shooting_list(auth_client, project_id, monkeypatch)
    cut_number = shooting_list["shots"][0]["cut_number"]

    monkeypatch.setattr(settings, "TOGETHER_API_KEY", "fake-key")
    mock_generate = AsyncMock(return_value=FAKE_PNG_BYTES)
    monkeypatch.setattr(together_ai_service, "generate_character_sheet_image", mock_generate)

    resp = await auth_client.post(
        f"/api/v1/projects/{project_id}/shooting-list/shots/{cut_number}/generate-image",
        json={"style": "modern anime style, clean line art, vibrant colors"},
    )
    assert resp.status_code == 202
    assert resp.json()["status"] == "generating"

    resp = await auth_client.get(
        f"/api/v1/projects/{project_id}/shooting-list/shots/{cut_number}/image-status"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "generated"
    assert body["image_path"] == f"shot_images/{body['id']}.png"
    assert body["error_message"] is None

    mock_generate.assert_awaited_once()
    prompt_arg = mock_generate.await_args.args[0]
    assert "modern anime style, clean line art, vibrant colors" in prompt_arg

    resp = await auth_client.get(
        f"/api/v1/projects/{project_id}/shooting-list/shots/{cut_number}/image"
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.content == FAKE_PNG_BYTES


async def test_generate_shot_image_includes_approved_character_prompt(
    auth_client, project_id, monkeypatch
):
    shooting_list = await _generate_and_approve_shooting_list(auth_client, project_id, monkeypatch)
    cut_number = shooting_list["shots"][0]["cut_number"]

    monkeypatch.setattr(settings, "TOGETHER_API_KEY", "fake-key")
    mock_generate = AsyncMock(return_value=FAKE_PNG_BYTES)
    monkeypatch.setattr(together_ai_service, "generate_character_sheet_image", mock_generate)

    char_resp = await auth_client.post(
        f"/api/v1/projects/{project_id}/characters",
        json={"name": "Hero", "prompt": "A consistent character bible description."},
    )
    character_id = char_resp.json()["id"]
    await auth_client.post(f"/api/v1/characters/{character_id}/generate")
    await auth_client.post(f"/api/v1/characters/{character_id}/approve")

    resp = await auth_client.post(
        f"/api/v1/projects/{project_id}/shooting-list/shots/{cut_number}/generate-image",
        json={},
    )
    assert resp.status_code == 202

    await auth_client.get(
        f"/api/v1/projects/{project_id}/shooting-list/shots/{cut_number}/image-status"
    )

    prompt_arg = mock_generate.await_args.args[0]
    assert "A consistent character bible description." in prompt_arg


async def test_generate_shot_image_returns_409_while_generating(auth_client, project_id, monkeypatch):
    import asyncio

    shooting_list = await _generate_and_approve_shooting_list(auth_client, project_id, monkeypatch)
    cut_number = shooting_list["shots"][0]["cut_number"]
    monkeypatch.setattr(settings, "TOGETHER_API_KEY", "fake-key")

    started = asyncio.Event()
    release = asyncio.Event()

    async def slow_generate(prompt):
        started.set()
        await release.wait()
        return FAKE_PNG_BYTES

    monkeypatch.setattr(together_ai_service, "generate_character_sheet_image", slow_generate)

    task = asyncio.create_task(
        auth_client.post(
            f"/api/v1/projects/{project_id}/shooting-list/shots/{cut_number}/generate-image",
            json={},
        )
    )
    await started.wait()

    resp = await auth_client.post(
        f"/api/v1/projects/{project_id}/shooting-list/shots/{cut_number}/generate-image",
        json={},
    )
    assert resp.status_code == 409

    release.set()
    first_resp = await task
    assert first_resp.status_code == 202
