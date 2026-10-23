import sqlite3

from core.config import MIN_PLAYBACK_SECONDS
from core.module_playback.models import (
    PlaybackEventCreate,
    PlaybackEventResponse,
    TopSongMetric,
)
from db.connection import get_db_connection


class PlaybackService:

    @staticmethod
    def record_playback(event: PlaybackEventCreate) -> PlaybackEventResponse:
        # Criterio PRD: Se requiere al menos 10 segundos de reproducción
        if event.played_duration < MIN_PLAYBACK_SECONDS:
            raise ValueError(
                f"La duración reproducida ({event.played_duration:.1f}s) es menor al umbral mínimo requerido ({MIN_PLAYBACK_SECONDS:.1f}s)."
            )

        with get_db_connection() as conn:
            # 1. Validar existencia de la canción
            song = conn.execute(
                "SELECT id FROM songs WHERE id = ?", (event.song_id,)
            ).fetchone()
            if not song:
                raise KeyError(f"La canción con id {event.song_id} no existe en el catálogo.")

            # 2. Verificar idempotencia: ¿Ya existe el playback_id?
            existing_playback = conn.execute(
                "SELECT playback_id FROM playbacks WHERE playback_id = ?",
                (event.playback_id,),
            ).fetchone()

            if existing_playback:
                # Ya fue procesado previamente; no incrementar contador
                metric = conn.execute(
                    "SELECT play_count FROM song_metrics WHERE song_id = ?",
                    (event.song_id,),
                ).fetchone()
                current_count = metric["play_count"] if metric else 0
                return PlaybackEventResponse(
                    playback_id=event.playback_id,
                    song_id=event.song_id,
                    counted=False,
                    current_play_count=current_count,
                    message="Evento de reproducción ya procesado previamente (idempotencia garantizada).",
                )

            # 3. Registrar nuevo evento e incrementar sincrónicamente el contador
            try:
                conn.execute(
                    """
                    INSERT INTO playbacks (playback_id, song_id, user_id, played_duration)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        event.playback_id,
                        event.song_id,
                        event.user_id,
                        event.played_duration,
                    ),
                )
            except sqlite3.IntegrityError:
                # Caso carrera concurrente con la misma clave de idempotencia
                metric = conn.execute(
                    "SELECT play_count FROM song_metrics WHERE song_id = ?",
                    (event.song_id,),
                ).fetchone()
                return PlaybackEventResponse(
                    playback_id=event.playback_id,
                    song_id=event.song_id,
                    counted=False,
                    current_play_count=metric["play_count"] if metric else 0,
                    message="Evento duplicado detectado por restricción de clave primaria.",
                )

            # 4. Incremento sincrónico en song_metrics
            conn.execute(
                """
                INSERT INTO song_metrics (song_id, play_count, last_played_at)
                VALUES (?, 1, CURRENT_TIMESTAMP)
                ON CONFLICT(song_id) DO UPDATE SET
                    play_count = song_metrics.play_count + 1,
                    last_played_at = CURRENT_TIMESTAMP
                """,
                (event.song_id,),
            )

            metric = conn.execute(
                "SELECT play_count FROM song_metrics WHERE song_id = ?",
                (event.song_id,),
            ).fetchone()
            new_count = metric["play_count"] if metric else 1

            return PlaybackEventResponse(
                playback_id=event.playback_id,
                song_id=event.song_id,
                counted=True,
                current_play_count=new_count,
                message="Reproducción registrada y contador incrementado exitosamente.",
            )

    @staticmethod
    def get_top_metrics(limit: int = 10) -> list[TopSongMetric]:
        with get_db_connection() as conn:
            rows = conn.execute(
                """
                SELECT 
                    s.id AS song_id,
                    s.title,
                    s.artist,
                    s.album,
                    COALESCE(m.play_count, 0) AS play_count,
                    m.last_played_at
                FROM songs s
                LEFT JOIN song_metrics m ON s.id = m.song_id
                ORDER BY play_count DESC, s.title ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [TopSongMetric(**dict(r)) for r in rows]

    @staticmethod
    def get_song_metric(song_id: int) -> TopSongMetric | None:
        with get_db_connection() as conn:
            row = conn.execute(
                """
                SELECT 
                    s.id AS song_id,
                    s.title,
                    s.artist,
                    s.album,
                    COALESCE(m.play_count, 0) AS play_count,
                    m.last_played_at
                FROM songs s
                LEFT JOIN song_metrics m ON s.id = m.song_id
                WHERE s.id = ?
                """,
                (song_id,),
            ).fetchone()
            if not row:
                return None
            return TopSongMetric(**dict(row))
