# Modelo de datos

Cuatro tablas. El esquema está en DDL porque es la forma precisa; si vamos con Django, los modelos
salen directo de acá.

## Esquema

```sql
create table generos (
  slug   text primary key,        -- "drama", legible en queries y en la API
  emoji  text not null,
  label  text not null,
  orden  smallint not null        -- el orden de los chips lo manda el dato, no el código
);

create table usuarios (
  id         bigint primary key,  -- el id de Telegram, sin surrogate
  nombre     text not null,       -- first_name: lo que se muestra
  username   text,                -- opcional y cambiante: nunca usar como clave
  creado_en  timestamptz not null default now()
);

create table titulos (
  id               bigserial primary key,
  titulo           text     not null,     -- como lo dice la gente
  titulo_original  text,                  -- de TMDB
  anio             smallint,
  tipo             text     not null check (tipo in ('pelicula','serie','episodio')),
  genero_slug      text     not null references generos(slug),

  tmdb_tipo        text     check (tmdb_tipo in ('movie','tv')),
  tmdb_id          integer,
  temporada        smallint,              -- sólo para tipo='episodio'
  episodio         smallint,

  poster_path      text,                  -- "/abc.jpg", no la URL completa
  director         text,
  sinopsis         text,

  propuesto_por    bigint   not null references usuarios(id),
  agregado_en      timestamptz not null default now(),
  nota             text,

  constraint tmdb_completo check ((tmdb_tipo is null) = (tmdb_id is null)),
  constraint episodio_numerado check (
    tipo <> 'episodio' or (temporada is not null and episodio is not null)
  )
);

-- Deduplicación. Parcial, para que los títulos cargados a mano sin TMDB
-- no choquen entre sí por tener todo en null.
create unique index titulos_tmdb_unico
  on titulos (tmdb_tipo, tmdb_id, coalesce(temporada,-1), coalesce(episodio,-1))
  where tmdb_id is not null;

create index titulos_genero_idx   on titulos (genero_slug);
create index titulos_agregado_idx on titulos (agregado_en desc);

create table votos (
  titulo_id   bigint      not null references titulos(id) on delete cascade,
  usuario_id  bigint      not null references usuarios(id),
  valor       smallint    not null check (valor between 1 and 5),
  votado_en   timestamptz not null default now(),
  primary key (titulo_id, usuario_id)   -- un voto por persona por título
);

create view titulos_rating as
  select t.*,
         count(v.valor)                  as votos,
         round(avg(v.valor)::numeric, 2) as promedio
  from titulos t
  left join votos v on v.titulo_id = t.id
  group by t.id;
```

## Por qué así

### El id de Telegram es la clave primaria de usuarios

Es un int64 estable y global. Usarlo directo evita una tabla de mapeo y hace que el bot y la Mini App
resuelvan al mismo usuario sin coordinarse: el bot lo lee del update, la app del `initData` verificado.

`username` es opcional en Telegram y se puede cambiar cuando uno quiera, así que no sirve ni como clave
ni como única forma de mostrar a alguien. Se muestra `nombre`, con `username` como complemento.

### La deduplicación no puede ser sólo `tmdb_id`

TMDB tiene **espacios de id separados** para películas y series: `movie/123` y `tv/123` son cosas
distintas. Por eso la clave de dedupe es `(tmdb_tipo, tmdb_id)`, no `tmdb_id` solo.

Y para episodios hace falta más: un episodio de Los Simpson apunta al `tv/456` de la serie, igual que
la serie misma. Lo que los diferencia es `temporada` + `episodio`, así que entran en el índice. El
`coalesce(..., -1)` es para que los nulls comparen como iguales — sin eso Postgres considera cada null
distinto y la restricción no dedupe nada. En Postgres 15+ se puede usar
`unique nulls not distinct` en su lugar, que es más legible pero ata la versión.

El índice es **parcial** (`where tmdb_id is not null`) para que se puedan cargar títulos a mano que
TMDB no tenga, sin que colisionen entre ellos.

### No hay columna `estado`

Se deriva de `votos`, que es la decisión que ya estaba tomada: si alguien calificó, la vio. Y sirve
para las dos preguntas distintas sin guardar nada:

- ¿la vio el grupo? → el título tiene algún voto
- ¿la vi yo? → existe mi voto para ese título

### No hay `promedio` ni `cantidad_votos` cacheados en `titulos`

Tentador, porque la grilla muestra la calificación de todos los títulos. Pero son 47 filas y del orden
de 200 votos: el `left join` con `group by` de la vista corre en menos de un milisegundo. Cachear
obligaría a actualizar en cada voto, cada cambio de voto y cada borrado, y a arreglar la deriva cuando
algo falle en el medio.

La vista `titulos_rating` deja las queries legibles sin desnormalizar. En Django el equivalente es un
`annotate(Avg, Count)` y ni hace falta la vista.

Se revisa cuando haya miles de títulos, o si aparece una pantalla muy visitada que ordene por
promedio.

### El mapeo de géneros de TMDB va en el código, no en la base

TMDB devuelve sus propios géneros; nuestra taxonomía es editorial y no coincide. El mapeo es una
**heurística que se usa una sola vez, al agregar**, para pre-seleccionar el botón que el humano
confirma. Nadie lo consulta después. Es lógica, no dato: va versionado con el código.

### El bot no necesita guardar estado de conversación

El flujo de `/add` tiene pasos (buscar → elegir candidato → confirmar género), pero ese estado puede
viajar en el `callback_data` de los botones, que admite 64 bytes:

```
pick|movie|1234            → elegiste este candidato
gen|movie|1234|drama       → y este género
```

Alcanza de sobra. **El bot queda stateless**: no hace falta tabla de sesiones ni Redis, y un redeploy
en medio de un alta no rompe nada.

### `director` es un campo de texto

Normalizarlo permitiría "todas las de Kurosawa", que en esta lista tiene sentido — hay dos Visconti y
dos von Trier. Pero es una tabla más y una pantalla más, y hoy nadie lo pidió. Si aparece, una tabla
`personas` con una intermedia es la evolución natural y no invalida nada de esto.

### El borrado es real, con cascada

Si alguien carga mal un título se borra, y sus votos se van con él (`on delete cascade`). No hay
borrado lógico: en una lista entre amigos no hay nada que auditar.

## Lo que no está y forzaría un cambio de esquema

**Un solo grupo.** El chat al que el bot avisa es configuración (variable de entorno), no dato. Si
alguna vez hay más de un grupo, aparece una tabla `grupos` y `titulos` necesita `grupo_id` — es el
cambio más probable a futuro y el más caro, porque toca la clave de dedupe (dos grupos pueden querer
la misma película).

**Búsqueda en el servidor.** La API devuelve la lista completa y la Mini App filtra en memoria, que es
lo que hace la maqueta y lo correcto a este tamaño. Por eso no hay índice de texto. Cuando la lista no
entre en una respuesta razonable, la búsqueda se mueve al servidor y ahí entra `pg_trgm`.

## Superficie de la API que se desprende

```
GET  /api/titulos          → lista completa desde titulos_rating, más mi voto en cada uno
PUT  /api/titulos/{id}/voto  {valor: 1..5}
DELETE /api/titulos/{id}/voto
```

Todo autenticado con el `initData` de Telegram verificado por HMAC con el token del bot.
