import asyncio
from unittest.mock import AsyncMock

from app.core.config import settings
from app.services import character_bible, together_ai_service
from app.services.together_ai_service import ImageGenerationError

# 1x1 の透明PNG（テスト用のダミー生成結果）
FAKE_PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010802000000907753"
    "de0000000c4944415478da63640000060005fed88b0e0000000049454e44ae42"
    "6082"
)


def _fake_variables() -> dict[str, str]:
    template = character_bible.CHARACTER_BIBLE_TEMPLATES[character_bible.CURRENT_TEMPLATE_VERSION]
    return {key: f"test-{key.lower()}" for key in character_bible.extract_template_variables(template)}


async def _create_character(auth_client, project_id, name="Test Character", variables=None):
    resp = await auth_client.post(
        f"/api/v1/projects/{project_id}/characters",
        json={"name": name, "variables": variables or _fake_variables()},
    )
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# character_bible unit tests
# ---------------------------------------------------------------------------


def test_extract_template_variables_returns_unique_ordered_names():
    template = "A {{FOO}} and a {{BAR}} and another {{FOO}}."
    assert character_bible.extract_template_variables(template) == ["FOO", "BAR"]


def test_render_template_substitutes_all_placeholders():
    template = "{{FOO}} likes {{BAR}}."
    rendered = character_bible.render_template(template, {"FOO": "Alice", "BAR": "tea"})
    assert rendered == "Alice likes tea."


def test_render_template_raises_on_missing_variable():
    template = "{{FOO}} likes {{BAR}}."
    try:
        character_bible.render_template(template, {"FOO": "Alice"})
        assert False, "expected ValueError"
    except ValueError as e:
        assert "BAR" in str(e)


# ---------------------------------------------------------------------------
# template-variables endpoint
# ---------------------------------------------------------------------------


async def test_template_variables_endpoint(auth_client):
    resp = await auth_client.get("/api/v1/characters/template-variables")
    assert resp.status_code == 200
    body = resp.json()
    assert body["template_version"] == "v1"
    assert set(body["variables"]) == set(
        character_bible.extract_template_variables(
            character_bible.CHARACTER_BIBLE_TEMPLATES["v1"]
        )
    )


# ---------------------------------------------------------------------------
# create / list
# ---------------------------------------------------------------------------


async def test_create_character_success(auth_client, project_id):
    character = await _create_character(auth_client, project_id)
    assert character["name"] == "Test Character"
    assert character["status"] == "draft"
    assert character["template_version"] == "v1"
    assert character["sheet_image_path"] is None


async def test_create_character_missing_variable_returns_422(auth_client, project_id):
    variables = _fake_variables()
    variables.pop(next(iter(variables)))
    resp = await auth_client.post(
        f"/api/v1/projects/{project_id}/characters",
        json={"name": "Missing Var", "variables": variables},
    )
    assert resp.status_code == 422


async def test_create_character_extra_variable_returns_422(auth_client, project_id):
    variables = _fake_variables()
    variables["UNKNOWN_FIELD"] = "x"
    resp = await auth_client.post(
        f"/api/v1/projects/{project_id}/characters",
        json={"name": "Extra Var", "variables": variables},
    )
    assert resp.status_code == 422


async def test_list_characters_returns_created_characters(auth_client, project_id):
    await _create_character(auth_client, project_id, name="A")
    await _create_character(auth_client, project_id, name="B")

    resp = await auth_client.get(f"/api/v1/projects/{project_id}/characters")
    assert resp.status_code == 200
    names = [c["name"] for c in resp.json()]
    assert names == ["A", "B"]


# ---------------------------------------------------------------------------
# generate
# ---------------------------------------------------------------------------


async def test_generate_returns_503_without_together_api_key(auth_client, project_id, monkeypatch):
    character = await _create_character(auth_client, project_id)
    monkeypatch.setattr(settings, "TOGETHER_API_KEY", "")

    resp = await auth_client.post(f"/api/v1/characters/{character['id']}/generate")
    assert resp.status_code == 503


