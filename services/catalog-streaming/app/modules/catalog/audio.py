from dataclasses import dataclass
from pathlib import Path

import mutagen

from app.shared.errors import InvalidInput

_MIME_BY_EXTENSION = {".mp3": "audio/mpeg", ".ogg": "audio/ogg", ".wav": "audio/wav"}


@dataclass
class AudioInfo:
    duration_seconds: int
    mime_type: str


def inspect_audio(path: Path) -> AudioInfo:
    """Valida con mutagen que el archivo sea audio y extrae duración y tipo MIME."""
    error = InvalidInput("El archivo no es un audio válido.", code="invalid_audio")
    mime_type = _MIME_BY_EXTENSION.get(path.suffix.lower())
    if mime_type is None:
        raise error
    try:
        audio = mutagen.File(path)
        if audio is None or audio.info is None:
            raise error
        duration = max(1, round(audio.info.length))
    except InvalidInput:
        raise
    except Exception as exc:
        raise error from exc
    return AudioInfo(duration_seconds=duration, mime_type=mime_type)
