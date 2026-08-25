# Cineclub — CLAUDE.md

Lista de películas compartida por un grupo de amigos. **Bot de Telegram** para dar de alta,
**Mini App** para navegar. Reemplaza una nota de Google Keep. Proyecto personal, ~5-10 usuarios,
47 títulos que crecen de a poco.

> No tiene relación con Dory ni con wannacode, aunque se despliegue en el mismo servidor.

## Por dónde empezar

| Para saber | Leer |
|---|---|
| Qué es y cómo funciona | `README.md` |
| **Por qué está hecho así** | `docs/decisiones.md` — lo cerrado y lo descartado, con el porqué |
| Esquema de la base | `docs/modelo-de-datos.md` |
| Qué falta hacer | `docs/todo.md` — con los comandos adentro de cada ítem |
| Cómo se ve la Mini App | `docs/mockup-miniapp.html` — maqueta navegable, abrir en el browser |
| La carga inicial de datos | `seed/README.md` |

**Leer `docs/decisiones.md` antes de proponer cambios de diseño.** Muchas cosas que parecen
mejoras obvias ya se discutieron y se descartaron por razones que están anotadas ahí.

## Stack

- **Django sin DRF.** La API son tres vistas devolviendo `JsonResponse`: la lista, el voto y el
  webhook del bot. DRF se descartó explícitamente — ver `decisiones.md`.
- **Postgres.** Esquema en `docs/modelo-de-datos.md`.
- **El bot va por webhook**, no long polling: es un endpoint más de la misma app, un solo proceso.
- **Sin auth propia.** La identidad la da Telegram: `initData` verificado por HMAC con el token del
  bot en la Mini App, y el `from.id` del update en el bot. Nadie crea cuenta.

## Despliegue

Dokku en `cineclub.tallertotal.org` (servidor `186.13.42.31`, puerto SSH 2222).

> **El servidor tiene la RAM justa** — 3,7 GB con once apps, varias de producción de otro proyecto,
> y swap ya en uso. Los builds de Dokku corren en el host. Usar `dokku resource:limit` y evitar
> builds pesados: un OOM acá se lleva puesta una app ajena.

## Convenciones

- **Todo en castellano**: código, comentarios, documentación y mensajes de commit.
- **Los commits explican el porqué**, no el qué. El diff ya dice qué cambió.
- **Sin `Co-Authored-By: Claude`** en los commits.
- **Git**: el remote usa el alias SSH `github-cineclub`, no `github.com`. Son cuentas distintas y
  `github.com` resuelve con otra clave — pushear con la URL normal usa la cuenta equivocada.
- Los scripts del seed no tienen dependencias: sólo stdlib, sin venv.

## Datos

`seed/lista.raw.txt` (la nota exportada) está en `.gitignore` a propósito: es la fuente, no el dato.
El resultado revisable es `seed/titulos.json`, que sí se versiona.

Antes de cargar cualquier cosa a la base: `python3 seed/validar.py`, que chequea las mismas reglas
que impone Postgres pero con mensajes legibles.
