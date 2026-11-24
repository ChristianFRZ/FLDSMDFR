"""Catálogo real de Jamendo, importado por `catalog-streaming`."""
from seed import internal


async def import_catalog(sizes) -> str:
    # Un género puede traer menos de lo pedido; una importación muy corta se repite.
    minimum = int(len(sizes.genres) * sizes.per_genre * 0.9)
    done = await internal.catalog().get("/catalog/import-done", genres=",".join(sizes.genres), minimum=minimum)
    if done["done"]:
        return "Catálogo de Jamendo: ya importado, sin peticiones nuevas."
    result = await internal.catalog().post("/catalog/import", {"genres": list(sizes.genres), "per_genre": sizes.per_genre})
    if result["status"] != "done":
        raise RuntimeError(f"La importación se detuvo tras {result['imported']} pistas: {result['error']}")
    return f"Catálogo de Jamendo: {result['imported']} pistas importadas."
