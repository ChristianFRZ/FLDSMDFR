"""Dos miembros agregan a la vez la pista 12: una entra y la otra recibe 409."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from common import Api, check, error_code, new_user, published_songs, run

ROUNDS = 5  # una carrera sola puede salir bien por suerte


def race(owner: Api, member: Api, songs: list[dict], number: int) -> None:
    tape = owner.ok("POST", "/api/tapes", {"title": f"Escenario 5, ronda {number}"})
    path = f"/api/tapes/{tape['id']}"
    try:
        limit = owner.ok("GET", path)["max_tracks"]
        for song in songs[: limit - 1]:
            owner.ok("POST", f"{path}/tracks", {"song_id": song["id"]})
        invite = owner.ok("POST", f"{path}/invites", {})
        member.ok("POST", f"/api/tapes/join/{invite['token']}")

        barrier = Barrier(2)

        def add(api: Api, song: dict) -> tuple[int, dict]:
            barrier.wait()
            return api.call("POST", f"{path}/tracks", {"song_id": song["id"]})

        with ThreadPoolExecutor(2) as pool:
            first = pool.submit(add, owner, songs[limit - 1])
            second = pool.submit(add, member, songs[limit])
            results = sorted([first.result(), second.result()], key=lambda r: r[0])

        check([status for status, _ in results] == [201, 409], f"ronda {number}: una 201 y una 409")
        check(error_code(results[1][1]) == "tape_full", f"ronda {number}: el rechazo dice tape_full")
        positions = [t["position"] for t in owner.ok("GET", path)["tracks"]]
        check(positions == list(range(1, limit + 1)), f"ronda {number}: {limit} pistas, sin posiciones repetidas")
    finally:
        owner.ok("DELETE", path)


def scenario() -> None:
    owner, _ = new_user("casete-a")
    member, _ = new_user("casete-b")
    songs = published_songs(owner, 13)
    for number in range(1, ROUNDS + 1):
        race(owner, member, songs, number)


if __name__ == "__main__":
    run("Escenario 5: casete lleno", scenario)
