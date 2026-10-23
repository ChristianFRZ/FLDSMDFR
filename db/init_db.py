import sqlite3
from pathlib import Path

from core.config import BASE_DIR, DB_PATH, MEDIA_DIR
from db.connection import get_db_connection

SCHEMA_PATH = BASE_DIR / "db" / "schema.sql"


def init_database(db_path: Path | str = DB_PATH, seed: bool = True):
    """Ejecuta el schema.sql y siembra datos iniciales de prueba si está vacía."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    with get_db_connection(db_path) as conn:
        with open(SCHEMA_PATH, encoding="utf-8") as f:
            conn.executescript(f.read())

        if seed:
            seed_data(conn)


def seed_data(conn: sqlite3.Connection):
    """Inserta datos de prueba (usuarios, canciones y playlists) si no existen."""
    # 1. Sembrado de Usuarios (Equipo FLDSMDFR)
    users_data = [
        ("christian", "christian@fldsmdfr.unam.mx", "Christian Franco"),
        ("miriam", "miriam@fldsmdfr.unam.mx", "Miriam López"),
        ("erick", "erick@fldsmdfr.unam.mx", "Erick Nava"),
        ("brent", "brent@fldsmdfr.unam.mx", "Brent Pérez"),
    ]
    for username, email, full_name in users_data:
        conn.execute(
            """
            INSERT OR IGNORE INTO users (username, email, full_name)
            VALUES (?, ?, ?)
            """,
            (username, email, full_name),
        )

    # 2. Sembrado de Canciones demo
    songs_data = [
        (
            "Cosmic Lofi",
            "FLDSMDFR Beats",
            "Synthesizer Dreams",
            20,
            str(MEDIA_DIR / "cosmic_lofi.wav"),
            "audio/wav",
        ),
        (
            "Neon Cyberpunk",
            "RetroWave Core",
            "Night Runner",
            22,
            str(MEDIA_DIR / "neon_cyberpunk.wav"),
            "audio/wav",
        ),
        (
            "Chillwave Beats",
            "Lo-Fi Flow",
            "Study Session Vol. 1",
            18,
            str(MEDIA_DIR / "chillwave_beats.wav"),
            "audio/wav",
        ),
    ]

    for title, artist, album, duration, file_path, mime_type in songs_data:
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO songs (title, artist, album, duration_seconds, file_path, mime_type)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (title, artist, album, duration, file_path, mime_type),
        )
        # Si se insertó una nueva canción, inicializar su métrica en 0
        song_row = conn.execute(
            "SELECT id FROM songs WHERE title = ? AND artist = ?", (title, artist)
        ).fetchone()
        if song_row:
            conn.execute(
                """
                INSERT OR IGNORE INTO song_metrics (song_id, play_count)
                VALUES (?, 0)
                """,
                (song_row["id"],),
            )

    # 3. Sembrado de una Playlist inicial para el usuario 1 si no tiene ninguna
    user_row = conn.execute(
        "SELECT id FROM users WHERE username = 'christian'"
    ).fetchone()
    if user_row:
        user_id = user_row["id"]
        playlist_row = conn.execute(
            "SELECT id FROM playlists WHERE user_id = ? AND name = ?",
            (user_id, "Favoritas FLDSMDFR"),
        ).fetchone()
        if not playlist_row:
            cur = conn.execute(
                """
                INSERT INTO playlists (user_id, name, description)
                VALUES (?, ?, ?)
                """,
                (
                    user_id,
                    "Favoritas FLDSMDFR",
                    "Canciones recomendadas para programar sistemas distribuidos",
                ),
            )
            playlist_id = cur.lastrowid
            # Asociar canciones a la playlist
            all_songs = conn.execute("SELECT id FROM songs").fetchall()
            for s in all_songs[:2]:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO playlist_songs (playlist_id, song_id)
                    VALUES (?, ?)
                    """,
                    (playlist_id, s["id"]),
                )


if __name__ == "__main__":
    init_database()
    print("Base de datos inicializada correctamente.")
