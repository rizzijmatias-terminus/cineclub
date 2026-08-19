#!/usr/bin/env python3
"""Parsea la nota de Keep a JSON.

    python seed/parsear.py seed/lista.raw.txt > seed/titulos.json

No toca TMDB: eso es el paso siguiente. Lo único que hace es entender la
estructura de la nota (encabezados de sección, "Título (Año)", episodios) y
avisar de cualquier línea que no haya podido clasificar, para que nada se
pierda en silencio.
"""
import json
import re
import sys
import unicodedata

# El emoji no alcanza para identificar la sección: 🎭 aparece en Drama y en
# Comedia. Se matchea por el texto del encabezado.
SECCIONES = [
    ("Drama",           "drama",    "pelicula"),
    ("Suspenso",        "suspenso", "pelicula"),
    ("Terror",          "terror",   "pelicula"),
    ("Ciencia ficción", "scifi",    "pelicula"),
    ("Aventura",        "aventura", "pelicula"),
    ("Comedia",         "comedia",  "pelicula"),
    ("Series",          "serie",    "serie"),
    ("Episodios",       "serie",    "episodio"),   # misma categoría, distinto tipo
]

RE_TITULO   = re.compile(r"^(?P<titulo>.+?)\s*\((?P<anio>\d{4})\)\s*$")
RE_EPISODIO = re.compile(
    r"^(?P<serie>.+?)\s*,\s*T(?P<temporada>\d{1,2})E(?P<episodio>\d{1,2})\s*$"
)
RE_SEPARADOR = re.compile(r"^[_\s]+$")
# "Películas" es el título del documento, no una sección
RE_IGNORAR = re.compile(r"^(Películas)\s*$", re.IGNORECASE)


def es_encabezado(linea):
    """Un encabezado arranca con un emoji (categoría Symbol/Other)."""
    if not linea:
        return None
    if unicodedata.category(linea[0]) not in ("So", "Sk"):
        return None
    for aguja, slug, tipo in SECCIONES:
        if aguja.lower() in linea.lower():
            return slug, tipo, linea
    return "?", "?", linea      # encabezado no reconocido: se reporta


def parsear(texto):
    titulos, sin_clasificar = [], []
    genero = tipo = None

    for nro, cruda in enumerate(texto.splitlines(), 1):
        linea = cruda.strip()
        if not linea or RE_SEPARADOR.match(linea) or RE_IGNORAR.match(linea):
            continue

        cabecera = es_encabezado(linea)
        if cabecera:
            genero, tipo, etiqueta = cabecera
            if genero == "?":
                sin_clasificar.append((nro, linea, "encabezado desconocido"))
            continue

        m = RE_TITULO.match(linea)
        if not m:
            sin_clasificar.append((nro, linea, "no matchea 'Título (Año)'"))
            continue
        if genero is None:
            sin_clasificar.append((nro, linea, "título antes de cualquier sección"))
            continue

        titulo, anio = m.group("titulo").strip(), int(m.group("anio"))
        item = {"titulo": titulo, "anio": anio, "genero": genero, "tipo": tipo}

        if tipo == "episodio":
            ep = RE_EPISODIO.match(titulo)
            if ep:
                item["serie"] = ep.group("serie").strip()
                item["temporada"] = int(ep.group("temporada"))
                item["episodio"] = int(ep.group("episodio"))
            else:
                sin_clasificar.append(
                    (nro, linea, "episodio sin patrón 'Serie, TxxExx'")
                )
        titulos.append(item)

    return titulos, sin_clasificar


def main():
    ruta = sys.argv[1] if len(sys.argv) > 1 else "seed/lista.raw.txt"
    with open(ruta, encoding="utf-8") as fh:
        titulos, sin_clasificar = parsear(fh.read())

    print(json.dumps(titulos, ensure_ascii=False, indent=2))

    # el informe va a stderr para no ensuciar el JSON
    resumen = {}
    for t in titulos:
        clave = f"{t['genero']}/{t['tipo']}"
        resumen[clave] = resumen.get(clave, 0) + 1
    print(f"\n{len(titulos)} títulos", file=sys.stderr)
    for clave, n in sorted(resumen.items()):
        print(f"  {clave:<20} {n:>3}", file=sys.stderr)
    if sin_clasificar:
        print(f"\n{len(sin_clasificar)} líneas SIN CLASIFICAR:", file=sys.stderr)
        for nro, linea, motivo in sin_clasificar:
            print(f"  línea {nro}: {linea!r} — {motivo}", file=sys.stderr)
    else:
        print("\nsin líneas huérfanas", file=sys.stderr)


if __name__ == "__main__":
    main()
