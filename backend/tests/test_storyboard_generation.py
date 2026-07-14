import asyncio
from unittest.mock import AsyncMock

from app.services import ai_service

from tests.test_structure_generation import FAKE_AI_RESULT
from tests.test_structure_revision import _generate_and_approve

FAKE_STORYBOARD_RESULT = {
    "scenes": [
        {
            "scene_number": 1,
            "intent": "興味を引く",
            "composition": "人物クローズアップ",
            "camera_work": "静止からズームイン",
            "text_overlay": "あなたの仕事を、もっと自由に。",
        }
    ]
}

# 複数シーンの構成（time_start/time_end の累積計算を検証するため）
MULTI_SCENE_STRUCTURE_RESULT = {
    "options": [
        {
            "scenes": [
                {
                    "number": 1,
                    "title": "Opening",
                    "duration_sec": 10,
                    "description": "desc-1",
                    "shot_type": "B-roll",
                    "mood": "calm",
                    "notes": "",
                },
                {
                    "number": 2,
                    "title": "Middle",
                    "duration_sec": 20,
                    "description": "desc-2",
                    "shot_type": "Interview",
                    "mood": "serious",
                    "notes": "",
                },
                {
                    "number": 3,
                    "title": "Closing",
                    "duration_sec": 5,
                    "description": "desc-3",
                    "shot_type": "B-roll",
                    "mood": "warm",
                    "notes": "",
                },
            ],
            "total_duration_sec": 35,
            "rationale": "because",
        },
        FAKE_AI_RESULT["options"][1],
        FAKE_AI_RESULT["options"][2],
    ]
}

MULTI_SCENE_STORYBOARD_RESULT = {
    "scenes": [
        {
            "scene_number": 1,
            "intent": "興味を引く",
            "composition": "人物クローズアップ",
            "camera_work": "静止からズームイン",
            "text_overlay": "あなたの仕事を、もっと自由に。",
        },
        {
            "scene_number": 2,
            "intent": "課題を提示する",
            "composition": "インタビュー、バストショット",
            "camera_work": "固定",
            "text_overlay": "",
        },
        {
            "scene_number": 3,
            "intent": "余韻を残す",
            "composition": "オフィス全景",
            "camera_work": "ゆっくりパン",
            "text_overlay": "",
        },
    ]
}


async def test_generate_rejected_when_structure_not_approved(auth_client, project_id, monkeypatch):
    monkeypatch.setattr(
        ai_service, "generate_structure", AsyncMock(return_value=FAKE_AI_RESULT)
    )
    await auth_client.post(f"/api/v1/projects/{project_id}/structure/generate")

    resp = await auth_client.post(f"/api/v1/projects/{project_id}/storyboard/generate")
    assert resp.status_code == 400


async def test_generate_returns_pending_then_completes(auth_client, project_id, monkeypatch):
    await _generate_and_approve(auth_client, project_id, monkeypatch)

    monkeypatch.setattr(
        ai_service, "generate_storyboard", AsyncMock(return_value=FAKE_STORYBOARD_RESULT)
    )
    resp = await auth_client.post(f"/api/v1/projects/{project_id}/storyboard/generate")
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "pending"
    assert body["scenes"] == []

    resp = await auth_client.get(f"/api/v1/projects/{project_id}/storyboard")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "completed"
    assert len(body["scenes"]) == 1
    assert body["scenes"][0]["scene_number"] == 1
    assert body["scenes"][0]["time_start"] == 0
    assert body["scenes"][0]["time_end"] == 10
    assert body["scenes"][0]["composition"] == "人物クローズアップ"
    assert body["error_message"] is None

    # 生成完了時点では storyboard フェーズのまま（承認前に shooting へ先行しない）
    resp = await auth_client.get(f"/api/v1/projects/{project_id}")
    assert resp.json()["status"] == "storyboard"


async def test_generate_computes_cumulative_time_ranges(auth_client, project_id, monkeypatch):
    monkeypatch.setattr(
        ai_service, "generate_structure", AsyncMock(return_value=MULTI_SCENE_STRUCTURE_RESULT)
    )
    await auth_client.post(f"/api/v1/projects/{project_id}/structure/generate")
    await auth_client.post(f"/api/v1/projects/{project_id}/structure/approve")

    monkeypatch.setattr(
        ai_service, "generate_storyboard", AsyncMock(return_value=MULTI_SCENE_STORYBOARD_RESULT)
    )
    await auth_client.post(f"/api/v1/projects/{project_id}/storyboard/generate")

    resp = await auth_client.get(f"/api/v1/projects/{project_id}/storyboard")
    scenes = resp.json()["scenes"]
    assert [s["scene_number"] for s in scenes] == [1, 2, 3]
    assert (scenes[0]["time_start"], scenes[0]["time_end"]) == (0, 10)
    assert (scenes[1]["time_start"], scenes[1]["time_end"]) == (10, 30)
    assert (scenes[2]["time_start"], scenes[2]["time_end"]) == (30, 35)


