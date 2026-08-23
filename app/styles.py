from dataclasses import dataclass


@dataclass(frozen=True)
class PortraitStyle:
    code: str
    title_ru: str
    title_en: str
    prompt: str


STYLES: dict[str, PortraitStyle] = {
    "cinematic": PortraitStyle(
        code="cinematic",
        title_ru="Кинематографический портрет",
        title_en="Cinematic portrait",
        prompt="cinematic photorealistic portrait, soft dramatic light, detailed face",
    ),
    "cyberpunk": PortraitStyle(
        code="cyberpunk",
        title_ru="Киберпанк",
        title_en="Cyberpunk",
        prompt="cyberpunk portrait, neon lights, futuristic city, detailed face",
    ),
    "watercolor": PortraitStyle(
        code="watercolor",
        title_ru="Акварель",
        title_en="Watercolor",
        prompt="elegant watercolor portrait, soft brush strokes, clean composition",
    ),
}


def style_title(code: str, language: str) -> str:
    style = STYLES[code]
    return style.title_en if language == "en" else style.title_ru
