# Pendientes

Cada ítem trae lo que hace falta para hacerlo, sin tener que buscar en otro lado.

## Bloquean el seed

1. [ ] **Corregir los dos `tmdb_id` que apuntan a otra película.** Se detectan por la dirección:
   *The Time That Remains* (2009) dice "Soda Jerk" y es de **Elia Suleiman**; *Memories of Murder*
   (2003) dice "Robert Michael Lewis" y es de **Bong Joon-ho**. El id sale de la URL en
   themoviedb.org (`/movie/11423-memories-of-murder` → `11423`).

   ```bash
   python3 seed/corregir.py "Memories of Murder" movie <id>
   python3 seed/corregir.py "The Time That Remains" movie <id>
   export TMDB_API_KEY=...
   python3 seed/resolver_tmdb.py && python3 seed/validar.py
   ```

2. [ ] **Decidir Satyricon.** `movie/281783` es el de **Gian Luigi Polidoro**. En 1969 se estrenaron
   dos y el famoso es el de **Fellini** — el año no desambigua. Si era Fellini, corregir igual que arriba.

3. [ ] **Año de *Fondo de aire rojo*.** El id (`movie/53197`) es correcto: *Le fond de l'air est rouge*
   de Chris Marker. Pero es de **1977**, y en la nota figura 2024. Corregir el año en
   `seed/titulos.json` y en `seed/lista.raw.txt` para que no se separen.

## Infra

4. [ ] **DNS.** `cineclub.tallertotal.org` todavía no resuelve. Crear el registro en Cloudflare
   apuntando a `186.13.42.31`, **proxeado** (nube naranja), igual que `microapp`.

5. [ ] **Setup de Dokku.** Después del DNS:

   ```bash
   sudo dokku apps:create cineclub
   sudo dokku postgres:create cineclub-db
   sudo dokku postgres:link cineclub-db cineclub
   sudo dokku domains:set cineclub cineclub.tallertotal.org
   sudo dokku resource:limit --memory 512m cineclub    # la máquina está justa de RAM
   sudo dokku letsencrypt:list                          # ver cómo lo resolvieron las otras apps
   ```

6. [ ] **Crear el bot en @BotFather** y guardar el token. Hace falta para el webhook y también
   para verificar el `initData` de la Mini App — es la misma clave.

7. [ ] **Registrar el webhook** una vez que la app esté desplegada, con un `secret_token` propio:

   ```bash
   curl -F "url=https://cineclub.tallertotal.org/telegram/webhook" \
        -F "secret_token=<algo largo y aleatorio>" \
        https://api.telegram.org/bot<TOKEN>/setWebhook
   ```

   El backend **tiene que verificar** la cabecera `X-Telegram-Bot-Api-Secret-Token` en cada request,
   o cualquiera puede postear updates falsos al endpoint.

## Código

8. [ ] **Proyecto Django sin DRF.** Un solo servicio: la API, el admin y el webhook del bot.
9. [ ] **Cargador del seed** — el paso 4 de `seed/README.md`, lee `titulos.json` y puebla las tablas.
10. [ ] **El bot**: `/add` con desambiguación por botones, manejo del deep link
    `?start=add__<término>`, y aviso al grupo cuando se agrega algo.
11. [ ] **API + Mini App**: `GET /api/titulos`, `PUT|DELETE /api/titulos/{id}/voto`, con `initData`
    verificado por HMAC. El frontend parte de `docs/mockup-miniapp.html`.

## Chico y fácil de olvidar

12. [ ] **Atribución de TMDB en la Mini App.** Sus términos la exigen: "Este producto usa la API de
    TMDB pero no está avalado ni certificado por TMDB", con el logo. Va en el pie de la ficha, junto
    al link "Ver en TMDB".

13. [ ] **Deuda visual**: el emoji 🎭 está repetido en Drama y Comedia. Como chips uno al lado del
    otro, confunde. Cambiar el de Comedia cuando moleste.

## Preguntas abiertas

14. [ ] **¿Hay un Postgres reutilizable en el servidor?** (`sudo dokku postgres:list`). La decisión
    tomada es usar uno dedicado, pero conviene saber qué hay para dimensionar la máquina.

15. [ ] **¿Dar acceso a dokku o correr los comandos a mano?** La clave sigue sin registrar. Tener
    presente que Dokku no tiene permisos por app: registrarla da acceso a las 11 apps del servidor,
    incluidas las de producción.

16. [ ] **¿Qué pasó con la cuenta `MatiasRizzi`?** Las cuatro claves SSH (`github`, `id_rsa`,
    `id_rsa_azure`, `github_cineclub`) autentican hoy contra `rizzijmatias-terminus`. Si la cuenta
    vieja todavía existe con repos adentro, desde esta máquina no se puede pushear ahí.
