import asyncio

from app.services import ai_service

from tests.test_shooting_list_generation import (
    FAKE_SHOOTING_LIST_RESULT,
    _generate_and_approve_shooting_list,
)
from tests.test_storyboard_revision import _generate_and_approve_storyboard


async def test_export_404_when_no_shooting_list(auth_client, project_id, monkeypatch):
    await _generate_and_approve_storyboard(auth_client, project_id, monkeypatch)

    resp = await auth_client.get(f"/api/v1/projects/{project_id}/shooting-list/export")
    assert resp.status_code == 404


async def test_export_has_utf8_bom(auth_client, project_id, monkeypatch):
    await _generate_and_approve_shooting_list(auth_client, project_id, monkeypatch)

    resp = await auth_client.get(f"/api/v1/projects/{project_id}/shooting-list/export")
    assert resp.status_code == 200
    assert resp.content.startswith(b"\xef\xbb\xbf")


async def test_export_columns_and_values(auth_client, project_id, monkeypatch):
    approved = await _generate_and_approve_shooting_list(auth_client, project_id, monkeypatch)
    shot = approved["shots"][0]

    resp = await auth_client.get(f"/api/v1/projects/{project_id}/shooting-list/export")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]

    text = resp.content.decode("utf-8-sig")
    lines = text.strip("\r\n").split("\r\n")
    assert lines[0] == "カテゴリ,ショット番号,内容,チェック状態"

    assert len(lines) == 1 + len(FAKE_SHOOTING_LIST_RESULT["shots"])
    assert lines[1] == f"人物,{shot['cut_number']},{shot['title']},未"


async def test_export_reflects_completed_status_in_japanese(auth_client, project_id, monkeypatch):
    approved = await _generate_and_approve_shooting_list(auth_client, project_id, monkeypatch)
    cut_number = approved["shots"][0]["cut_number"]

    await auth_client.patch(
        f"/api/v1/projects/{project_id}/shooting-list/shots/{cut_number}",
        json={"completed": True},
    )

    resp = await auth_client.get(f"/api/v1/projects/{project_id}/shooting-list/export")
    text = resp.content.decode("utf-8-sig")
    lines = text.strip("\r\n").split("\r\n")
    assert lines[1].endswith(",済")


async def test_export_empty_when_generation_still_pending(auth_client, project_id, monkeypatch):
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

    resp = await auth_client.get(f"/api/v1/projects/{project_id}/shooting-list/export")
    assert resp.status_code == 200
    text = resp.content.decode("utf-8-sig")
    lines = text.strip("\r\n").split("\r\n")
    assert lines == ["カテゴリ,ショット番号,内容,チェック状態"]

    release.set()
    await task
