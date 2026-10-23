from core.module_catalog.models import SongCreate, SongResponse
from db.connection import get_db_connection


class CatalogService:

    @staticmethod
    def list_songs(query: str | None = None) -> list[SongResponse]:
        with get_db_connection() as conn:
            if query and query.strip():
                pattern = f"%{query.strip()}%"
                rows = conn.execute(
                    """
                    SELECT * FROM songs
                    WHERE title LIKE ? OR artist LIKE ? OR album LIKE ?
                    ORDER BY id ASC
                    """,
                    (pattern, pattern, pattern),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM songs ORDER BY id ASC").fetchall()

            return [SongResponse(**dict(r)) for r in rows]

    @staticmethod
    def get_song_by_id(song_id: int) -> SongResponse | None:
        with get_db_connection() as conn:
            row = conn.execute("SELECT * FROM songs WHERE id = ?", (song_id,)).fetchone()
            if not row:
                return None
            return SongResponse(**dict(row))

    @staticmethod
    def create_song(data: SongCreate) -> SongResponse:
        with get_db_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO songs (title, artist, album, duration_seconds, file_path, mime_type)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    data.title.strip(),
                    data.artist.strip(),
                    data.album.strip(),
                    data.duration_seconds,
                    data.file_path.strip(),
                    data.mime_type.strip(),
                ),
            )
            song_id = cur.lastrowid
            # Inicializar contador de reproducciones en el módulo de métricas
            conn.execute(
                """
                INSERT OR IGNORE INTO song_metrics (song_id, play_count)
                VALUES (?, 0)
                """,
                (song_id,),
            )
            row = conn.execute("SELECT * FROM songs WHERE id = ?", (song_id,)).fetchone()
            return SongResponse(**dict(row))
