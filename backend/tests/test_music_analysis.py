import io
import math
import struct
import wave


def _make_wav_bytes(duration: float = 2, freq: float = 440, sr: int = 44100) -> bytes:
    """合成サイン波のPCM16 WAVをバイト列で生成する（essentia環境確認時と同じ波形）。"""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        frames = bytearray()
        for i in range(int(sr * duration)):
            val = int(32767 * 0.5 * math.sin(2 * math.pi * freq * i / sr))
            frames += struct.pack("<h", val)
        w.writeframes(bytes(frames))
    return buffer.getvalue()


async def test_analyze_returns_bpm_and_key(auth_client, project_id):
    resp = await auth_client.post(
        f"/api/v1/projects/{project_id}/music-analysis",
        files={"file": ("test.wav", _make_wav_bytes(), "audio/wav")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["filename"] == "test.wav"
    assert body["bpm"] > 0
    assert body["scale"] in {"major", "minor"}
    assert 0.0 <= body["key_strength"] <= 1.0


async def test_get_returns_saved_analysis_without_reupload(auth_client, project_id):
    post_resp = await auth_client.post(
        f"/api/v1/projects/{project_id}/music-analysis",
        files={"file": ("test.wav", _make_wav_bytes(), "audio/wav")},
    )
    posted = post_resp.json()

    resp = await auth_client.get(f"/api/v1/projects/{project_id}/music-analysis")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == posted["id"]
    assert body["bpm"] == posted["bpm"]
    assert body["key"] == posted["key"]


async def test_get_404_when_not_analyzed_yet(auth_client, project_id):
    resp = await auth_client.get(f"/api/v1/projects/{project_id}/music-analysis")
    assert resp.status_code == 404


async def test_reupload_overwrites_previous_analysis(auth_client, project_id):
    resp_a = await auth_client.post(
        f"/api/v1/projects/{project_id}/music-analysis",
        files={"file": ("a.wav", _make_wav_bytes(freq=440), "audio/wav")},
    )
    id_a = resp_a.json()["id"]

    resp_b = await auth_client.post(
        f"/api/v1/projects/{project_id}/music-analysis",
        files={"file": ("b.wav", _make_wav_bytes(freq=220, duration=3), "audio/wav")},
    )
    assert resp_b.status_code == 200
    body_b = resp_b.json()
    assert body_b["id"] == id_a  # 1プロジェクト1レコードなので上書きされる
    assert body_b["filename"] == "b.wav"

    resp = await auth_client.get(f"/api/v1/projects/{project_id}/music-analysis")
    assert resp.json()["filename"] == "b.wav"


async def test_unsupported_extension_returns_422(auth_client, project_id):
    resp = await auth_client.post(
        f"/api/v1/projects/{project_id}/music-analysis",
        files={"file": ("notes.txt", b"this is not audio", "text/plain")},
    )
    assert resp.status_code == 422


async def test_corrupt_wav_content_returns_422(auth_client, project_id):
    resp = await auth_client.post(
        f"/api/v1/projects/{project_id}/music-analysis",
        files={"file": ("broken.wav", b"not really a wav file", "audio/wav")},
    )
    assert resp.status_code == 422


async def test_empty_file_returns_422(auth_client, project_id):
    resp = await auth_client.post(
        f"/api/v1/projects/{project_id}/music-analysis",
        files={"file": ("empty.wav", b"", "audio/wav")},
    )
    assert resp.status_code == 422
