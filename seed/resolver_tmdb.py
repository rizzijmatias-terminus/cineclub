#!/usr/bin/env python3
"""Enriquece seed/titulos.json contra TMDB, en el lugar.

    export TMDB_API_KEY=...
    python seed/resolver_tmdb.py

Es idempotente: sólo toca los que todavía no tienen tmdb_id. Lo que no puede
resolver con confianza queda marcado con "revisar" y la lista de candidatos,
para elegir a mano. Nunca adivina en silencio.

Sin dependencias: sólo stdlib.
"""
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

API = "https://api.themoviedb.org/3"
CLAVE = os.environ.get("TMDB_API_KEY")
IDIOMA = "es-MX"
RUTA = "seed/titulos.json"


def pedir(camino, **params):
    params.update(api_key=CLAVE)
    url = f"{API}{camino}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.load(r)


def normalizar(s):
    """Para comparar títulos: sin acentos, sin puntuación, en minúsculas."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def anio_de(cadena):
    return int(cadena[:4]) if cadena and cadena[:4].isdigit() else None


def puntuar(item, titulo, anio, campo_fecha, campos_titulo):
    """Confianza de 0 a 100. Título exacto + año exacto = 100."""
    objetivo = normalizar(titulo)
    mejor = 0
    for campo in campos_titulo:
        cand = normalizar(item.get(campo, ""))
        if not cand:
            continue
        if cand == objetivo:
            mejor = max(mejor, 60)
        elif objetivo in cand or cand in objetivo:
            mejor = max(mejor, 40)
    delta = abs((anio_de(item.get(campo_fecha)) or 0) - anio)
    if delta == 0:
        mejor += 40
    elif delta <= 1:
        mejor += 30
    elif delta <= 3:
        mejor += 10
    return mejor


def buscar(tipo_tmdb, titulo, anio):
    campo_fecha = "release_date" if tipo_tmdb == "movie" else "first_air_date"
    campos = (["title", "original_title"] if tipo_tmdb == "movie"
              else ["name", "original_name"])
    vistos, resultados = set(), []
    # con año y sin año: el año filtra bien pero a veces TMDB lo tiene distinto
    for params in ({"year": anio} if tipo_tmdb == "movie"
                   else {"first_air_date_year": anio}), {}:
        datos = pedir(f"/search/{tipo_tmdb}", query=titulo, language=IDIOMA,
                      include_adult="false", **params)
        for item in datos.get("results", [])[:8]:
            if item["id"] in vistos:
                continue
            vistos.add(item["id"])
            item["_puntaje"] = puntuar(item, titulo, anio, campo_fecha, campos)
            resultados.append(item)
    return sorted(resultados, key=lambda x: -x["_puntaje"]), campo_fecha, campos


def director_de_pelicula(tmdb_id):
    creditos = pedir(f"/movie/{tmdb_id}/credits", language=IDIOMA)
    nombres = [c["name"] for c in creditos.get("crew", []) if c.get("job") == "Director"]
    return ", ".join(dict.fromkeys(nombres)) or None


def detalle(camino):
    """Trae el detalle, con fallback a inglés si la sinopsis en español está vacía."""
    d = pedir(camino, language=IDIOMA)
    if not d.get("overview"):
        en = pedir(camino, language="en-US")
        d["overview"] = en.get("overview") or ""
        d.setdefault("_poster_en", en.get("poster_path"))
    return d


def resolver(t):
    """Devuelve (campos, candidatos). Si campos es None, hay que revisar."""
    if t["tipo"] == "episodio":
        serie, temporada, episodio = t["serie"], t["temporada"], t["episodio"]
        ranking, campo_fecha, campos = buscar("tv", serie, t["anio"])
        if not ranking or ranking[0]["_puntaje"] < 60:
            return None, ranking[:4]
        tv = ranking[0]
        try:
            ep = detalle(f"/tv/{tv['id']}/season/{temporada}/episode/{episodio}")
        except Exception as e:
            return None, [{"error": f"episodio inexistente en TMDB: {e}"}] + ranking[:3]
        directores = [c["name"] for c in ep.get("crew", []) if c.get("job") == "Director"]
        return {
            "tmdb_tipo": "tv",
            "tmdb_id": tv["id"],
            "titulo_original": ep.get("name"),
            "poster_path": ep.get("still_path") or tv.get("poster_path"),
            "sinopsis": ep.get("overview") or None,
            "director": ", ".join(dict.fromkeys(directores)) or None,
        }, None

    tipo_tmdb = "movie" if t["tipo"] == "pelicula" else "tv"
    ranking, campo_fecha, campos = buscar(tipo_tmdb, t["titulo"], t["anio"])
    if not ranking:
        return None, []
    mejor = ranking[0]
    ambiguo = len(ranking) > 1 and ranking[1]["_puntaje"] == mejor["_puntaje"]
    if mejor["_puntaje"] < 90 or ambiguo:
        return None, ranking[:4]

    d = detalle(f"/{tipo_tmdb}/{mejor['id']}")
    if tipo_tmdb == "movie":
        director = director_de_pelicula(mejor["id"])
        original = d.get("original_title")
    else:
        director = ", ".join(p["name"] for p in d.get("created_by", [])) or None
        original = d.get("original_name")
    return {
        "tmdb_tipo": tipo_tmdb,
        "tmdb_id": mejor["id"],
        "titulo_original": original if normalizar(original) != normalizar(t["titulo"]) else None,
        "poster_path": d.get("poster_path") or d.get("_poster_en"),
        "sinopsis": d.get("overview") or None,
        "director": director,
    }, None


def resumen_candidato(c, tipo):
    if "error" in c:
        return c["error"]
    nombre = c.get("title") or c.get("name")
    fecha = c.get("release_date") or c.get("first_air_date") or "????"
    return f"[{c['_puntaje']:>3}] {tipo}/{c['id']}  {nombre} ({fecha[:4]})"


def main():
    if not CLAVE:
        sys.exit("Falta TMDB_API_KEY. Sacala gratis en themoviedb.org "
                 "(Settings → API) y exportala.")
    forzar = "--forzar" in sys.argv
    titulos = json.load(open(RUTA, encoding="utf-8"))

    resueltos = pendientes = 0
    for t in titulos:
        if t.get("tmdb_id") and not forzar:
            continue
        try:
            campos, candidatos = resolver(t)
        except Exception as e:
            campos, candidatos = None, [{"error": str(e)}]
        if campos:
            t.update(campos)
            t.pop("revisar", None)
            t.pop("candidatos", None)
            resueltos += 1
            print(f"  ok   {t['titulo']} ({t['anio']}) → {campos['tmdb_tipo']}/{campos['tmdb_id']}")
        else:
            tipo = "movie" if t["tipo"] == "pelicula" else "tv"
            t["revisar"] = True
            t["candidatos"] = [resumen_candidato(c, tipo) for c in (candidatos or [])]
            pendientes += 1
            print(f"  ??   {t['titulo']} ({t['anio']})")
            for linea in t["candidatos"]:
                print(f"         {linea}")
        time.sleep(0.15)

    with open(RUTA, "w", encoding="utf-8") as fh:
        json.dump(titulos, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    print(f"\n{resueltos} resueltos, {pendientes} a revisar a mano.")
    if pendientes:
        print("Editá seed/titulos.json: poné tmdb_tipo y tmdb_id del candidato correcto,\n"
              "borrá 'revisar' y 'candidatos', y volvé a correr para completar el resto.")


if __name__ == "__main__":
    main()
