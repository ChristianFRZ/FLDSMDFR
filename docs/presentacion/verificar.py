"""Pruebas sobre meloxo.pptx: fuentes, colores, tamaños, pistas, márgenes y holguras."""
import math
import os
import re
import zipfile

import pytest
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.util import Emu

MELOXO_PPTX = os.environ.get(
    "MELOXO_PPTX", os.path.join(os.path.dirname(os.path.abspath(__file__)), "meloxo.pptx")
)
ESPERADAS = 8

FUENTES = {"Montserrat", "Roboto", "Caveat"}
PALETA = {"141317", "201F25", "4A4852", "F4F1EA", "BDB9AF", "FF3D8B", "00D1BE", "FFD233", "4A5CFF"}
EXCLUIDAS_PISTA = {"pista-papel", "pista-cinta"}


def pulgadas(v):
    return Emu(v).inches


@pytest.fixture(scope="module")
def pres():
    return Presentation(MELOXO_PPTX)


def formas(coleccion):
    for f in coleccion:
        if f.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield f
            yield from formas(f.shapes)
        else:
            yield f


def runs(pres):
    for n, lam in enumerate(pres.slides, 1):
        for f in formas(lam.shapes):
            if f.has_text_frame:
                for p in f.text_frame.paragraphs:
                    for r in p.runs:
                        yield n, f, r


def es_fondo(f):
    return f.shape_type == MSO_SHAPE_TYPE.PICTURE and pulgadas(f.width) >= 9.99 and pulgadas(f.height) >= 5.6


def test_numero_laminas(pres):
    assert len(pres.slides) == ESPERADAS


def test_fuentes_permitidas(pres):
    malas = [(n, f.name, r.font.name) for n, f, r in runs(pres) if r.font.name not in FUENTES]
    assert not malas, malas


def _color(fmt):
    try:
        if fmt.type is not None and fmt.fore_color.type is not None:
            return str(fmt.fore_color.rgb)
    except (AttributeError, TypeError):
        pass
    return None


def test_colores_permitidos(pres):
    malos = []
    for n, lam in enumerate(pres.slides, 1):
        for f in formas(lam.shapes):
            if f.shape_type == MSO_SHAPE_TYPE.PICTURE or f.shape_type == MSO_SHAPE_TYPE.GROUP:
                continue
            if f.shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE or f.shape_type == MSO_SHAPE_TYPE.TEXT_BOX:
                c = _color(f.fill)
                if c and c not in PALETA:
                    malos.append((n, f.name, "relleno", c))
            if f.has_text_frame:
                for p in f.text_frame.paragraphs:
                    for r in p.runs:
                        c = _color(r.font.color)
                        if c and c not in PALETA:
                            malos.append((n, f.name, "texto", c))
    assert not malos, malos


def test_tamanos_minimos(pres):
    malos = []
    for n, f, r in runs(pres):
        pt = r.font.size.pt if r.font.size else None
        if pt is None:
            malos.append((n, f.name, "sin tamaño"))
            continue
        minimo = {"Roboto": 12, "Caveat": 14}.get(r.font.name, 0)
        if f.name == "titulo":
            minimo = 30
        if pt < minimo:
            malos.append((n, f.name, r.font.name, pt, minimo))
    assert not malos, malos


def test_cada_lamina_tiene_pista_y_notas(pres):
    for n, lam in enumerate(pres.slides, 1):
        pistas = [f for f in formas(lam.shapes) if f.name == "pista"]
        assert len(pistas) == 1, f"lámina {n}: {len(pistas)} formas pista"
        assert re.match(r"^Lado [AB] · \d\d — ", pistas[0].text_frame.text.replace("\n", " ")), f"lámina {n}: formato de pista"
        assert lam.has_notes_slide, f"lámina {n}: sin notas"
        assert len(lam.notes_slide.notes_text_frame.text) >= 250, f"lámina {n}: notas cortas"


def _rect(f):
    return (f.left, f.top, f.left + f.width, f.top + f.height)


def _envolvente(f):
    """Caja envolvente del rectángulo rotado (en EMU)."""
    x0, y0, x1, y1 = _rect(f)
    ang = math.radians(getattr(f, "rotation", 0) or 0)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    w, h = f.width, f.height
    ew = abs(w * math.cos(ang)) + abs(h * math.sin(ang))
    eh = abs(w * math.sin(ang)) + abs(h * math.cos(ang))
    return (cx - ew / 2, cy - eh / 2, cx + ew / 2, cy + eh / 2)


