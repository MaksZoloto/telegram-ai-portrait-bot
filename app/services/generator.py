from __future__ import annotations

import asyncio
import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import httpx
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

from app.config import Settings
from app.styles import PortraitStyle


class PortraitGenerator(Protocol):
    async def generate(self, *, source_path: Path, style: PortraitStyle) -> bytes:
        ...


@dataclass
class DemoPortraitGenerator:
    max_size: int = 1024

    async def generate(self, *, source_path: Path, style: PortraitStyle) -> bytes:
        return await asyncio.to_thread(self._render, source_path, style)

    def _render(self, source_path: Path, style: PortraitStyle) -> bytes:
        with Image.open(source_path) as raw:
            image = ImageOps.exif_transpose(raw).convert("RGB")
            image.thumbnail((self.max_size, self.max_size))

            if style.code == "cinematic":
                image = ImageEnhance.Contrast(image).enhance(1.25)
                image = ImageEnhance.Color(image).enhance(0.9)
                image = ImageEnhance.Sharpness(image).enhance(1.15)
            elif style.code == "cyberpunk":
                gray = ImageOps.grayscale(image)
                image = ImageOps.colorize(gray, black="#111827", white="#ec4899").convert("RGB")
                image = ImageEnhance.Contrast(image).enhance(1.35)
            else:
                image = image.filter(ImageFilter.SMOOTH_MORE)
                image = ImageOps.posterize(image, 5)
                image = ImageEnhance.Color(image).enhance(0.75)

            canvas = Image.new("RGB", (image.width, image.height + 70), "#0f172a")
            canvas.paste(image, (0, 0))
            draw = ImageDraw.Draw(canvas)
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
            except OSError:
                font = ImageFont.load_default()
            draw.text((24, image.height + 20), f"DEMO • {style.code}", fill="#f8fafc", font=font)

            buffer = io.BytesIO()
            canvas.save(buffer, format="JPEG", quality=92)
            return buffer.getvalue()


class LeonardoPortraitGenerator:
    base_url = "https://cloud.leonardo.ai/api/rest/v1"

    def __init__(self, settings: Settings) -> None:
        if settings.leonardo_api_key is None or not settings.leonardo_model_id:
            raise RuntimeError("LEONARDO_API_KEY and LEONARDO_MODEL_ID are required")
        self.api_key = settings.leonardo_api_key.get_secret_value()
        self.model_id = settings.leonardo_model_id
        self.timeout_sec = settings.generation_timeout_sec

    @property
    def headers(self) -> dict[str, str]:
        return {
            "accept": "application/json",
            "authorization": f"Bearer {self.api_key}",
        }

    async def _upload_init_image(self, client: httpx.AsyncClient, source_path: Path) -> str:
        init_response = await client.post(
            f"{self.base_url}/init-image",
            headers={**self.headers, "content-type": "application/json"},
            json={"extension": source_path.suffix.lstrip(".").lower() or "jpg"},
        )
        init_response.raise_for_status()
        upload = init_response.json()["uploadInitImage"]
        fields = json.loads(upload["fields"])
        with source_path.open("rb") as source:
            upload_response = await client.post(
                upload["url"],
                data=fields,
                files={"file": (source_path.name, source, "application/octet-stream")},
            )
        upload_response.raise_for_status()
        return str(upload["id"])

    async def generate(self, *, source_path: Path, style: PortraitStyle) -> bytes:
        async with httpx.AsyncClient(timeout=30) as client:
            init_image_id = await self._upload_init_image(client, source_path)
            create_response = await client.post(
                f"{self.base_url}/generations",
                headers={**self.headers, "content-type": "application/json"},
                json={
                    "modelId": self.model_id,
                    "prompt": style.prompt,
                    "num_images": 1,
                    "width": 768,
                    "height": 768,
                    "photoReal": True,
                    "photoRealVersion": "v2",
                    "init_image_id": init_image_id,
                    "init_strength": 0.35,
                },
            )
            create_response.raise_for_status()
            generation_id = str(create_response.json()["sdGenerationJob"]["generationId"])

            deadline = asyncio.get_running_loop().time() + self.timeout_sec
            while asyncio.get_running_loop().time() < deadline:
                await asyncio.sleep(3)
                status_response = await client.get(
                    f"{self.base_url}/generations/{generation_id}",
                    headers=self.headers,
                )
                status_response.raise_for_status()
                images = (
                    status_response.json()
                    .get("generations_by_pk", {})
                    .get("generated_images", [])
                )
                if images:
                    image_response = await client.get(str(images[0]["url"]))
                    image_response.raise_for_status()
                    return image_response.content

        raise TimeoutError("Image generation timed out")


def build_generator(settings: Settings) -> PortraitGenerator:
    if settings.demo_mode:
        return DemoPortraitGenerator()
    return LeonardoPortraitGenerator(settings)
