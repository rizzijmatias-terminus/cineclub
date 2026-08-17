# Cineclub

Lista de películas compartida por un grupo de amigos, con **bot de Telegram** para dar de alta y
**Mini App** para navegar. Reemplaza una nota de Google Keep que se volvió difícil de consultar.

## Cómo funciona

```
Telegram bot  ──escribe──▶  Postgres  ◀──lee/vota──  Mini App (Telegram Web App)
   /add                                                  grilla + ficha
```

- **El bot da de alta.** `/add <título>` resuelve contra TMDB, desambigua con botones, deduplica por
  `tmdb_id` y confirma en el grupo para que todos vean lo que se agregó.
- **La Mini App navega.** Grilla por género con orden y buscador, ficha por título con la calificación
  del grupo. No da de alta: un botón manda al bot por deep link.
- **La identidad la da Telegram.** El backend verifica el `initData` por HMAC con el token del bot.
  Nadie crea una cuenta.

## Estado

En implementación. La UI está cerrada — ver `docs/mockup-miniapp.html` (maqueta navegable con datos
reales de la lista, estados de carga y error, y el voto optimista simulados).

Lo que sigue:

1. Modelo de datos en Postgres
2. Seed de los 47 títulos desde la nota de Keep, resueltos contra TMDB
3. El bot: `/add`, desambiguación, deep link `?start=add__<término>`
4. API + Mini App: lectura de la lista y voto con `initData` verificado

## Despliegue

Dokku sobre `cineclub.tallertotal.org`. El bot usa long polling, así que no necesita nada entrante —
el dominio lo necesitan sólo la Mini App y la API.

> El servidor tiene la RAM justa y los builds de Dokku corren en el host. Usar
> `dokku resource:limit` y evitar builds pesados.

## Decisiones de diseño

En `docs/decisiones.md`, con el porqué de cada una.
