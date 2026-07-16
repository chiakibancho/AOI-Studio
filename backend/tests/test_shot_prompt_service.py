from unittest.mock import AsyncMock

from app.core.config import settings
from app.services import together_ai_service
from app.services.shot_prompt_service import generate_flux_prompt

from tests.test_shooting_list_generation import _generate_and_approve_shooting_list

# 1x1 の透明PNG（テスト用のダミー生成結果）
FAKE_PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010802000000907753"
    "de0000000c4944415478da63640000060005fed88b0e0000000049454e44ae42"
    "6082"
)


def _base_shot(**overrides) -> dict:
    shot = {
        "cut_number": 1,
        "scene_number": 1,
        "shot_type": "",
        "subject": "",
        "location": "",
        "equipment": "",
        "notes": "",
    }
    shot.update(overrides)
    return shot


# ---------------------------------------------------------------------------
# shot_type マッピング
# ---------------------------------------------------------------------------


def test_close_up_shot_type_is_translated():
    prompt = generate_flux_prompt(_base_shot(shot_type="クローズアップ", subject="主人公"))
    assert "extreme close-up, face only of 主人公" in prompt


def test_medium_shot_type_is_translated():
    prompt = generate_flux_prompt(_base_shot(shot_type="ミディアムショット"))
    assert "medium shot, upper body" in prompt


def test_medium_close_up_shot_type_is_translated():
    prompt = generate_flux_prompt(_base_shot(shot_type="ミディアムクローズアップ"))
    assert "medium close-up, face and upper chest" in prompt


def test_unknown_shot_type_passes_through_unchanged():
    prompt = generate_flux_prompt(_base_shot(shot_type="ドローンショット"))
    assert "ドローンショット" in prompt


# ---------------------------------------------------------------------------
# location 変換
# ---------------------------------------------------------------------------


def test_indoor_studio_window_set_location():
    prompt = generate_flux_prompt(_base_shot(location="室内スタジオ（窓セット）"))
    assert "indoor studio, window set" in prompt


def test_high_rise_night_cityscape_location():
    prompt = generate_flux_prompt(_base_shot(location="高層階の夜景"))
    assert "high-rise night cityscape background" in prompt


# ---------------------------------------------------------------------------
# equipment 変換
# ---------------------------------------------------------------------------


def test_85mm_f14_equipment_is_translated():
    prompt = generate_flux_prompt(_base_shot(equipment="85mm F1.4"))
    assert "85mm portrait lens, shallow depth of field F1.4" in prompt


def test_cold_low_intensity_lighting_equipment():
    prompt = generate_flux_prompt(_base_shot(equipment="冷色・低輝度"))
    assert "cold low-intensity lighting, blue-toned shadows" in prompt


def test_warm_golden_hour_lighting_equipment():
    prompt = generate_flux_prompt(_base_shot(equipment="暖色・ゴールデンアワー調"))
    assert "warm golden hour window light, 3200-3800K" in prompt


# ---------------------------------------------------------------------------
# character_prompt / style / notes の組み立て
# ---------------------------------------------------------------------------


def test_character_prompt_is_prepended_when_present():
    prompt = generate_flux_prompt(_base_shot(subject="A"), character_prompt="A consistent character bible.")
    assert prompt.startswith("A consistent character bible.")


def test_character_prompt_omitted_when_empty():
    prompt = generate_flux_prompt(_base_shot(subject="A"), character_prompt="")
    assert "character bible" not in prompt


def test_style_is_appended_at_the_end():
    prompt = generate_flux_prompt(
        _base_shot(subject="A"), style="modern anime style, clean line art, vibrant colors"
    )
    assert prompt.endswith("modern anime style, clean line art, vibrant colors")


def test_notes_are_included():
    prompt = generate_flux_prompt(_base_shot(notes="逆光に注意、柔らかい表情で"))
    assert "逆光に注意、柔らかい表情で" in prompt


def test_full_shot_combines_all_segments_in_order():
    shot = _base_shot(
        shot_type="クローズアップ",
        subject="主人公",
        location="室内スタジオ（窓セット）",
        equipment="85mm F1.4",
        notes="柔らかい表情で",
    )
    prompt = generate_flux_prompt(
        shot, character_prompt="Character bible text.", style="cinematic realism"
    )
    lines = prompt.split("\n")
    assert lines[0] == "Character bible text."
    assert lines[1] == "extreme close-up, face only of 主人公"
    assert lines[2] == "Background: indoor studio, window set"
    assert lines[3] == "85mm portrait lens, shallow depth of field F1.4"
    assert lines[4] == "柔らかい表情で"
    assert lines[5] == "cinematic realism"


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

    # 承認済みキャラクターが無い場合は character_prompt 抜きで、ショット情報＋styleが渡っていること
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
