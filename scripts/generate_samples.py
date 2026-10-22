"""
Script para generar archivos de audio WAV sintéticos y agradables para el catálogo de demostración de FLDSMDFR.
Permite reproducir streaming real sin depender de descargas externas de archivos pesados.
"""

import math
import struct
import wave
from pathlib import Path

AUDIO_DIR = Path(__file__).resolve().parent.parent / "media" / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

SAMPLE_RATE = 44100  # Hz


def generate_synth_track(
    filename: str,
    duration: float,
    notes: list[float],
    tempo_bpm: float = 120,
    waveform: str = "sine",
):
    """Genera un archivo WAV de 16-bit mono con una secuencia de notas sintetizadas."""
    output_path = AUDIO_DIR / filename
    num_samples = int(duration * SAMPLE_RATE)
    seconds_per_beat = 60.0 / tempo_bpm
    samples_per_note = int(seconds_per_beat * SAMPLE_RATE)

    with wave.open(str(output_path), "w") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(SAMPLE_RATE)

        raw_data = bytearray()
        for i in range(num_samples):
            note_idx = (i // samples_per_note) % len(notes)
            freq = notes[note_idx]

            # Tiempo dentro de la nota actual para envolvente (fade-in / fade-out)
            t_note = (i % samples_per_note) / SAMPLE_RATE
            note_duration = seconds_per_beat
            # Envolvente simple
            envelope = min(1.0, t_note / 0.05) * max(
                0.0, (note_duration - t_note) / (note_duration * 0.5)
            )

            # Forma de onda
            t = i / SAMPLE_RATE
            if waveform == "sine":
                val = math.sin(2 * math.pi * freq * t)
                # Agregar un armónico suave para calidez
                val += 0.3 * math.sin(4 * math.pi * freq * t)
            elif waveform == "chime":
                val = math.sin(2 * math.pi * freq * t) * 0.7 + math.sin(
                    6 * math.pi * freq * t
                ) * 0.3
            else:
                val = math.sin(2 * math.pi * freq * t)

            sample_val = int(val * envelope * 0.5 * 32767.0)
            sample_val = max(-32768, min(32767, sample_val))
            raw_data.extend(struct.pack("<h", sample_val))

        wav_file.writeframes(raw_data)
    print(f"Generado: {output_path} ({duration}s, {len(raw_data)} bytes)")


if __name__ == "__main__":
    # Pista 1: Cosmic Lofi (Escala Pentatónica Menor en La: A4=440, C5=523.25, D5=587.33, E5=659.25, G5=783.99)
    generate_synth_track(
        filename="cosmic_lofi.wav",
        duration=20.0,
        notes=[440.0, 523.25, 587.33, 659.25, 783.99, 659.25, 587.33, 523.25],
        tempo_bpm=110,
        waveform="sine",
    )

    # Pista 2: Neon Cyberpunk (Escala Frigia en Mi: E4=329.63, F4=349.23, G4=392.00, A4=440.0, B4=493.88)
    generate_synth_track(
        filename="neon_cyberpunk.wav",
        duration=22.0,
        notes=[329.63, 349.23, 392.00, 440.00, 392.00, 349.23, 329.63, 293.66],
        tempo_bpm=128,
        waveform="chime",
    )

    # Pista 3: Chillwave Beats (Secuencia de acordes suaves en Do Mayor)
    generate_synth_track(
        filename="chillwave_beats.wav",
        duration=18.0,
        notes=[523.25, 659.25, 783.99, 659.25, 587.33, 698.46, 880.00, 698.46],
        tempo_bpm=96,
        waveform="sine",
    )