async def test_generate_scene_number_mismatch_marks_failed(auth_client, project_id, monkeypatch):
    await _generate_and_approve(auth_client, project_id, monkeypatch)

    bad_result = {
        "scenes": [
            {
                "scene_number": 99,  # Structureに存在しない番号
                "intent": "x",
                "composition": "x",
                "camera_work": "x",
                "text_overlay": "",
            }
        ]
    }
    monkeypatch.setattr(
        ai_service, "generate_storyboard", AsyncMock(return_value=bad_result)
    )
    await auth_client.post(f"/api/v1/projects/{project_id}/storyboard/generate")

    resp = await auth_client.get(f"/api/v1/projects/{project_id}/storyboard")
    body = resp.json()
    assert body["status"] == "failed"
    assert body["error_message"]


async def test_generate_api_failure_marks_failed(auth_client, project_id, monkeypatch):
    await _generate_and_approve(auth_client, project_id, monkeypatch)

    async def boom(project, spec, structure_scenes):
        raise RuntimeError("Claude API エラー: simulated 401")

    monkeypatch.setattr(ai_service, "generate_storyboard", boom)
    await auth_client.post(f"/api/v1/projects/{project_id}/storyboard/generate")

    resp = await auth_client.get(f"/api/v1/projects/{project_id}/storyboard")
    body = resp.json()
    assert body["status"] == "failed"
    assert "simulated 401" in body["error_message"]


async def test_generate_increments_version(auth_client, project_id, monkeypatch):
    await _generate_and_approve(auth_client, project_id, monkeypatch)
    monkeypatch.setattr(
        ai_service, "generate_storyboard", AsyncMock(return_value=FAKE_STORYBOARD_RESULT)
    )

    resp = await auth_client.post(f"/api/v1/projects/{project_id}/storyboard/generate")
    assert resp.json()["version"] == 1

    resp = await auth_client.post(f"/api/v1/projects/{project_id}/storyboard/generate")
    assert resp.json()["version"] == 2


async def test_generate_returns_409_while_pending(auth_client, project_id, monkeypatch):
    await _generate_and_approve(auth_client, project_id, monkeypatch)

    started = asyncio.Event()
    release = asyncio.Event()

    async def slow_generate(project, spec, structure_scenes):
        started.set()
        await release.wait()
        return FAKE_STORYBOARD_RESULT

    monkeypatch.setattr(ai_service, "generate_storyboard", slow_generate)

    task = asyncio.create_task(
        auth_client.post(f"/api/v1/projects/{project_id}/storyboard/generate")
    )
    await started.wait()

    resp = await auth_client.post(f"/api/v1/projects/{project_id}/storyboard/generate")
    assert resp.status_code == 409

    release.set()
    first_resp = await task
    assert first_resp.status_code == 202


async def test_approve_rejects_non_completed(auth_client, project_id, monkeypatch):
    await _generate_and_approve(auth_client, project_id, monkeypatch)

    async def boom(project, spec, structure_scenes):
        raise RuntimeError("boom")

    monkeypatch.setattr(ai_service, "generate_storyboard", boom)
    await auth_client.post(f"/api/v1/projects/{project_id}/storyboard/generate")

    resp = await auth_client.post(f"/api/v1/projects/{project_id}/storyboard/approve")
    assert resp.status_code == 400


async def test_approve_succeeds_and_advances_project_status(auth_client, project_id, monkeypatch):
    await _generate_and_approve(auth_client, project_id, monkeypatch)
    monkeypatch.setattr(
        ai_service, "generate_storyboard", AsyncMock(return_value=FAKE_STORYBOARD_RESULT)
    )
    await auth_client.post(f"/api/v1/projects/{project_id}/storyboard/generate")

    resp = await auth_client.post(f"/api/v1/projects/{project_id}/storyboard/approve")
    assert resp.status_code == 200
    assert resp.json()["approved_at"] is not None

    resp = await auth_client.get(f"/api/v1/projects/{project_id}")
    assert resp.json()["status"] == "shooting"
