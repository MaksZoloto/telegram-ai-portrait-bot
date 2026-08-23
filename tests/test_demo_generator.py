from pathlib import Path

import pytest
from PIL import Image

from app.services.generator import DemoPortraitGenerator
from app.styles import STYLES


@pytest.mark.asyncio
async def test_demo_generator_returns_jpeg(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    Image.new("RGB", (320, 240), "white").save(source)

    content = await DemoPortraitGenerator().generate(
        source_path=source,
        style=STYLES["cinematic"],
    )

    result = tmp_path / "result.jpg"
    result.write_bytes(content)
    with Image.open(result) as image:
        assert image.format == "JPEG"
        assert image.height > 240
