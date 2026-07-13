import asyncio
from unittest.mock import AsyncMock

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.project import Project, ProjectStatus
from app.services import ai_service

from tests.test_structure_generation import FAKE_AI_RESULT

FAKE_REVISED_RESULT = {
    "scenes": [
        {
            "number": 1,
            "title": "Opening (revised)",
            "duration_sec": 15,
            "description": "revised desc",
            "shot_type": "B-roll",
            "mood": "calm",
            "notes": "",
        }
    ],
    "total_duration_sec": 15,
    "rationale": "revised because",
}


async def _generate_and_approve(auth_client, project_id, monkeypatch, option_index=0):
    monkeypatch.setattr(
        ai_service, "generate_structure", AsyncMock(return_value=FAKE_AI_RESULT)
    )
    await auth_client.post(f"/api/v1/projects/{project_id}/structure/generate")
    resp = await auth_client.post(
        f"/api/v1/projects/{project_id}/structure/approve",
        params={"option_index": option_index},
    )
    assert resp.status_code == 200
    return resp.json()


async def test_revise_rejected_when_nothing_approved(auth_client, project_id, monkeypatch):
    monkeypatch.setattr(
        ai_service, "generate_structure", AsyncMock(return_value=FAKE_AI_RESULT)
    )
    await auth_client.post(f"/api/v1/projects/{project_id}/structure/generate")

    resp = await auth_client.post(
        f"/api/v1/projects/{project_id}/structure/revise",
        json={"feedback": "もっと短くして"},
    )
    assert resp.status_code == 400


async def test_revise_rejected_when_latest_failed(auth_client, project_id, monkeypatch):
    async def boom(project, spec):
        raise RuntimeError("boom")

    monkeypatch.setattr(ai_service, "generate_structure", boom)
    await auth_client.post(f"/api/v1/projects/{project_id}/structure/generate")

    resp = await auth_client.post(
        f"/api/v1/projects/{project_id}/structure/revise",
        json={"feedback": "もっと短くして"},
    )
    assert resp.status_code == 400


async def test_revise_returns_409_while_pending(auth_client, project_id, monkeypatch):
    await _generate_and_approve(auth_client, project_id, monkeypatch)

    started = asyncio.Event()
    release = asyncio.Event()

    async def slow_revise(project, spec, base_scenes, base_rationale, feedback):
        started.set()
        await release.wait()
        return FAKE_REVISED_RESULT

    monkeypatch.setattr(ai_service, "revise_structure", slow_revise)

    task = asyncio.create_task(
        auth_client.post(
            f"/api/v1/projects/{project_id}/structure/revise",
            json={"feedback": "もっと短くして"},
        )
    )
    await started.wait()

    resp = await auth_client.post(
        f"/api/v1/projects/{project_id}/structure/revise",
        json={"feedback": "別の修正"},
    )
    assert resp.status_code == 409

    release.set()
    first_resp = await task
    assert first_resp.status_code == 202


async def test_revise_creates_new_version_referencing_base(auth_client, project_id, monkeypatch):
    approved = await _generate_and_approve(auth_client, project_id, monkeypatch)

    monkeypatch.setattr(
        ai_service, "revise_structure", AsyncMock(return_value=FAKE_REVISED_RESULT)
    )
    resp = await auth_client.post(
        f"/api/v1/projects/{project_id}/structure/revise",
        json={"feedback": "もっと短くして"},
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["version"] == approved["version"] + 1
    assert body["based_on_structure_id"] == approved["id"]
    assert body["human_feedback"] == "もっと短くして"
    assert body["options"] == []
    assert body["status"] == "pending"


async def test_revise_completes_and_can_be_approved(auth_client, project_id, monkeypatch):
    await _generate_and_approve(auth_client, project_id, monkeypatch)

    monkeypatch.setattr(
        ai_service, "revise_structure", AsyncMock(return_value=FAKE_REVISED_RESULT)
    )
    await auth_client.post(
        f"/api/v1/projects/{project_id}/structure/revise",
        json={"feedback": "もっと短くして"},
    )

    resp = await auth_client.get(f"/api/v1/projects/{project_id}/structure")
    body = resp.json()
    assert body["status"] == "completed"
    assert body["scenes"][0]["title"] == "Opening (revised)"
    assert body["total_duration_sec"] == 15

    resp = await auth_client.post(f"/api/v1/projects/{project_id}/structure/approve")
    assert resp.status_code == 200
    body = resp.json()
    assert body["approved_at"] is not None
    assert body["scenes"][0]["title"] == "Opening (revised)"


async def test_revise_malformed_ai_output_marks_failed(auth_client, project_id, monkeypatch):
    await _generate_and_approve(auth_client, project_id, monkeypatch)

    bad_result = {"scenes": [{"number": 1, "title": "Opening"}]}  # 必須フィールド欠落
    monkeypatch.setattr(
        ai_service, "revise_structure", AsyncMock(return_value=bad_result)
    )
    await auth_client.post(
        f"/api/v1/projects/{project_id}/structure/revise",
        json={"feedback": "もっと短くして"},
    )

    resp = await auth_client.get(f"/api/v1/projects/{project_id}/structure")
    body = resp.json()
    assert body["status"] == "failed"
    assert body["error_message"]

    resp = await auth_client.get(f"/api/v1/projects/{project_id}")
    assert resp.json()["status"] == "storyboard"


async def test_revise_approval_does_not_regress_project_status(auth_client, project_id, monkeypatch):
    await _generate_and_approve(auth_client, project_id, monkeypatch)

    # 承認後、プロジェクトが撮影フェーズまで進んでいる想定を DB 上で再現する
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one()
        project.status = ProjectStatus.shooting
        await db.commit()

    monkeypatch.setattr(
        ai_service, "revise_structure", AsyncMock(return_value=FAKE_REVISED_RESULT)
    )
    await auth_client.post(
        f"/api/v1/projects/{project_id}/structure/revise",
        json={"feedback": "もっと短くして"},
    )

    resp = await auth_client.get(f"/api/v1/projects/{project_id}")
    assert resp.json()["status"] == "shooting"

    await auth_client.post(f"/api/v1/projects/{project_id}/structure/approve")

    resp = await auth_client.get(f"/api/v1/projects/{project_id}")
    assert resp.json()["status"] == "shooting"


async def test_regenerate_after_approve_does_not_regress_project_status(
    auth_client, project_id, monkeypatch
):
    await _generate_and_approve(auth_client, project_id, monkeypatch)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one()
        project.status = ProjectStatus.shooting
        await db.commit()

    # 承認後でも「再生成する」（3案フルリセット）は今日のUIから引き続き呼べるが、
    # project.status を後退させてはいけない。
    monkeypatch.setattr(
        ai_service, "generate_structure", AsyncMock(return_value=FAKE_AI_RESULT)
    )
    await auth_client.post(f"/api/v1/projects/{project_id}/structure/generate")

    resp = await auth_client.get(f"/api/v1/projects/{project_id}")
    assert resp.json()["status"] == "shooting"
