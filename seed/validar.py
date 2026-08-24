#!/usr/bin/env python3
"""Chequea seed/titulos.json contra las restricciones del modelo.

    python3 seed/validar.py

Corre esto antes de cargar a la base: son las mismas reglas que va a imponer
Postgres, pero con mensajes que se entienden.
"""
import collections
import json
import re
import sys

RUTA = "seed/titulos.json"
CRUDA = "seed/lista.raw.txt"
GENEROS = {"drama", "suspenso", "terror", "scifi", "aventura", "comedia", "serie"}


def main():
    d = json.load(open(RUTA, encoding="utf-8"))
    errores, avisos = [], []

    # --- restricciones que impone el esquema ---
    for t in d:
        n = f"{t['titulo']} ({t['anio']})"
        if (t.get("tmdb_tipo") is None) != (t.get("tmdb_id") is None):
            errores.append(f"{n}: tmdb_tipo y tmdb_id deben ser ambos nulos o ambos no")
        if t.get("tmdb_tipo") not in (None, "movie", "tv"):
            errores.append(f"{n}: tmdb_tipo inválido {t.get('tmdb_tipo')!r}")
        if t["tipo"] not in ("pelicula", "serie", "episodio"):
            errores.append(f"{n}: tipo inválido {t['tipo']!r}")
        if t["genero"] not in GENEROS:
            errores.append(f"{n}: género desconocido {t['genero']!r}")
        if t["tipo"] == "episodio" and not (t.get("temporada") and t.get("episodio")):
            errores.append(f"{n}: episodio sin temporada/episodio")
        if t["tipo"] != "episodio" and (t.get("temporada") or t.get("episodio")):
            errores.append(f"{n}: no es episodio pero tiene temporada/episodio")
        if t["tipo"] == "pelicula" and t.get("tmdb_tipo") == "tv":
            errores.append(f"{n}: es película pero apunta a tv/")
        if t["tipo"] in ("serie", "episodio") and t.get("tmdb_tipo") == "movie":
            errores.append(f"{n}: es {t['tipo']} pero apunta a movie/")

    # --- el índice único de titulos ---
    clave = lambda t: (t.get("tmdb_tipo"), t.get("tmdb_id"),
                       t.get("temporada"), t.get("episodio"))
    for k, n in collections.Counter(clave(t) for t in d).items():
        if n > 1 and k[1] is not None:
            choques = [f"{t['titulo']} ({t['anio']})" for t in d if clave(t) == k]
            errores.append(f"clave duplicada {k}: " + " / ".join(choques))

    # --- sin errores pero vale mirarlos ---
    for t in d:
        if t.get("revisar"):
            errores.append(f"{t['titulo']}: quedó marcado 'revisar'")
        if t.get("tmdb_id") and not t.get("poster_path"):
            avisos.append(f"{t['titulo']}: sin enriquecer, volvé a correr resolver_tmdb.py")
        elif not t.get("director"):
            avisos.append(f"{t['titulo']}: sin dirección (puede ser que TMDB no la tenga)")

    # --- ¿sigue en sincronía con la nota? ---
    try:
        cruda = open(CRUDA, encoding="utf-8").read()
        en_nota = len(re.findall(r"^.+\(\d{4}\)\s*$", cruda, re.M))
        if en_nota != len(d):
            avisos.append(f"la nota tiene {en_nota} títulos y el JSON {len(d)}: se separaron")
    except FileNotFoundError:
        pass

    print(f"{len(d)} títulos")
    for clave_, n in sorted(collections.Counter(
            f"{t['genero']}/{t['tipo']}" for t in d).items()):
        print(f"  {clave_:<20} {n:>3}")
    if avisos:
        print("\nAVISOS")
        for a in avisos:
            print(f"  · {a}")
    if errores:
        print("\nERRORES")
        for e in errores:
            print(f"  ✗ {e}")
        sys.exit(1)
    print("\nSin errores: listo para cargar.")


if __name__ == "__main__":
    main()
