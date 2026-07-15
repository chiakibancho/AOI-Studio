import asyncio
from unittest.mock import AsyncMock

from app.services import ai_service

from tests.test_structure_revision import _generate_and_approve
from tests.test_storyboard_generation import (
    FAKE_STORYBOARD_RESULT,
    MULTI_SCENE_STORYBOARD_RESULT,
    MULTI_SCENE_STRUCTURE_RESULT,
)
from tests.test_storyboard_revision import _generate_and_approve_storyboard

FAKE_SHOOTING_LIST_RESULT = {
    "shots": [
        {
            "scene_number": 1,
            "category": "people",
            "title": "オフィス入口での挨拶ショット",
            "location": "オフィスエントランス",
            "equipment": "一眼カメラ、ジンバル",
            "talent_props": "出演者A",
            "notes": "逆光に注意",
        }
    ]
}

# 1シーンに複数ショット（scene_number 1 に2件）を含む結果。cut_number の連番検証用。
MULTI_SHOT_RESULT = {
    "shots": [
        {
            "scene_number": 1,
            "category": "people",
            "title": "ワイドショット",
            "location": "オフィスエントランス",
            "equipment": "一眼カメラ",
            "talent_props": "出演者A",
            "notes": "",
        },
        {
            "scene_number": 1,
            "category": "people",
            "title": "クローズアップ",
            "location": "オフィスエントランス",
            "equipment": "一眼カメラ、単焦点レンズ",
            "talent_props": "出演者A",
            "notes": "",
        },
        {
            "scene_number": 2,
            "category": "product",
            "title": "商品カット",
            "location": "会議室",
            "equipment": "三脚",
            "talent_props": "製品サンプル",
            "notes": "",
        },
        {
            "scene_number": 3,
            "category": "exterior",
            "title": "オフィス外観",
            "location": "ビル前",
            "equipment": "ドローン",
            "talent_props": "",
            "notes": "天候に注意",
        },
    ]
}


async def _generate_and_approve_multi_scene_storyboard(auth_client, project_id, monkeypatch):
    monkeypatch.setattr(
        ai_service, "generate_structure", AsyncMock(return_value=MULTI_SCENE_STRUCTURE_RESULT)
    )
    await auth_client.post(f"/api/v1/projects/{project_id}/structure/generate")
    await auth_client.post(f"/api/v1/projects/{project_id}/structure/approve")

    monkeypatch.setattr(
        ai_service, "generate_storyboard", AsyncMock(return_value=MULTI_SCENE_STORYBOARD_RESULT)
    )
    await auth_client.post(f"/api/v1/projects/{project_id}/storyboard/generate")
    resp = await auth_client.post(f"/api/v1/projects/{project_id}/storyboard/approve")
    assert resp.status_code == 200
    return resp.json()


async def _generate_and_approve_shooting_list(auth_client, project_id, monkeypatch):
    await _generate_and_approve_storyboard(auth_client, project_id, monkeypatch)
    monkeypatch.setattr(
        ai_service, "generate_shooting_list", AsyncMock(return_value=FAKE_SHOOTING_LIST_RESULT)
    )
    await auth_client.post(f"/api/v1/projects/{project_id}/shooting-list/generate")
    resp = await auth_client.post(f"/api/v1/projects/{project_id}/shooting-list/approve")
    assert resp.status_code == 200
    return resp.json()


async def test_generate_rejected_when_no_storyboard_exists(auth_client, project_id, monkeypatch):
    await _generate_and_approve(auth_client, project_id, monkeypatch)

    resp = await auth_client.post(f"/api/v1/projects/{project_id}/shooting-list/generate")
    assert resp.status_code == 404


async def test_generate_rejected_when_storyboard_not_approved(auth_client, project_id, monkeypatch):
    await _generate_and_approve(auth_client, project_id, monkeypatch)
    monkeypatch.setattr(
        ai_service, "generate_storyboard", AsyncMock(return_value=FAKE_STORYBOARD_RESULT)
    )
    await auth_client.post(f"/api/v1/projects/{project_id}/storyboard/generate")

    resp = await auth_client.post(f"/api/v1/projects/{project_id}/shooting-list/generate")
    assert resp.status_code == 400


