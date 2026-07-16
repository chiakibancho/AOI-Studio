import asyncio
import os
import tempfile

import essentia.standard as es

ALLOWED_EXTENSIONS = {".mp3", ".wav"}


class UnsupportedAudioFormatError(Exception):
    """非対応フォーマット、または音声として読み込めないファイルが渡された場合。"""


def _run_analysis(path: str) -> dict:
    try:
        audio = es.MonoLoader(filename=path)()
    except RuntimeError as e:
        raise UnsupportedAudioFormatError(f"音声ファイルを読み込めませんでした: {e}") from e

    if len(audio) == 0:
        raise UnsupportedAudioFormatError("音声データが空です")

    key, scale, key_strength = es.KeyExtractor()(audio)
    bpm, _beats, _confidence, _, _ = es.RhythmExtractor2013(method="multifeature")(audio)

    return {
        "bpm": float(bpm),
        "key": key,
        "scale": scale,
        "key_strength": float(key_strength),
    }


async def analyze_audio_file(filename: str, content: bytes) -> dict:
    """アップロードされた音声ファイルを解析し、BPM・キー・スケール・キー信頼度を返す。

    非対応拡張子、またはデコードに失敗した場合は UnsupportedAudioFormatError を送出する。
    essentia のデコード/解析はCPUバウンドな同期処理のため、イベントループを塞がないよう
    asyncio.to_thread で別スレッドに逃がす。
    """
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise UnsupportedAudioFormatError(
            f"非対応の音声フォーマットです（対応形式: mp3, wav）: {ext or '(拡張子なし)'}"
        )

    fd, tmp_path = tempfile.mkstemp(suffix=ext)
    try:
        with os.fdopen(fd, "wb") as tmp:
            tmp.write(content)
        return await asyncio.to_thread(_run_analysis, tmp_path)
    finally:
        os.unlink(tmp_path)
