"""Pruebas sobre meloxo.pptx: fuentes, colores, tamaños, pistas, márgenes y holguras."""
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
ESPERADAS = 2

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


def test_pista_sin_solape(pres):
    for n, lam in enumerate(pres.slides, 1):
        todas = list(formas(lam.shapes))
        p = next(f for f in todas if f.name == "pista")
        a = _rect(p)
        for f in todas:
            if f is p or f.name in EXCLUIDAS_PISTA or f.shape_type == MSO_SHAPE_TYPE.GROUP or es_fondo(f):
                continue
            b = _rect(f)
            cruza = a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]
            assert not cruza, f"lámina {n}: pista se cruza con {f.name}"


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


def test_holgura_titulos(pres):
    malas = []
    for n, lam in enumerate(pres.slides, 1):
        for f in formas(lam.shapes):
            if f.name != "titulo":
                continue
            tam = max(r.font.size.pt for p in f.text_frame.paragraphs for r in p.runs)
            largo = len(f.text_frame.text)
            necesario = largo * 0.62 * tam / 72
            if necesario > 0.9 * pulgadas(f.width):
                malas.append((n, largo, tam, round(necesario, 2), round(pulgadas(f.width), 2)))
    assert not malas, malas


def test_sin_unbounded():
    with zipfile.ZipFile(MELOXO_PPTX) as z:
        for nombre in z.namelist():
            if nombre.endswith((".xml", ".rels")):
                assert b"Unbounded" not in z.read(nombre), nombre
