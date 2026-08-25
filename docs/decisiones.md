# Decisiones de diseño

Registro de lo que ya está cerrado y por qué. La idea es no volver a discutirlo salvo que aparezca
información nueva.

## Producto

**Bot para dar de alta + Mini App para navegar, no una sola superficie.**
El reparto es por dirección, no por feature: el bot empuja (escribir, avisar, dentro de la charla),
la app tira (leer, explorar, cuando abrís con intención). Se descartó el bot como interfaz de lectura
—navegar en un chat es malo— y se descartó la app como interfaz de alta.

**El alta vive en el bot aunque haya base de datos.**
Con Postgres la app *podría* escribir, pero el motivo del bot nunca fue técnico: agregar por el chat
son dos toques sin salir de la conversación, y **el grupo ve el aviso**. Por la app serían cinco toques
y nadie se entera. Además el alta es de bajísimo tráfico: un par de películas por semana contra una
lista que se navega todos los días.

**El bot tiene un solo comando.**
Se descartó el menú de géneros con inline keyboards, `/buscar`, `/stats` y la paginación: todo eso
era la respuesta a "cómo hago que navegar en un chat no sea horrible", pregunta que la Mini App
vuelve obsoleta. Candidatos a v2 sólo por ser *sociales*: `/ruleta` (el resultado es compartido y
nadie puede re-tirar en secreto) e inline mode (sirve para *mandar* una peli a la conversación).

**Privacy mode del bot queda activado**, y el alta es `/add <título>`. Desactivarlo dejaría al bot
leyendo todos los mensajes del grupo para ahorrar cinco caracteres.

## Datos

**Género único, no múltiple.** La lista original es de bucket único: cada título aparece una vez.
El multi-tag cambia la UI de filtros y el conteo por género.

**La taxonomía es editorial, no mecánica.** "Drama social/político/histórico" o
"Terror/Horror psicológico" son buckets propios; TMDB no los va a resolver. Se usa una tabla de mapeo
como *sugerencia* y se confirma al agregar. La curaduría es parte del valor de la lista.

**Series y episodios comparten una categoría** ("📺 Series"), pero el campo `tipo` los sigue
distinguiendo por dentro. La categoría es de navegación, el tipo es del dato.

**`estado` se deriva de los votos**: si alguien calificó, la vio. Un campo menos que mantener a mano.

**Un voto por persona por título**, como restricción de unicidad real en la base.

**Deuda anotada:** el emoji 🎭 está repetido en Drama y Comedia. En una lista de texto pasa
desapercibido; como chips uno al lado del otro, confunde. Se deja así por ahora.

## Interfaz

**Grilla de 3 columnas** con poster, título y año, más la calificación cuando existe.

**Orden en un sheet, con cinco criterios**, por defecto *últimos agregados*: en una lista compartida
que crece, "qué hay de nuevo" es la pregunta más frecuente. El orden es independiente del género.

**Una sola fila de filtros.** Se descartó una segunda faceta (década, sin ver): con 47 títulos,
encadenar dos facetas deja resultados de uno a tres items, porque el género ya corta de 47 a entre 4
y 20. Las décadas empiezan a valer alrededor de los 150 títulos.

**Calificación: estrellas con el promedio del grupo, tu voto abajo en número.**
Las estrellas son el control además del indicador. Se descartó tener dos filas de estrellas
(promedio y voto propio) por redundante, y se descartó mostrar los votos individuales de los demás
por minimalismo — si alguna vez se quieren, el lugar es tocar el número del promedio.

Las estrellas muestran el promedio *siempre*, también antes de votar: vaciarlas escondería la
calificación del grupo justo a quien no votó, que es la mayoría de las visitas.

**Esqueleto en la carga, no spinner.** Misma grilla en gris: no hay salto de layout y se percibe más
rápido aunque tarde lo mismo. El error es pantalla completa con motivo y botón de reintentar — lo
importante es que nunca quede una pantalla en blanco.

**Voto optimista.** La estrella se pinta al instante y el pedido va en segundo plano.
- Si falla, no pasa nada visible (hay un reintento silencioso antes de rendirse). La contra asumida:
  si los dos intentos fallan, el voto se pierde y se nota la próxima vez que se abre la app. Si
  molesta, la solución barata es guardarlo local y reintentar al abrir.
- El promedio del servidor pisa al calculado localmente.
- Gana el último voto: las respuestas viejas se descartan por número de secuencia.

**Los títulos nuevos no llevan marca.** El orden por defecto ya los pone arriba. Si con el uso resulta
que el grupo no vuelve a abrir la app, ahí se evalúa un "nuevo desde tu última visita" —que es la
versión útil, pero obliga a guardar la última visita de cada usuario.

**El pie de la grilla es un atajo al bot**, no una instrucción. Con el buscador sin resultados se
vuelve más prominente y arrastra el término buscado en el payload del deep link, porque es el momento
de mayor intención de alta que va a tener la app.

## Backend

**Django sin DRF.**
La sensación de que "Django es grande para esto" apunta a algo real, pero el bulto no es Django: es
DRF. Serializers, viewsets, routers y permissions para dos endpoints es pura ceremonia. Sin DRF
quedan las partes que sí se usan —ORM, migraciones, management commands y sobre todo **el admin**,
que es un CRUD gratis para corregir datos de una lista curada sin construir pantallas— y la API son
tres vistas devolviendo `JsonResponse`.

Se evaluó FastAPI y era una elección sana: unos 60 MB menos de memoria, pero sin admin y con
migraciones más artesanales. A esta escala la diferencia de peso no decide nada — con 5-10 usuarios
el cuello de botella es el tiempo de quien lo mantiene, no la máquina. Se descartaron Go y Node: la
ganancia es memoria que no hace falta y el costo es no acordarse cómo tocarlo en seis meses.

**El bot recibe updates por webhook, no por long polling.**
Al principio se había elegido long polling porque no requiere nada entrante. Pero el dominio con
HTTPS existe igual para la Mini App, y con webhook el bot deja de ser un proceso corriendo para
siempre y pasa a ser **un endpoint más de la misma app**: un contenedor en vez de dos. En una
máquina con la RAM justa eso ahorra más que elegir el framework más liviano, y elimina un proceso
que se puede colgar sin que nadie se entere.

Contrapartida a tener presente: el endpoint queda expuesto a internet. Telegram permite mandar un
`secret_token` en `setWebhook` que vuelve en la cabecera `X-Telegram-Bot-Api-Secret-Token`; hay que
verificarlo o cualquiera puede postear updates falsos.

## Infraestructura

**Postgres desde el arranque**, no Google Sheets. Se evaluó Sheets como almacenamiento —viable a esta
escala— pero al querer votos desde la app hacía falta un endpoint con credenciales de escritura, y una
vez que ese endpoint existe no hay razón para no usar una base de verdad. La planilla queda sólo como
origen del seed.

**Servicio de Postgres dedicado, no compartido.** En Dokku un servicio es un contenedor y una base;
compartirlo mezclaría las tablas con otra app. El ahorro de memoria (50-150 MB) no justifica el
acoplamiento — el riesgo real de esa máquina son los builds, no el estado en reposo.

**Bot y API en el mismo servicio.** Comparten modelo de datos y token; separarlos a esta escala es
trabajo sin beneficio.

**El repo vive en la cuenta nueva** (`rizzijmatias-terminus/cineclub`, privado), y se llega por el
alias SSH `github-cineclub` — no por `github.com`, que resuelve con otra clave. Los commits usan
`rizzijmatias@gmail.com` desde el primero, así que nunca hizo falta reescribir historia.
