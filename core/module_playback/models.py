from pydantic import BaseModel, Field


class PlaybackEventCreate(BaseModel):
    playback_id: str = Field(..., description="UUID único para idempotencia")
    song_id: int = Field(..., description="Identificador de la canción reproducida")
    user_id: int | None = Field(default=None, description="Identificador opcional del oyente")
    played_duration: float = Field(..., ge=0, description="Duración en segundos de escucha")


class PlaybackEventResponse(BaseModel):
    playback_id: str
    song_id: int
    counted: bool
    current_play_count: int
    message: str


class TopSongMetric(BaseModel):
    song_id: int
    title: str
    artist: str
    album: str
    play_count: int
    last_played_at: str | None
