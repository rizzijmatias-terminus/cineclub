# Seed

Carga inicial de la lista, en tres pasos. Es trabajo de una sola vez, pero queda
versionado porque documenta de dónde salió cada dato.

```
lista.raw.txt   →   parsear.py   →   titulos.json   →   resolver_tmdb.py   →   (cargador)
  (la nota)          estructura        revisable         enriquecido            a la base
```

## 1. Parsear

```bash
python3 seed/parsear.py seed/lista.raw.txt > seed/titulos.json
```

Entiende la estructura de la nota: encabezados de sección, `Título (Año)` y
episodios `Serie, TxxExx`. **Reporta a stderr cualquier línea que no haya podido
clasificar** — si sale "sin líneas huérfanas", nada se perdió en el camino.

`lista.raw.txt` está en `.gitignore`: es la exportación de la nota, no el dato.
El resultado revisable es `titulos.json`, que sí se commitea.

## 2. Resolver contra TMDB

Hace falta una clave gratuita de [themoviedb.org](https://www.themoviedb.org)
(Settings → API).

```bash
export TMDB_API_KEY=...
python3 seed/resolver_tmdb.py
```

Completa `tmdb_tipo`, `tmdb_id`, `titulo_original`, `poster_path`, `sinopsis` y
`director`. Es **idempotente**: saltea los que ya están completos, así que se
puede correr las veces que haga falta.

El trabajo está partido en dos, y eso importa para las correcciones a mano:

- `identificar()` **busca** y decide qué `tmdb_id` corresponde.
- `enriquecer()` **completa el resto de los campos a partir del id que haya**,
  venga del buscador o lo hayas puesto vos.

Por eso corregir un id a mano y volver a correr alcanza para que se complete
solo. Cada uno imprime lo que TMDB dice que es ese id:

```
  ok   Dersu Uzala (1975)
         TMDB movie/9764 dice: Dersu Uzala (1975)
         dirección: Akira Kurosawa
```

**Revisá esa línea**: es la forma de detectar un id que apunta a otra película.

Lo que no puede resolver con confianza **no lo adivina**: lo marca con
`"revisar": true` y una lista de candidatos con su puntaje.

```json
{
  "titulo": "Héroe",
  "anio": 2002,
  "revisar": true,
  "candidatos": [
    "[ 70] movie/79  Hero (2002)",
    "[ 40] movie/8452  Hero (1992)"
  ]
}
```

Para arreglarlo a mano: poné `tmdb_tipo` y `tmdb_id` del correcto, borrá
`revisar` y `candidatos`, y volvé a correr — completa el resto de los campos.

Se esperan entre cinco y ocho a revisar. Los sospechosos son los títulos en
castellano que TMDB indexa distinto (*Héroe* es 英雄/*Hero*, *Fondo de aire rojo*,
*La Fiaca*, *Felicidades*), los ambiguos por nombre (*Frankenstein* 2025,
*Moebius* — hay una argentina del 96 y una coreana del 2013) y las series que aún
no estrenaron (*La Casa de los Espíritus*, 2026).

**Cuidado con el poster de los episodios**: se usa `still_path` (el fotograma del
episodio) y si no hay, cae al poster de la serie.

## 3. Cargar a la base

Pendiente: depende del proyecto Django, que todavía no existe. El cargador va a
leer `titulos.json` y poblar `generos`, `titulos` y el usuario que figura como
proponente inicial.