async def test_generate_returns_pending_then_completes(auth_client, project_id, monkeypatch):
    await _generate_and_approve_storyboard(auth_client, project_id, monkeypatch)

    monkeypatch.setattr(
        ai_service, "generate_shooting_list", AsyncMock(return_value=FAKE_SHOOTING_LIST_RESULT)
    )
    resp = await auth_client.post(f"/api/v1/projects/{project_id}/shooting-list/generate")
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "pending"
    assert body["shots"] == []

    resp = await auth_client.get(f"/api/v1/projects/{project_id}/shooting-list")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "completed"
    assert len(body["shots"]) == 1
    assert body["shots"][0]["cut_number"] == 1
    assert body["shots"][0]["scene_number"] == 1
    assert body["shots"][0]["completed"] is False
    assert body["error_message"] is None

    # 生成完了時点では project.status は shooting のまま
    resp = await auth_client.get(f"/api/v1/projects/{project_id}")
    assert resp.json()["status"] == "shooting"


async def test_generate_multi_shot_per_scene_assigns_sequential_cut_numbers(
    auth_client, project_id, monkeypatch
):
    await _generate_and_approve_multi_scene_storyboard(auth_client, project_id, monkeypatch)

    monkeypatch.setattr(
        ai_service, "generate_shooting_list", AsyncMock(return_value=MULTI_SHOT_RESULT)
    )
    await auth_client.post(f"/api/v1/projects/{project_id}/shooting-list/generate")

    resp = await auth_client.get(f"/api/v1/projects/{project_id}/shooting-list")
    body = resp.json()
    assert body["status"] == "completed"
    shots = body["shots"]
    assert len(shots) == 4
    assert [s["cut_number"] for s in shots] == [1, 2, 3, 4]
    # scene_number 順に安定ソートされ、シーン1の2ショットが連続する
    assert [s["scene_number"] for s in shots] == [1, 1, 2, 3]


async def test_generate_scene_number_mismatch_marks_failed(auth_client, project_id, monkeypatch):
    await _generate_and_approve_storyboard(auth_client, project_id, monkeypatch)

    bad_result = {
        "shots": [
            {
                "scene_number": 99,  # Storyboardに存在しない番号
                "category": "people",
                "title": "x",
                "location": "x",
                "equipment": "x",
                "talent_props": "x",
                "notes": "",
            }
        ]
    }
    monkeypatch.setattr(
        ai_service, "generate_shooting_list", AsyncMock(return_value=bad_result)
    )
    await auth_client.post(f"/api/v1/projects/{project_id}/shooting-list/generate")

    resp = await auth_client.get(f"/api/v1/projects/{project_id}/shooting-list")
    body = resp.json()
    assert body["status"] == "failed"
    assert body["error_message"]


async def test_generate_invalid_category_marks_failed(auth_client, project_id, monkeypatch):
    await _generate_and_approve_storyboard(auth_client, project_id, monkeypatch)

    bad_result = {
        "shots": [
            {
                "scene_number": 1,
                "category": "not-a-real-category",
                "title": "x",
                "location": "x",
                "equipment": "x",
                "talent_props": "x",
                "notes": "",
            }
        ]
    }
    monkeypatch.setattr(
        ai_service, "generate_shooting_list", AsyncMock(return_value=bad_result)
    )
    await auth_client.post(f"/api/v1/projects/{project_id}/shooting-list/generate")

    resp = await auth_client.get(f"/api/v1/projects/{project_id}/shooting-list")
    body = resp.json()
    assert body["status"] == "failed"
    assert body["error_message"]


async def test_generate_api_failure_marks_failed(auth_client, project_id, monkeypatch):
    await _generate_and_approve_storyboard(auth_client, project_id, monkeypatch)

    async def boom(project, spec, storyboard_scenes):
        raise RuntimeError("Claude API エラー: simulated 401")

    monkeypatch.setattr(ai_service, "generate_shooting_list", boom)
    await auth_client.post(f"/api/v1/projects/{project_id}/shooting-list/generate")

    resp = await auth_client.get(f"/api/v1/projects/{project_id}/shooting-list")
    body = resp.json()
    assert body["status"] == "failed"
    assert "simulated 401" in body["error_message"]


