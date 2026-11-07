"""Catálogo real de Jamendo. Reutiliza el trabajo de importación del Administrador."""
from app.modules.catalog.public import demo_import_done, import_demo_catalog


async def import_catalog(sizes) -> str:
    # Un género puede traer menos de lo pedido; una importación muy corta se repite.
    minimum = int(len(sizes.genres) * sizes.per_genre * 0.9)
    if await demo_import_done(list(sizes.genres), minimum):
        return "Catálogo de Jamendo: ya importado, sin peticiones nuevas."
    status, imported, error = await import_demo_catalog(list(sizes.genres), sizes.per_genre)
    if status != "done":
        raise RuntimeError(f"La importación se detuvo tras {imported} pistas: {error}")
    return f"Catálogo de Jamendo: {imported} pistas importadas."
