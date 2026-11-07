"""Audio sintético de las pistas locales. No se versiona: se genera con ffmpeg en cada instalación."""
import asyncio
import shutil
import subprocess
from pathlib import Path

from mutagen.mp3 import MP3

from app.core.config import get_settings

FOLDER = "demo"
NOTES = (220.0, 247.0, 262.0, 294.0, 330.0, 349.0, 392.0, 440.0, 494.0, 523.0, 587.0, 659.0)


def _render(path: Path, frequency: float, seconds: int) -> None:
    source = f"sine=frequency={frequency}:duration={seconds}"
    fade = f"afade=t=in:d=1,afade=t=out:st={seconds - 2}:d=2,volume=0.4"
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", source, "-af", fade, "-ac", "1", "-b:a", "64k", str(path)],
        check=True,
    )


def _folder() -> Path:
    return Path(get_settings().MEDIA_DIR) / FOLDER


async def ensure_tones(count: int) -> list[tuple[str, float]]:
    """Devuelve ruta relativa y duración de cada tono, sin repetir los que ya existen."""
    folder = _folder()
    folder.mkdir(parents=True, exist_ok=True)
    tones = []
    for index in range(count):
        name = f"tono-{index:02}.mp3"
        path = folder / name
        if not path.exists():
            await asyncio.to_thread(_render, path, NOTES[index % len(NOTES)], 30 + 3 * (index % 6))
        tones.append((f"{FOLDER}/{name}", MP3(path).info.length))
    return tones


def remove_tones() -> None:
    shutil.rmtree(_folder(), ignore_errors=True)
