"""Archivos mínimos válidos para pruebas de subida."""
MP3_FRAME = b"\xff\xfb\x90\x00" + b"\x00" * 413  # MPEG1 Layer III, 128 kbps, 44.1 kHz
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 100
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100


def mp3(frames: int = 100) -> bytes:
    return MP3_FRAME * frames
