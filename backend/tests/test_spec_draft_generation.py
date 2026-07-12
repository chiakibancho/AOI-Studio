import asyncio
from unittest.mock import AsyncMock

from app.services import ai_service

FAKE_AI_RESULT = {
    "duration_sec": 60,
    "target_audience": "20代の求職者",
    "message": "働きやすさを伝えたい",
    "mood": "friendly",
    "style_notes": "オフィス風景を中心に",
    "reference_urls": [],
    "rationale": "because",
}


async def test_generate_returns_pending_then_completes(auth_client, project_id, monkeypatch):
    monkeypatch.setattr(
        ai_service, "analyze_spec", AsyncMock(return_value=FAKE_AI_RESULT)
    )

    resp = await auth_client.post(
        f"/api/v1/projects/{project_id}/spec-draft/generate",
        json={"raw_input": "採用動画を作りたい"},
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "pending"
    assert body["raw_input"] == "採用動画を作りたい"

    resp = await auth_client.get(f"/api/v1/projects/{project_id}/spec-draft")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "completed"
    assert body["message"] == "働きやすさを伝えたい"
    assert body["mood"] == "friendly"
    assert body["rationale"] == "because"
    assert body["error_message"] is None

    resp = await auth_client.get(f"/api/v1/projects/{project_id}")
    assert resp.json()["status"] == "setup"


async def test_generate_api_failure_marks_failed(auth_client, project_id, monkeypatch):
    async def boom(project, raw_input):
        raise RuntimeError("Claude API エラー: simulated 401")

    monkeypatch.setattr(ai_service, "analyze_spec", boom)

    resp = await auth_client.post(
        f"/api/v1/projects/{project_id}/spec-draft/generate",
        json={"raw_input": "採用動画を作りたい"},
    )
    assert resp.status_code == 202

    resp = await auth_client.get(f"/api/v1/projects/{project_id}/spec-draft")
    body = resp.json()
    assert body["status"] == "failed"
    assert "simulated 401" in body["error_message"]


async def test_generate_malformed_output_marks_failed(auth_client, project_id, monkeypatch):
    """AIが返した内容がVideoSpecCreateとして不正な場合、GET /spec-draftの500ではなくfailedに落ちる。"""
    bad_result = {
        "duration_sec": 99999,  # 範囲外
        "target_audience": "20代の求職者",
        "message": "働きやすさを伝えたい",
        "mood": "friendly",
        "rationale": "because",
    }
    monkeypatch.setattr(
        ai_service, "analyze_spec", AsyncMock(return_value=bad_result)
    )

    resp = await auth_client.post(
        f"/api/v1/projects/{project_id}/spec-draft/generate",
        json={"raw_input": "採用動画を作りたい"},
    )
    assert resp.status_code == 202

    resp = await auth_client.get(f"/api/v1/projects/{project_id}/spec-draft")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "failed"
    assert body["error_message"]


async def test_approve_rejects_non_completed(auth_client, project_id, monkeypatch):
    async def boom(project, raw_input):
        raise RuntimeError("boom")

    monkeypatch.setattr(ai_service, "analyze_spec", boom)
    await auth_client.post(
        f"/api/v1/projects/{project_id}/spec-draft/generate",
        json={"raw_input": "採用動画を作りたい"},
    )

    resp = await auth_client.post(f"/api/v1/projects/{project_id}/spec-draft/approve")
    assert resp.status_code == 400


async def test_approve_creates_video_spec_when_none_exists(auth_client, monkeypatch):
    # project_id フィクスチャは spec を PUT 済みなので使わず、素の project を作る
    resp = await auth_client.post(
        "/api/v1/projects", json={"title": "No Spec Project", "video_type": "brand"}
    )
    assert resp.status_code == 201
    pid = resp.json()["id"]

    monkeypatch.setattr(
        ai_service, "analyze_spec", AsyncMock(return_value=FAKE_AI_RESULT)
    )
    await auth_client.post(
        f"/api/v1/projects/{pid}/spec-draft/generate",
        json={"raw_input": "採用動画を作りたい"},
    )

    resp = await auth_client.post(f"/api/v1/projects/{pid}/spec-draft/approve")
    assert resp.status_code == 200
    body = resp.json()
    assert body["message"] == "働きやすさを伝えたい"
    assert body["mood"] == "friendly"

    resp = await auth_client.get(f"/api/v1/projects/{pid}/spec")
    assert resp.status_code == 200
    assert resp.json()["message"] == "働きやすさを伝えたい"


async def test_approve_updates_existing_video_spec(auth_client, project_id, monkeypatch):
    # project_id フィクスチャは duration_sec=30, mood="casual" の spec を PUT 済み
    monkeypatch.setattr(
        ai_service, "analyze_spec", AsyncMock(return_value=FAKE_AI_RESULT)
    )
    await auth_client.post(
        f"/api/v1/projects/{project_id}/spec-draft/generate",
        json={"raw_input": "採用動画を作りたい"},
    )

    resp = await auth_client.post(f"/api/v1/projects/{project_id}/spec-draft/approve")
    assert resp.status_code == 200
    body = resp.json()
    assert body["duration_sec"] == 60
    assert body["mood"] == "friendly"

    resp = await auth_client.get(f"/api/v1/projects/{project_id}/spec")
    body = resp.json()
    assert body["duration_sec"] == 60
    assert body["mood"] == "friendly"


async def test_approve_does_not_change_project_status(auth_client, project_id, monkeypatch):
    monkeypatch.setattr(
        ai_service, "analyze_spec", AsyncMock(return_value=FAKE_AI_RESULT)
    )
    await auth_client.post(
        f"/api/v1/projects/{project_id}/spec-draft/generate",
        json={"raw_input": "採用動画を作りたい"},
    )
    await auth_client.post(f"/api/v1/projects/{project_id}/spec-draft/approve")

    resp = await auth_client.get(f"/api/v1/projects/{project_id}")
    assert resp.json()["status"] == "setup"


async def test_generate_increments_version(auth_client, project_id, monkeypatch):
    monkeypatch.setattr(
        ai_service, "analyze_spec", AsyncMock(return_value=FAKE_AI_RESULT)
    )

    resp = await auth_client.post(
        f"/api/v1/projects/{project_id}/spec-draft/generate",
        json={"raw_input": "採用動画を作りたい"},
    )
    assert resp.json()["version"] == 1

    resp = await auth_client.post(
        f"/api/v1/projects/{project_id}/spec-draft/generate",
        json={"raw_input": "もう一度お願いします"},
    )
    assert resp.json()["version"] == 2


async def test_generate_returns_409_while_pending(auth_client, project_id, monkeypatch):
    started = asyncio.Event()
    release = asyncio.Event()

    async def slow_generate(project, raw_input):
        started.set()
        await release.wait()
        return FAKE_AI_RESULT

    monkeypatch.setattr(ai_service, "analyze_spec", slow_generate)

    task = asyncio.create_task(
        auth_client.post(
            f"/api/v1/projects/{project_id}/spec-draft/generate",
            json={"raw_input": "採用動画を作りたい"},
        )
    )
    await started.wait()

    resp = await auth_client.post(
        f"/api/v1/projects/{project_id}/spec-draft/generate",
        json={"raw_input": "もう一度お願いします"},
    )
    assert resp.status_code == 409

    release.set()
    first_resp = await task
    assert first_resp.status_code == 202
