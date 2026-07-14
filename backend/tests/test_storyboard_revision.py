import asyncio
from unittest.mock import AsyncMock

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.project import Project, ProjectStatus
from app.services import ai_service

from tests.test_structure_revision import _generate_and_approve
from tests.test_storyboard_generation import FAKE_STORYBOARD_RESULT

FAKE_REVISED_STORYBOARD_RESULT = {
    "scenes": [
        {
            "scene_number": 1,
            "intent": "興味を引く（改訂）",
            "composition": "人物クローズアップ、背景をぼかす",
            "camera_work": "静止からゆっくりズームイン",
            "text_overlay": "あなたの仕事を、もっと自由に。",
        }
    ]
}


async def _generate_and_approve_storyboard(auth_client, project_id, monkeypatch):
    await _generate_and_approve(auth_client, project_id, monkeypatch)
    monkeypatch.setattr(
        ai_service, "generate_storyboard", AsyncMock(return_value=FAKE_STORYBOARD_RESULT)
    )
    await auth_client.post(f"/api/v1/projects/{project_id}/storyboard/generate")
    resp = await auth_client.post(f"/api/v1/projects/{project_id}/storyboard/approve")
    assert resp.status_code == 200
    return resp.json()


async def test_revise_rejected_when_nothing_approved(auth_client, project_id, monkeypatch):
    await _generate_and_approve(auth_client, project_id, monkeypatch)
    monkeypatch.setattr(
        ai_service, "generate_storyboard", AsyncMock(return_value=FAKE_STORYBOARD_RESULT)
    )
    await auth_client.post(f"/api/v1/projects/{project_id}/storyboard/generate")

    resp = await auth_client.post(
        f"/api/v1/projects/{project_id}/storyboard/revise",
        json={"feedback": "もっとシンプルに"},
    )
    assert resp.status_code == 400


async def test_revise_rejected_when_latest_failed(auth_client, project_id, monkeypatch):
    await _generate_and_approve(auth_client, project_id, monkeypatch)

    async def boom(project, spec, structure_scenes):
        raise RuntimeError("boom")

    monkeypatch.setattr(ai_service, "generate_storyboard", boom)
    await auth_client.post(f"/api/v1/projects/{project_id}/storyboard/generate")

    resp = await auth_client.post(
        f"/api/v1/projects/{project_id}/storyboard/revise",
        json={"feedback": "もっとシンプルに"},
    )
    assert resp.status_code == 400


async def test_revise_returns_409_while_pending(auth_client, project_id, monkeypatch):
    await _generate_and_approve_storyboard(auth_client, project_id, monkeypatch)

    started = asyncio.Event()
    release = asyncio.Event()

    async def slow_revise(project, spec, structure_scenes, base_storyboard_scenes, feedback):
        started.set()
        await release.wait()
        return FAKE_REVISED_STORYBOARD_RESULT

    monkeypatch.setattr(ai_service, "revise_storyboard", slow_revise)

    task = asyncio.create_task(
        auth_client.post(
            f"/api/v1/projects/{project_id}/storyboard/revise",
            json={"feedback": "もっとシンプルに"},
        )
    )
    await started.wait()

    resp = await auth_client.post(
        f"/api/v1/projects/{project_id}/storyboard/revise",
        json={"feedback": "別の修正"},
    )
    assert resp.status_code == 409

    release.set()
    first_resp = await task
    assert first_resp.status_code == 202


async def test_revise_creates_new_version_referencing_base(auth_client, project_id, monkeypatch):
    approved = await _generate_and_approve_storyboard(auth_client, project_id, monkeypatch)

    monkeypatch.setattr(
        ai_service, "revise_storyboard", AsyncMock(return_value=FAKE_REVISED_STORYBOARD_RESULT)
    )
    resp = await auth_client.post(
        f"/api/v1/projects/{project_id}/storyboard/revise",
        json={"feedback": "もっとシンプルに"},
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["version"] == approved["version"] + 1
    assert body["based_on_storyboard_id"] == approved["id"]
    assert body["structure_id"] == approved["structure_id"]
    assert body["human_feedback"] == "もっとシンプルに"
    assert body["scenes"] == []
    assert body["status"] == "pending"


async def test_revise_completes_and_can_be_approved(auth_client, project_id, monkeypatch):
    await _generate_and_approve_storyboard(auth_client, project_id, monkeypatch)

    monkeypatch.setattr(
        ai_service, "revise_storyboard", AsyncMock(return_value=FAKE_REVISED_STORYBOARD_RESULT)
    )
    await auth_client.post(
        f"/api/v1/projects/{project_id}/storyboard/revise",
        json={"feedback": "もっとシンプルに"},
    )

    resp = await auth_client.get(f"/api/v1/projects/{project_id}/storyboard")
    body = resp.json()
    assert body["status"] == "completed"
    assert body["scenes"][0]["intent"] == "興味を引く（改訂）"
    assert body["scenes"][0]["time_start"] == 0
    assert body["scenes"][0]["time_end"] == 10

    resp = await auth_client.post(f"/api/v1/projects/{project_id}/storyboard/approve")
    assert resp.status_code == 200
    assert resp.json()["approved_at"] is not None


async def test_revise_malformed_ai_output_marks_failed(auth_client, project_id, monkeypatch):
    await _generate_and_approve_storyboard(auth_client, project_id, monkeypatch)

    bad_result = {"scenes": [{"scene_number": 1}]}  # 必須フィールド欠落
    monkeypatch.setattr(
        ai_service, "revise_storyboard", AsyncMock(return_value=bad_result)
    )
    await auth_client.post(
        f"/api/v1/projects/{project_id}/storyboard/revise",
        json={"feedback": "もっとシンプルに"},
    )

    resp = await auth_client.get(f"/api/v1/projects/{project_id}/storyboard")
    body = resp.json()
    assert body["status"] == "failed"
    assert body["error_message"]


async def test_revise_scene_number_mismatch_marks_failed(auth_client, project_id, monkeypatch):
    await _generate_and_approve_storyboard(auth_client, project_id, monkeypatch)

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
        ai_service, "revise_storyboard", AsyncMock(return_value=bad_result)
    )
    await auth_client.post(
        f"/api/v1/projects/{project_id}/storyboard/revise",
        json={"feedback": "もっとシンプルに"},
    )

    resp = await auth_client.get(f"/api/v1/projects/{project_id}/storyboard")
    body = resp.json()
    assert body["status"] == "failed"
    assert body["error_message"]


async def test_revise_approval_does_not_regress_project_status(auth_client, project_id, monkeypatch):
    await _generate_and_approve_storyboard(auth_client, project_id, monkeypatch)

    # 承認後、プロジェクトが撮影より先のフェーズまで進んでいる想定を DB 上で再現する。
    # shooting までしか進めないと「後退していない」のか「approveで正しくshootingに
    # 進んだだけ」なのか区別できないため、より先の upload まで進めておく。
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one()
        project.status = ProjectStatus.upload
        await db.commit()

    monkeypatch.setattr(
        ai_service, "revise_storyboard", AsyncMock(return_value=FAKE_REVISED_STORYBOARD_RESULT)
    )
    await auth_client.post(
        f"/api/v1/projects/{project_id}/storyboard/revise",
        json={"feedback": "もっとシンプルに"},
    )

    resp = await auth_client.get(f"/api/v1/projects/{project_id}")
    assert resp.json()["status"] == "upload"

    await auth_client.post(f"/api/v1/projects/{project_id}/storyboard/approve")

    resp = await auth_client.get(f"/api/v1/projects/{project_id}")
    assert resp.json()["status"] == "upload"