def _cruza(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def test_pista_sin_solape(pres):
    """La pista, su papel y su cinta (con rotación) no se cruzan con ninguna otra forma."""
    for n, lam in enumerate(pres.slides, 1):
        todas = list(formas(lam.shapes))
        propias = [f for f in todas if f.name == "pista" or f.name in EXCLUIDAS_PISTA]
        for p in propias:
            a = _envolvente(p)
            for f in todas:
                if f in propias or f.shape_type == MSO_SHAPE_TYPE.GROUP or es_fondo(f):
                    continue
                assert not _cruza(a, _envolvente(f)), f"lámina {n}: {p.name} se cruza con {f.name}"


def test_margenes(pres):
    malas = []
    for n, lam in enumerate(pres.slides, 1):
        for f in formas(lam.shapes):
            if es_fondo(f) or f.shape_type == MSO_SHAPE_TYPE.GROUP:
                continue
            x0, y0, x1, y1 = (pulgadas(v) for v in _rect(f))
            eps = 0.005
            if x0 < 0.4 - eps or y0 < 0.3 - eps or x1 > 9.6 + eps or y1 > 5.35 + eps:
                malas.append((n, f.name, round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)))
    assert not malas, malas


FUENTE_MONTSERRAT = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".qa", "fonts", "Montserrat-VF.ttf")


def _ancho_texto(texto, pt):
    """Ancho real en pulgadas de texto en Montserrat Bold a pt puntos (1 px = 1 pt a 72 dpi)."""
    from PIL import ImageFont
    fuente = ImageFont.truetype(FUENTE_MONTSERRAT, size=1000)
    try:
        fuente.set_variation_by_name("Bold")
    except (AttributeError, OSError):
        pass
    return fuente.getlength(texto) / 1000 * pt / 72


def test_holgura_titulos(pres):
    if not os.path.exists(FUENTE_MONTSERRAT):
        pytest.skip(f"falta la fuente {FUENTE_MONTSERRAT}: copia Montserrat a .qa/fonts")
    malas = []
    for n, lam in enumerate(pres.slides, 1):
        for f in formas(lam.shapes):
            if f.name != "titulo":
                continue
            tam = max(r.font.size.pt for p in f.text_frame.paragraphs for r in p.runs)
            ancho = _ancho_texto(f.text_frame.text, tam)
            if ancho > 0.9 * pulgadas(f.width):
                malas.append((n, f.text_frame.text, tam, round(ancho, 2), round(pulgadas(f.width), 2)))
    assert not malas, malas


def test_sin_unbounded():
    with zipfile.ZipFile(MELOXO_PPTX) as z:
        for nombre in z.namelist():
            if nombre.endswith((".xml", ".rels")):
                assert b"Unbounded" not in z.read(nombre), nombre


def _textos(lam):
    return "\n".join(f.text_frame.text for f in formas(lam.shapes) if f.has_text_frame)


def test_textos_a1(pres):
    esperado = {2: ["monolito"], 3: ["12 pistas", "8 miembros", "140"],
                4: ["Oyente", "Compositor", "Administrador"], 5: ["Así se ve"]}
    for n, claves in esperado.items():
        t = _textos(pres.slides[n - 1])
        for c in claves:
            assert c in t, f"lámina {n}: falta {c!r}"
    video = [f for f in formas(pres.slides[4].shapes) if f.name == "video-demo"]
    assert len(video) == 1 and video[0].shape_type == MSO_SHAPE_TYPE.PICTURE
    for n in range(1, 6):
        pista = next(f for f in formas(pres.slides[n - 1].shapes) if f.name == "pista")
        assert pista.text_frame.text.startswith(f"Lado A · 0{n}"), f"lámina {n}: pista"


def test_textos_a2(pres):
    t6 = _textos(pres.slides[5])
    for nombre in ["edge", "gateway-auth", "users-playlists", "playback-metrics", "postgres", "redis-cache",
                   "HTTP /internal", "Redis Streams", "Python 3.12"]:
        assert nombre in t6, f"lámina 6: falta {nombre!r}"
    assert "redis" in t6.replace("redis-cache", ""), "lámina 6: falta redis"
    cajas = [f for f in formas(pres.slides[5].shapes) if f.has_text_frame and f.text_frame.text.startswith("catalog-streaming")]
    assert len(cajas) == 2, f"lámina 6: {len(cajas)} cajas catalog-streaming, se esperaban 2"
    t7 = _textos(pres.slides[6])
    for c in ["12 / 26", "36 / 71", "31 / 55", "27 / 66"]:
        assert c in t7, f"lámina 7: falta {c!r}"
    assert "0 / 293" in _textos(pres.slides[7]), "lámina 8: falta '0 / 293'"
    for n in range(6, 9):
        pista = next(f for f in formas(pres.slides[n - 1].shapes) if f.name == "pista")
        assert pista.text_frame.text.startswith(f"Lado A · 0{n}"), f"lámina {n}: pista"
