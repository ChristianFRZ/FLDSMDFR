"""Actividad simulada: pistas de Compositores, casetes, playlists y reproducciones."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from random import Random
from uuid import UUID

from seed import internal
from seed.audio import ensure_tones


@dataclass(frozen=True)
class DemoTrack:
    title: str
    genre: str
    audio_path: str
    duration: float
    status: str
    publish_at: datetime | None
    published_at: datetime | None


@dataclass(frozen=True)
class DemoComposer:
    user_id: UUID
    name: str
    bio: str
    tracks: list[DemoTrack] = field(default_factory=list)


@dataclass(frozen=True)
class DemoPlay:
    user_id: UUID
    song_id: UUID
    listened_seconds: int
    started_at: datetime


@dataclass(frozen=True)
class DemoPlaylist:
    owner_id: UUID
    name: str
    is_public: bool
    song_ids: list[UUID]


@dataclass(frozen=True)
class DemoTapeTrack:
    song_id: UUID
    added_by: UUID
    dedication: str | None


@dataclass(frozen=True)
class DemoTape:
    creator_id: UUID
    title: str
    color: str
    member_ids: list[UUID]
    tracks: list[DemoTapeTrack]


@dataclass(frozen=True)
class Song:
    id: UUID
    artist_id: UUID
    duration: float
    source: str


ARTISTS = (
    "Los Carretes", "Lado Z", "Neón de Barrio", "Ruido Rosa", "Bruma Norte", "Casa de Tonos",
    "Domingo Eterno", "Eco Verde", "Papel Rasgado", "Sábado 84", "Cinta Vieja", "Marea Alta",
)
TITLES = (
    "Luz de carretera", "Último camión", "Azotea", "Cuarto oscuro", "Lunes otra vez", "Mapa roto", "Café frío",
    "Ventana abierta", "Sin batería", "Regreso largo", "Canción para nadie", "Fin de semana", "Radio apagada", "Polvo",
)
GENRES = ("rock", "pop", "electronic", "jazz", "folk")
TAPE_TITLES = (
    "Viaje a Oaxaca", "Para no dormir", "Domingo lento", "Cumple de Nora", "Mudanza", "Noche de estudio",
    "Lado triste", "Volver a casa", "Verano 2026", "Para Lucía", "Road trip", "Sobremesa",
)
PLAYLIST_TITLES = ("Para correr", "Para cocinar", "Concentración", "Mañanas", "Tarde lluviosa", "Fiesta", "Descanso", "Clásicos míos")
DEDICATIONS = (
    "Para que no te duermas manejando.", "Te acuerdas de esta?", "La pusimos mil veces ese verano.",
    "Sube el volumen, ya sabes por qué.", "Esta me hizo pensar en ti.", "Perdón por lo del otro día.",
)
COLORS = ("pink", "yellow", "teal", "cobalt")
# Más actividad al salir de clases y de noche, y más los fines de semana.
HOURS = (2, 1, 1, 1, 1, 2, 4, 7, 9, 9, 8, 9, 11, 10, 9, 9, 11, 14, 17, 20, 22, 19, 12, 5)
WEEKDAYS = (9, 9, 10, 10, 13, 16, 14)
LISTENED = ((0.12, 2), (0.45, 3), (0.8, 2), (1.0, 3))


async def create_catalog(sizes, accounts, rng: Random, now: datetime) -> None:
    tones = await ensure_tones(min(12, max(1, sizes.composers * sizes.tracks_per_composer)))
    composers = []
    for index, account in enumerate(accounts.composers):
        tracks = []
        for number in range(sizes.tracks_per_composer):
            path, duration = rng.choice(tones)
            scheduled = number == sizes.tracks_per_composer - 1
            published_at = None if scheduled else now - timedelta(days=rng.uniform(1, sizes.days))
            tracks.append(
                DemoTrack(
                    title=rng.choice(TITLES),
                    genre=rng.choice(GENRES),
                    audio_path=path,
                    duration=duration,
                    status="scheduled" if scheduled else "published",
                    publish_at=now + timedelta(days=rng.randint(30, 60)) if scheduled else None,
                    published_at=published_at,
                )
            )
        composers.append(DemoComposer(account.id, ARTISTS[index % len(ARTISTS)], "Proyecto ficticio de la demo.", tracks))
    await internal.catalog().post("/catalog", {"composers": composers})


def _weights(count: int) -> list[float]:
    """Pocas pistas concentran casi todo, como en cualquier catálogo."""
    return [1 / (rank + 1) ** 0.8 for rank in range(count)]


def _plays(sizes, people, songs, rng: Random, now: datetime) -> list[DemoPlay]:
    days = [now - timedelta(days=offset) for offset in range(sizes.days)]
    # Crece hacia hoy y respeta el patrón de la semana.
    day_weights = [WEEKDAYS[day.weekday()] * (1 + (sizes.days - i) / sizes.days) for i, day in enumerate(days)]
    picked_songs = rng.choices(songs, weights=_weights(len(songs)), k=sizes.plays)
    picked_days = rng.choices(days, weights=day_weights, k=sizes.plays)
    picked_hours = rng.choices(range(24), weights=HOURS, k=sizes.plays)
    fractions = rng.choices([f for f, _ in LISTENED], weights=[w for _, w in LISTENED], k=sizes.plays)
    plays = []
    for song, day, hour, fraction in zip(picked_songs, picked_days, picked_hours, fractions):
        person = rng.choice(people)
        started = day.replace(hour=hour, minute=rng.randrange(60), second=rng.randrange(60), microsecond=0)
        started = min(max(started, person.created_at + timedelta(hours=1)), now - timedelta(hours=1))
        # Al final de la pista se reporta el segundo entero siguiente, igual que el reproductor.
        listened = int(song.duration * fraction) + (1 if fraction == 1.0 else 0)
        plays.append(DemoPlay(person.id, song.id, listened, started))
    return sorted(plays, key=lambda play: play.started_at)


async def create_activity(sizes, accounts, rng: Random, now: datetime) -> dict[str, int]:
    rows = await internal.catalog().get("/catalog/listenable", limit=sizes.song_pool)
    songs = [Song(UUID(row["id"]), UUID(row["artist_id"]), row["duration"], row["source"]) for row in rows]
    if not songs:
        raise RuntimeError("El catálogo no tiene pistas escuchables: importa Jamendo antes (python -m seed catalog).")
    people = accounts.listeners + accounts.composers
    ids = [song.id for song in songs]

    tapes = []
    for index in range(sizes.tapes):
        members = rng.sample(people, k=min(len(people), rng.randint(2, 5)))
        chosen = rng.sample(ids, k=min(len(ids), rng.randint(3, 10)))
        tracks = [
            DemoTapeTrack(song, rng.choice(members).id, rng.choice(DEDICATIONS) if rng.random() < 0.5 else None)
            for song in chosen
        ]
        # La primera dedicatoria asegura que el casete de ejemplo la muestre.
        tracks[0] = DemoTapeTrack(tracks[0].song_id, tracks[0].added_by, rng.choice(DEDICATIONS))
        tapes.append(
            DemoTape(members[0].id, TAPE_TITLES[index % len(TAPE_TITLES)], COLORS[index % len(COLORS)], [m.id for m in members], tracks)
        )
    playlists = [
        DemoPlaylist(
            rng.choice(people).id,
            PLAYLIST_TITLES[index % len(PLAYLIST_TITLES)],
            rng.random() < 0.4,
            rng.sample(ids, k=min(len(ids), rng.randint(4, 15))),
        )
        for index in range(sizes.playlists)
    ]
    await internal.users().post("/playlists", {"playlists": playlists})

    favorites = {(person.id, song) for person in people for song in rng.sample(ids, k=min(len(ids), rng.randint(2, 8)))}
    local_artists = sorted({song.artist_id for song in songs if song.source == "local"}, key=str)
    follows = {(person.id, rng.choice(local_artists)) for person in people for _ in range(2)} if local_artists else set()
    await internal.users().post(
        "/social", {"tapes": tapes, "favorites": sorted(favorites, key=str), "follows": sorted(follows, key=str)}
    )

    plays = _plays(sizes, people, songs, rng, now)
    await internal.playback().post("/playbacks", {"plays": plays, "duplicates": max(1, sizes.plays // 100)})
    return {"tapes": len(tapes), "playlists": sizes.playlists, "plays": len(plays)}
