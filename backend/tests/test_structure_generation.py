import asyncio
from unittest.mock import AsyncMock

from app.services import ai_service

FAKE_AI_RESULT = {
    "options": [
        {
            "scenes": [
                {
                    "number": 1,
                    "title": "Opening",
                    "duration_sec": 10,
                    "description": "desc",
                    "shot_type": "B-roll",
                    "mood": "calm",
                    "notes": "",
                }
            ],
            "total_duration_sec": 10,
            "rationale": "because",
        },
        {
            "scenes": [
                {
                    "number": 1,
                    "title": "Problem",
                    "duration_sec": 12,
                    "description": "desc-2",
                    "shot_type": "Interview",
                    "mood": "serious",
                    "notes": "",
                }
            ],
            "total_duration_sec": 12,
            "rationale": "because-2",
        },
        {
            "scenes": [
                {
                    "number": 1,
                    "title": "Montage",
                    "duration_sec": 14,
                    "description": "desc-3",
                    "shot_type": "Montage",
                    "mood": "energetic",
                    "notes": "",
                }
            ],
            "total_duration_sec": 14,
            "rationale": "because-3",
        },
    ]
}


async def test_generate_returns_pending_then_completes(auth_client, project_id, monkeypatch):
    monkeypatch.setattr(
        ai_service, "generate_structure", AsyncMock(return_value=FAKE_AI_RESULT)
    )

    resp = await auth_client.post(f"/api/v1/projects/{project_id}/structure/generate")
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "pending"
    assert body["scenes"] == []

    resp = await auth_client.get(f"/api/v1/projects/{project_id}/structure")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "completed"
    assert body["scenes"][0]["title"] == "Opening"
    assert body["total_duration_sec"] == 10
    assert body["error_message"] is None

    resp = await auth_client.get(f"/api/v1/projects/{project_id}")
    assert resp.json()["status"] == "structure"


async def test_generate_returns_three_options(auth_client, project_id, monkeypatch):
    monkeypatch.setattr(
        ai_service, "generate_structure", AsyncMock(return_value=FAKE_AI_RESULT)
    )
    await auth_client.post(f"/api/v1/projects/{project_id}/structure/generate")

    resp = await auth_client.get(f"/api/v1/projects/{project_id}/structure")
    body = resp.json()
    assert len(body["options"]) == 3
    assert body["options"][0]["scenes"][0]["title"] == "Opening"
    assert body["options"][1]["scenes"][0]["title"] == "Problem"
    assert body["options"][2]["scenes"][0]["title"] == "Montage"
    assert body["selected_option_index"] is None


async def test_generate_api_failure_marks_failed(auth_client, project_id, monkeypatch):
    async def boom(project, spec):
        raise RuntimeError("Claude API エラー: simulated 401")

    monkeypatch.setattr(ai_service, "generate_structure", boom)

    resp = await auth_client.post(f"/api/v1/projects/{project_id}/structure/generate")
    assert resp.status_code == 202

    resp = await auth_client.get(f"/api/v1/projects/{project_id}/structure")
    body = resp.json()
    assert body["status"] == "failed"
    assert "simulated 401" in body["error_message"]
    assert body["scenes"] == []


async def test_generate_malformed_scenes_marks_failed(auth_client, project_id, monkeypatch):
    """AIが返したいずれかの案のscenesの形が壊れている場合、GET /structureの500ではなくfailedに落ちる。"""
    bad_result = {
        "options": [
            {
                "scenes": [{"number": 1, "title": "Opening"}],  # 必須フィールド欠落
                "total_duration_sec": 10,
                "rationale": "because",
            },
            FAKE_AI_RESULT["options"][1],
            FAKE_AI_RESULT["options"][2],
        ]
    }
    monkeypatch.setattr(
        ai_service, "generate_structure", AsyncMock(return_value=bad_result)
    )

    resp = await auth_client.post(f"/api/v1/projects/{project_id}/structure/generate")
    assert resp.status_code == 202

    resp = await auth_client.get(f"/api/v1/projects/{project_id}/structure")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "failed"
    assert body["error_message"]


async def test_generate_wrong_option_count_marks_failed(auth_client, project_id, monkeypatch):
    bad_result = {"options": FAKE_AI_RESULT["options"][:2]}  # 2件しかない
    monkeypatch.setattr(
        ai_service, "generate_structure", AsyncMock(return_value=bad_result)
    )

    resp = await auth_client.post(f"/api/v1/projects/{project_id}/structure/generate")
    assert resp.status_code == 202

    resp = await auth_client.get(f"/api/v1/projects/{project_id}/structure")
    body = resp.json()
    assert body["status"] == "failed"
    assert "3" in body["error_message"]


