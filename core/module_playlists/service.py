import sqlite3

from core.module_catalog.models import SongResponse
from core.module_playlists.models import (
    PlaylistCreate,
    PlaylistDetailResponse,
    PlaylistResponse,
)
from db.connection import get_db_connection


class PlaylistService:

    @staticmethod
    def create_playlist(data: PlaylistCreate) -> PlaylistResponse:
        with get_db_connection() as conn:
            # Validar que el usuario exista
            user = conn.execute(
                "SELECT id FROM users WHERE id = ?", (data.user_id,)
            ).fetchone()
            if not user:
                raise ValueError(f"El usuario con id {data.user_id} no existe.")

            cur = conn.execute(
                """
                INSERT INTO playlists (user_id, name, description)
                VALUES (?, ?, ?)
                """,
                (
                    data.user_id,
                    data.name.strip(),
                    data.description.strip() if data.description else None,
                ),
            )
            playlist_id = cur.lastrowid
            row = conn.execute(
                "SELECT * FROM playlists WHERE id = ?", (playlist_id,)
            ).fetchone()
            return PlaylistResponse(**dict(row))

    @staticmethod
    def add_song_to_playlist(playlist_id: int, song_id: int):
        with get_db_connection() as conn:
            # Validar que la playlist exista
            playlist = conn.execute(
                "SELECT id FROM playlists WHERE id = ?", (playlist_id,)
            ).fetchone()
            if not playlist:
                raise KeyError(f"La playlist con id {playlist_id} no existe.")

            # Validar que la canción exista
            song = conn.execute(
                "SELECT id FROM songs WHERE id = ?", (song_id,)
            ).fetchone()
            if not song:
                raise ValueError(f"La canción con id {song_id} no existe.")

            try:
                conn.execute(
                    """
                    INSERT INTO playlist_songs (playlist_id, song_id)
                    VALUES (?, ?)
                    """,
                    (playlist_id, song_id),
                )
            except sqlite3.IntegrityError:
                # Ya existe en la playlist, operación idempotente
                pass

    @staticmethod
    def get_playlist_details(playlist_id: int) -> PlaylistDetailResponse | None:
        with get_db_connection() as conn:
            playlist_row = conn.execute(
                "SELECT * FROM playlists WHERE id = ?", (playlist_id,)
            ).fetchone()
            if not playlist_row:
                return None

            # Consultar canciones asociadas optimizado mediante join con índice (<200ms)
            songs_rows = conn.execute(
                """
                SELECT s.id, s.title, s.artist, s.album, s.duration_seconds, s.file_path, s.mime_type, s.created_at
                FROM songs s
                INNER JOIN playlist_songs ps ON s.id = ps.song_id
                WHERE ps.playlist_id = ?
                ORDER BY ps.added_at ASC
                """,
                (playlist_id,),
            ).fetchall()

            songs = [SongResponse(**dict(r)) for r in songs_rows]
            return PlaylistDetailResponse(
                id=playlist_row["id"],
                user_id=playlist_row["user_id"],
                name=playlist_row["name"],
                description=playlist_row["description"],
                created_at=playlist_row["created_at"],
                songs=songs,
            )

    @staticmethod
    def list_playlists_by_user(user_id: int) -> list[PlaylistResponse]:
        with get_db_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM playlists WHERE user_id = ? ORDER BY id DESC",
                (user_id,),
            ).fetchall()
            return [PlaylistResponse(**dict(r)) for r in rows]

    @staticmethod
    def list_all_playlists() -> list[PlaylistResponse]:
        with get_db_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM playlists ORDER BY id DESC"
            ).fetchall()
            return [PlaylistResponse(**dict(r)) for r in rows]
