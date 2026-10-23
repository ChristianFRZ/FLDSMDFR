-- FLDSMDFR Esquema Relacional del Monolito
-- Base de datos centralizada con módulos desacoplados lógicamente

PRAGMA foreign_keys = ON;

-- Módulo de Usuarios
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Módulo de Catálogo
CREATE TABLE IF NOT EXISTS songs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    artist TEXT NOT NULL,
    album TEXT NOT NULL DEFAULT 'Single',
    duration_seconds INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    mime_type TEXT NOT NULL DEFAULT 'audio/wav',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Módulo de Playlists
CREATE TABLE IF NOT EXISTS playlists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS playlist_songs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    playlist_id INTEGER NOT NULL,
    song_id INTEGER NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
    FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE,
    UNIQUE (playlist_id, song_id)
);

-- Módulo de Reproducciones y Métricas
-- playback_id actúa como clave de idempotencia garantizada por UUID
CREATE TABLE IF NOT EXISTS playbacks (
    playback_id TEXT PRIMARY KEY,
    song_id INTEGER NOT NULL,
    user_id INTEGER,
    played_duration REAL NOT NULL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Agregación sincrónica de contadores
CREATE TABLE IF NOT EXISTS song_metrics (
    song_id INTEGER PRIMARY KEY,
    play_count INTEGER NOT NULL DEFAULT 0,
    last_played_at TIMESTAMP,
    FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE
);

-- Índices para optimizar consultas de latencia baja (<200ms)
CREATE INDEX IF NOT EXISTS idx_songs_title ON songs(title);
CREATE INDEX IF NOT EXISTS idx_songs_artist ON songs(artist);
CREATE INDEX IF NOT EXISTS idx_playlists_user ON playlists(user_id);
CREATE INDEX IF NOT EXISTS idx_playlist_songs_playlist ON playlist_songs(playlist_id);
CREATE INDEX IF NOT EXISTS idx_metrics_count ON song_metrics(play_count DESC);
