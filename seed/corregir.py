#!/usr/bin/env python3
"""Corrige el tmdb_id de un título y deja que se vuelva a enriquecer.

    python3 seed/corregir.py "Memories of Murder" movie 11423
    python3 seed/resolver_tmdb.py      # completa dirección, poster y sinopsis

Cambiar el id a mano en el JSON no alcanza: los campos viejos quedan pegados
del match anterior. Esto los borra para que resolver_tmdb.py los rehaga.
"""
import json
import sys

RUTA = "seed/titulos.json"
DERIVADOS = ("titulo_original", "poster_path", "sinopsis", "director")


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    titulo, tipo, tmdb_id = sys.argv[1], sys.argv[2], int(sys.argv[3])
    if tipo not in ("movie", "tv"):
        sys.exit("el tipo tiene que ser 'movie' o 'tv'")

    d = json.load(open(RUTA, encoding="utf-8"))
    encontrados = [t for t in d if t["titulo"].lower() == titulo.lower()]
    if not encontrados:
        parecidos = [t["titulo"] for t in d if titulo.lower() in t["titulo"].lower()]
        sys.exit(f"no encontré {titulo!r}." +
                 (f" ¿Quisiste decir? {', '.join(parecidos)}" if parecidos else ""))
    if len(encontrados) > 1:
        sys.exit(f"{titulo!r} aparece {len(encontrados)} veces, desambiguá a mano")

    t = encontrados[0]
    antes = f"{t.get('tmdb_tipo')}/{t.get('tmdb_id')}"
    t["tmdb_tipo"], t["tmdb_id"] = tipo, tmdb_id
    for campo in DERIVADOS:
        t.pop(campo, None)
    t.pop("revisar", None)
    t.pop("candidatos", None)

    with open(RUTA, "w", encoding="utf-8") as fh:
        json.dump(d, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"{t['titulo']} ({t['anio']}): {antes} → {tipo}/{tmdb_id}")
    print("campos derivados borrados. Corré resolver_tmdb.py para rehacerlos.")


if __name__ == "__main__":
    main()