async def test_generate_completes_and_saves_sheet_image(auth_client, project_id, monkeypatch):
    monkeypatch.setattr(settings, "TOGETHER_API_KEY", "fake-key")
    monkeypatch.setattr(
        together_ai_service,
        "generate_character_sheet_image",
        AsyncMock(return_value=FAKE_PNG_BYTES),
    )
    character = await _create_character(auth_client, project_id)

    resp = await auth_client.post(f"/api/v1/characters/{character['id']}/generate")
    assert resp.status_code == 202
    assert resp.json()["status"] == "generating"

    resp = await auth_client.get(f"/api/v1/characters/{character['id']}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "generated"
    assert body["sheet_image_path"] == f"character_sheets/{character['id']}.png"
    assert body["error_message"] is None

    resp = await auth_client.get(f"/api/v1/characters/{character['id']}/sheet-image")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.content == FAKE_PNG_BYTES


async def test_generate_failure_marks_failed(auth_client, project_id, monkeypatch):
    monkeypatch.setattr(settings, "TOGETHER_API_KEY", "fake-key")

    async def boom(prompt):
        raise ImageGenerationError("Together AI エラー: simulated 500")

    monkeypatch.setattr(together_ai_service, "generate_character_sheet_image", boom)
    character = await _create_character(auth_client, project_id)

    await auth_client.post(f"/api/v1/characters/{character['id']}/generate")

    resp = await auth_client.get(f"/api/v1/characters/{character['id']}")
    body = resp.json()
    assert body["status"] == "failed"
    assert "simulated 500" in body["error_message"]


async def test_generate_returns_409_while_generating(auth_client, project_id, monkeypatch):
    monkeypatch.setattr(settings, "TOGETHER_API_KEY", "fake-key")

    started = asyncio.Event()
    release = asyncio.Event()

    async def slow_generate(prompt):
        started.set()
        await release.wait()
        return FAKE_PNG_BYTES

    monkeypatch.setattr(together_ai_service, "generate_character_sheet_image", slow_generate)
    character = await _create_character(auth_client, project_id)

    task = asyncio.create_task(
        auth_client.post(f"/api/v1/characters/{character['id']}/generate")
    )
    await started.wait()

    resp = await auth_client.post(f"/api/v1/characters/{character['id']}/generate")
    assert resp.status_code == 409

    release.set()
    first_resp = await task
    assert first_resp.status_code == 202


async def test_generate_rejected_after_approval(auth_client, project_id, monkeypatch):
    monkeypatch.setattr(settings, "TOGETHER_API_KEY", "fake-key")
    monkeypatch.setattr(
        together_ai_service,
        "generate_character_sheet_image",
        AsyncMock(return_value=FAKE_PNG_BYTES),
    )
    character = await _create_character(auth_client, project_id)
    await auth_client.post(f"/api/v1/characters/{character['id']}/generate")
    await auth_client.post(f"/api/v1/characters/{character['id']}/approve")

    resp = await auth_client.post(f"/api/v1/characters/{character['id']}/generate")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# approve
# ---------------------------------------------------------------------------


async def test_approve_rejected_before_generation(auth_client, project_id):
    character = await _create_character(auth_client, project_id)

    resp = await auth_client.post(f"/api/v1/characters/{character['id']}/approve")
    assert resp.status_code == 400


async def test_approve_succeeds_after_generation(auth_client, project_id, monkeypatch):
    monkeypatch.setattr(settings, "TOGETHER_API_KEY", "fake-key")
    monkeypatch.setattr(
        together_ai_service,
        "generate_character_sheet_image",
        AsyncMock(return_value=FAKE_PNG_BYTES),
    )
    character = await _create_character(auth_client, project_id)
    await auth_client.post(f"/api/v1/characters/{character['id']}/generate")

    resp = await auth_client.post(f"/api/v1/characters/{character['id']}/approve")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "approved"
    assert body["approved_at"] is not None


# ---------------------------------------------------------------------------
# ownership
# ---------------------------------------------------------------------------


async def test_character_not_visible_to_other_user(client, auth_client, project_id):
    character = await _create_character(auth_client, project_id)

    resp = await client.post(
        "/api/v1/auth/signup",
        json={"email": "other-user@example.com", "password": "testpass123", "name": "Other"},
    )
    other_token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {other_token}"

    resp = await client.get(f"/api/v1/characters/{character['id']}")
    assert resp.status_code == 404
