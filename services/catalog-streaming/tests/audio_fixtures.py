import math
import struct
import uuid
import wave
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog import repository
from app.modules.catalog.models import Song
from app.modules.catalog.schemas import SongOut

_RATE = 8000


def make_wav(path: Path, seconds: float = 2.0) -> Path:
    """WAV mono de 16 bits a 8 kHz con un tono simple."""
    frames = b"".join(
        struct.pack("<h", int(8000 * math.sin(2 * math.pi * 440 * i / _RATE)))
        for i in range(int(_RATE * seconds))
    )
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(_RATE)
        wav.writeframes(frames)
    return path


async def insert_song(
    session: AsyncSession,
    media_dir: Path,
    title: str = "Nubes de agosto",
    artist: str = "Los Meteoros",
    album: str = "Pronóstico",
    seconds: float = 2.0,
    is_active: bool = True,
) -> SongOut:
    song_id = uuid.uuid4()
    name = f"{song_id}.wav"
    path = make_wav(media_dir / name, seconds)
    song = Song(
        id=song_id,
        title=title,
        artist=artist,
        album=album,
        duration_seconds=max(1, round(seconds)),
        file_path=name,
        mime_type="audio/wav",
        size_bytes=path.stat().st_size,
        is_active=is_active,
    )
    await repository.add(session, song)
    return SongOut.model_validate(song)