async def test_generate_increments_version(auth_client, project_id, monkeypatch):
    await _generate_and_approve_storyboard(auth_client, project_id, monkeypatch)
    monkeypatch.setattr(
        ai_service, "generate_shooting_list", AsyncMock(return_value=FAKE_SHOOTING_LIST_RESULT)
    )

    resp = await auth_client.post(f"/api/v1/projects/{project_id}/shooting-list/generate")
    assert resp.json()["version"] == 1

    resp = await auth_client.post(f"/api/v1/projects/{project_id}/shooting-list/generate")
    assert resp.json()["version"] == 2


async def test_generate_returns_409_while_pending(auth_client, project_id, monkeypatch):
    await _generate_and_approve_storyboard(auth_client, project_id, monkeypatch)

    started = asyncio.Event()
    release = asyncio.Event()

    async def slow_generate(project, spec, storyboard_scenes):
        started.set()
        await release.wait()
        return FAKE_SHOOTING_LIST_RESULT

    monkeypatch.setattr(ai_service, "generate_shooting_list", slow_generate)

    task = asyncio.create_task(
        auth_client.post(f"/api/v1/projects/{project_id}/shooting-list/generate")
    )
    await started.wait()

    resp = await auth_client.post(f"/api/v1/projects/{project_id}/shooting-list/generate")
    assert resp.status_code == 409

    release.set()
    first_resp = await task
    assert first_resp.status_code == 202


async def test_approve_rejects_non_completed(auth_client, project_id, monkeypatch):
    await _generate_and_approve_storyboard(auth_client, project_id, monkeypatch)

    async def boom(project, spec, storyboard_scenes):
        raise RuntimeError("boom")

    monkeypatch.setattr(ai_service, "generate_shooting_list", boom)
    await auth_client.post(f"/api/v1/projects/{project_id}/shooting-list/generate")

    resp = await auth_client.post(f"/api/v1/projects/{project_id}/shooting-list/approve")
    assert resp.status_code == 400


async def test_approve_succeeds_and_advances_project_status(auth_client, project_id, monkeypatch):
    await _generate_and_approve_storyboard(auth_client, project_id, monkeypatch)
    monkeypatch.setattr(
        ai_service, "generate_shooting_list", AsyncMock(return_value=FAKE_SHOOTING_LIST_RESULT)
    )
    await auth_client.post(f"/api/v1/projects/{project_id}/shooting-list/generate")

    resp = await auth_client.post(f"/api/v1/projects/{project_id}/shooting-list/approve")
    assert resp.status_code == 200
    assert resp.json()["approved_at"] is not None

    resp = await auth_client.get(f"/api/v1/projects/{project_id}")
    assert resp.json()["status"] == "upload"


async def test_toggle_flips_completed(auth_client, project_id, monkeypatch):
    approved = await _generate_and_approve_shooting_list(auth_client, project_id, monkeypatch)
    cut_number = approved["shots"][0]["cut_number"]
    assert approved["shots"][0]["completed"] is False

    resp = await auth_client.patch(
        f"/api/v1/projects/{project_id}/shooting-list/shots/{cut_number}",
        json={"completed": True},
    )
    assert resp.status_code == 200
    body = resp.json()
    toggled = next(s for s in body["shots"] if s["cut_number"] == cut_number)
    assert toggled["completed"] is True

    resp = await auth_client.patch(
        f"/api/v1/projects/{project_id}/shooting-list/shots/{cut_number}",
        json={"completed": False},
    )
    body = resp.json()
    toggled = next(s for s in body["shots"] if s["cut_number"] == cut_number)
    assert toggled["completed"] is False


async def test_toggle_404_unknown_cut_number(auth_client, project_id, monkeypatch):
    await _generate_and_approve_shooting_list(auth_client, project_id, monkeypatch)

    resp = await auth_client.patch(
        f"/api/v1/projects/{project_id}/shooting-list/shots/999",
        json={"completed": True},
    )
    assert resp.status_code == 404


async def test_toggle_rejected_when_not_completed_status(auth_client, project_id, monkeypatch):
    await _generate_and_approve_storyboard(auth_client, project_id, monkeypatch)

    async def boom(project, spec, storyboard_scenes):
        raise RuntimeError("boom")

    monkeypatch.setattr(ai_service, "generate_shooting_list", boom)
    await auth_client.post(f"/api/v1/projects/{project_id}/shooting-list/generate")

    resp = await auth_client.patch(
        f"/api/v1/projects/{project_id}/shooting-list/shots/1",
        json={"completed": True},
    )
    assert resp.status_code == 400