async def test_generate_missing_options_key_marks_failed(auth_client, project_id, monkeypatch):
    # 旧形式（単一案）のレスポンスを返してしまった場合も failed に落ちる
    legacy_result = {
        "scenes": FAKE_AI_RESULT["options"][0]["scenes"],
        "total_duration_sec": 10,
        "rationale": "because",
    }
    monkeypatch.setattr(
        ai_service, "generate_structure", AsyncMock(return_value=legacy_result)
    )

    resp = await auth_client.post(f"/api/v1/projects/{project_id}/structure/generate")
    assert resp.status_code == 202

    resp = await auth_client.get(f"/api/v1/projects/{project_id}/structure")
    body = resp.json()
    assert body["status"] == "failed"
    assert "options" in body["error_message"]


async def test_approve_rejects_non_completed(auth_client, project_id, monkeypatch):
    async def boom(project, spec):
        raise RuntimeError("boom")

    monkeypatch.setattr(ai_service, "generate_structure", boom)
    await auth_client.post(f"/api/v1/projects/{project_id}/structure/generate")

    resp = await auth_client.post(f"/api/v1/projects/{project_id}/structure/approve")
    assert resp.status_code == 400


async def test_approve_succeeds_when_completed(auth_client, project_id, monkeypatch):
    monkeypatch.setattr(
        ai_service, "generate_structure", AsyncMock(return_value=FAKE_AI_RESULT)
    )
    await auth_client.post(f"/api/v1/projects/{project_id}/structure/generate")

    resp = await auth_client.post(f"/api/v1/projects/{project_id}/structure/approve")
    assert resp.status_code == 200
    body = resp.json()
    assert body["approved_at"] is not None
    assert body["scenes"][0]["title"] == "Opening"
    assert body["selected_option_index"] == 0

    resp = await auth_client.get(f"/api/v1/projects/{project_id}")
    assert resp.json()["status"] == "storyboard"


async def test_approve_with_option_index_selects_that_option(auth_client, project_id, monkeypatch):
    monkeypatch.setattr(
        ai_service, "generate_structure", AsyncMock(return_value=FAKE_AI_RESULT)
    )
    await auth_client.post(f"/api/v1/projects/{project_id}/structure/generate")

    resp = await auth_client.post(
        f"/api/v1/projects/{project_id}/structure/approve",
        params={"option_index": 2},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["scenes"][0]["title"] == "Montage"
    assert body["total_duration_sec"] == 14
    assert body["rationale"] == "because-3"
    assert body["selected_option_index"] == 2


async def test_approve_rejects_invalid_option_index(auth_client, project_id, monkeypatch):
    monkeypatch.setattr(
        ai_service, "generate_structure", AsyncMock(return_value=FAKE_AI_RESULT)
    )
    await auth_client.post(f"/api/v1/projects/{project_id}/structure/generate")

    resp = await auth_client.post(
        f"/api/v1/projects/{project_id}/structure/approve",
        params={"option_index": 5},
    )
    assert resp.status_code == 422


async def test_generate_increments_version(auth_client, project_id, monkeypatch):
    monkeypatch.setattr(
        ai_service, "generate_structure", AsyncMock(return_value=FAKE_AI_RESULT)
    )

    resp = await auth_client.post(f"/api/v1/projects/{project_id}/structure/generate")
    assert resp.json()["version"] == 1

    resp = await auth_client.post(f"/api/v1/projects/{project_id}/structure/generate")
    assert resp.json()["version"] == 2


async def test_generate_returns_409_while_pending(auth_client, project_id, monkeypatch):
    started = asyncio.Event()
    release = asyncio.Event()

    async def slow_generate(project, spec):
        started.set()
        await release.wait()
        return FAKE_AI_RESULT

    monkeypatch.setattr(ai_service, "generate_structure", slow_generate)

    task = asyncio.create_task(
        auth_client.post(f"/api/v1/projects/{project_id}/structure/generate")
    )
    await started.wait()

    resp = await auth_client.post(
        f"/api/v1/projects/{project_id}/structure/generate"
    )
    assert resp.status_code == 409

    release.set()
    first_resp = await task
    assert first_resp.status_code == 202
