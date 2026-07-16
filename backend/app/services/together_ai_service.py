import httpx

from app.core.config import settings

TOGETHER_IMAGE_ENDPOINT = "https://api.together.xyz/v1/images/generations"
_MODEL = "black-forest-labs/FLUX.1-dev"


class ImageGenerationError(Exception):
    """Together AI 呼び出し、または生成画像のダウンロードに失敗した場合。"""


async def generate_character_sheet_image(prompt: str) -> bytes:
    """Together AI (FLUX.1-dev) でキャラクターのモデルシート画像を生成し、画像バイトを返す。

    Together AI が返す画像URLは有効期限があるため、レスポンスを受け取ったこのリクエストの
    中で即座にダウンロードする（呼び出し側でURLをそのまま保存しない）。
    """
    async with httpx.AsyncClient(timeout=120) as client:
        try:
            resp = await client.post(
                TOGETHER_IMAGE_ENDPOINT,
                headers={"Authorization": f"Bearer {settings.TOGETHER_API_KEY}"},
                json={
                    "model": _MODEL,
                    "prompt": prompt,
                    "width": 1536,
                    "height": 1024,
                    "steps": 28,
                    "n": 1,
                    "response_format": "url",
                },
            )
        except httpx.HTTPError as e:
            raise ImageGenerationError(f"Together AI への接続に失敗しました: {e}") from e

        if resp.status_code != 200:
            raise ImageGenerationError(f"Together AI エラー: {resp.status_code} {resp.text}")

        data = resp.json()
        try:
            image_url = data["data"][0]["url"]
        except (KeyError, IndexError, TypeError) as e:
            raise ImageGenerationError(f"Together AI のレスポンス形式が不正です: {data}") from e

        try:
            image_resp = await client.get(image_url)
        except httpx.HTTPError as e:
            raise ImageGenerationError(f"生成画像のダウンロードに失敗しました: {e}") from e

        if image_resp.status_code != 200:
            raise ImageGenerationError(
                f"生成画像のダウンロードに失敗しました: {image_resp.status_code}"
            )

        return image_resp.content
