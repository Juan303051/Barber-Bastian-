# Creador de videos

**¿Primera vez? Empieza por [GUIA.md](GUIA.md).** Este archivo es la referencia. Qué es Iris y qué no: [SPEC.md](SPEC.md) · por qué se decidió así: [DECISIONS.md](DECISIONS.md) · qué se hizo y qué se encontró: [JOURNAL.md](JOURNAL.md) · privacidad, accesibilidad y licencias, punto por punto: [CUMPLIMIENTO.md](CUMPLIMIENTO.md).

Herramientas para guardar videos de referencia por empresa, medir cómo están hechos, compararlos con los tuyos y **recordar lo aprendido en una bóveda de Obsidian**. Los videos se quedan en tu Mac; al repositorio suben las métricas y las notas (los fotogramas se quedan en tu Mac, porque el repositorio es público), que es lo que Claude lee para analizar y proponer. Reglas de trabajo de Claude: `CLAUDE.md`.

## Dos carpetas con dos funciones
| Carpeta | Qué guarda |
|---|---|
| `boveda/` | **La memoria** (Markdown, se abre con Obsidian): fichas, notas por video, análisis, investigaciones con fuente, formatos e ideas, una carpeta por empresa. Guía y reglas: `boveda/00-LEEME.md` |
| `empresas/<empresa>/` | **Los datos de máquina** de cada empresa: enlaces y videos de entrada, métricas en JSON, guiones de Remotion y videos generados |

Dentro de `empresas/<empresa>/`:

| Archivo | Para qué |
|---|---|
| `referencias.txt` | Enlaces de videos que quieres tomar como modelo, con un comentario de por qué |
| `propios.txt` | Enlaces de tus videos ya publicados de esa empresa |
| `videos/referencias/`, `videos/propios/` | Los archivos de video (no se suben al repo). Puedes soltar ahí un .mp4 a mano |
| `analisis/` | Métricas en JSON (`.meta.json`, `.analisis.json`) de las que salen las notas de la bóveda |
| `formatos/` | Guiones JSON de los videos que se van a hacer (los lee Remotion) |
| `marca.json` | Opcional: colores, fuente, logo y usuario de la marca para Remotion |
| `salidas/` | Videos generados por Remotion (no se suben al repo) |

`maquetas-estilo` no es una empresa: es la biblioteca de videos modelo que sirve a todas.

## Uso
```bash
./instalar.sh                          # una sola vez
./creador app                          # la app de una sola pantalla (abre el navegador; deja la Terminal abierta)
./creador celular                      # pasa la app a un celular Android conectado por cable (abre el navegador del celular)
./creador iphone                       # opcional: abre Iris al iPhone por tu Wi-Fi de casa, con código de emparejamiento (la conexión no va cifrada)
./creador director                     # el test del director contra la IA real (necesita clave; cuesta unos centavos de dólar)
./creador musica cancion.mp3           # mide una canción: tempo, pulsos, energía, secciones y volumen
./creador cuenta restablecer ana@correo.com   # si olvidaste la contraseña de la app (./creador cuenta lista muestra las cuentas)
./creador probar                       # autodiagnóstico: dice si todo funciona y cómo arreglar lo que no (--rapido omite Remotion; las pruebas de pantalla solo corren si tienes Playwright)
./creador preparar                     # crea las carpetas donde soltar videos (también lo hace cada comando)
./creador todo                         # descarga, analiza, escribe las notas en la bóveda y la revisa
./creador todo --empresa al-volante    # solo una
./creador descargar --cookies-navegador safari   # si una red pide sesión
./creador analizar --sin-voz           # sin transcripción (más rápido)
./creador analizar --forzar            # rehacer lo ya analizado
./creador informe                      # reescribe las notas de cada video y el informe de cada empresa
./creador validar                      # revisa la bóveda: enlaces rotos, empresas mezcladas, videos dentro, notas sin propiedades
```
Después sube los resultados para que Claude los lea: `git add -A && git commit -m "Nuevas referencias" && git push`. Para recibir lo que Claude escribió: `git pull`.

## La app Iris (una sola pantalla)
```bash
./creador app        # abre http://127.0.0.1:8765; mientras trabajes, la ventana de la Terminal debe seguir abierta (Control + C la cierra)
```
Una pantalla con tres partes: **1. Referencias** (sueltas videos que te gustan o pegas un enlace; Iris mide su ritmo y su voz), **2. Música** (tus canciones, cada una con su licencia declarada) y **3. Tus videos** (todos los que necesites: subes **las escenas que grabaste**, escribes qué quieres y pulsas Crear). Mientras se crea, la tarjeta del video muestra **el video construyéndose fotograma a fotograma**, las etapas, el avance y el tiempo que falta. Al terminar se ve, se descarga y trae **lo que pediste y si se hizo**, su **informe de calidad** y **cómo lo dirigió Iris**. Diseño: Human Interface Guidelines de Apple con paleta arcoíris (investigación: `boveda/01-conocimiento/investigacion/diseno-apple-hig.md`).

| Tema | Cómo funciona |
|---|---|
| **Escenas** | Un video son **hasta 24 escenas** (archivos de video) que se suben juntas, se ordenan con «Subir» y «Bajar» (también con teclado; no hace falta arrastrar, WCAG 2.2 · 2.5.7) y se quitan una a una. Se ordenan solas por número en el nombre (`escena 2` antes de `escena 10`). Iris las deja del mismo tamaño y velocidad (30 fps), respeta el giro del iPhone, rellena el audio de las que no tienen y las une en una sola toma; sobre ella trabaja todo lo demás. Detalle: `app/servidor/escenas.py` |
| **Formato** | Se elige o lo decide Iris: **Automático** (según lo que escribes y lo que se oye), **Subtítulos**, **Dinero** (calculadora), **Antes y después** y **Pasos**. Cambiarlo no borra lo que escribiste. Catálogo: `app/servidor/formatos.py` |
| Lo que escribes | **Reglas, y mandan sobre el valor por defecto.** Entiende palabras en grande, cierre «comenta PALABRA», subtítulos arriba/centro/abajo, antes y después, quitar pausas, música sí/no, color, y también **calculadora, transiciones, efectos de sonido y logo**, con sus negaciones («sin efectos de sonido»). Lo que no sabe hacer (texto detrás de la persona, recorte exacto) lo dice en «Esto entendí». Un interruptor que **no tocaste** sigue a tu texto; uno que tocaste manda sobre el texto (el motivo se ve debajo de cada uno) |
| **Extras** | Cada uno se apaga solo: **calculadora** (suma, resta y muestra el resultado con las cifras que dices: «8.500.000», «300 mil», «un millón»; si el resultado no se dijo, el informe lo marca como calculado por Iris), **transiciones** (destello, barrido o impacto, solo en cortes reales: entre escenas y donde se quitaron pausas), **efectos de sonido** (sintetizados, sin archivos de terceros; nivel sutil o marcado) y **logo animado** por marca (se sube una vez en la tarjeta del video, con la confirmación de que tienes derecho a usarlo) |
| **Lo que pediste** | Al terminar, una lista compara cada cosa pedida con lo que de verdad quedó en el video: **hecho**, **parcial**, **no** (con el motivo) u **omitido** (lo apagaste tú). `app/servidor/cumplimiento.py` |
| **Director con IA** | Opcional. Con una clave de Anthropic (menú de tu cuenta → «Director con IA…» o la variable `ANTHROPIC_API_KEY`) **y tu confirmación de qué se envía**, Claude (por defecto **Opus 5.5**, con **Sonnet 5.5** como opción más barata) lee el guion hablado con tiempos, las cifras dichas, los cortes de escenas, tu instrucción, la ficha de la marca de la bóveda y el test del director, y propone el **formato**, el **gancho** (hasta 7 palabras), las **palabras clave**, los **momentos de énfasis**, la **calculadora**, las **transiciones**, los **sonidos**, el **logo**, la música y el **acabado de color**, y devuelve la lista de **requisitos** que entendió. Se le pide con salida estructurada y esfuerzo alto. **Límites que el código hace cumplir** (la IA propone, el código decide): ninguna cifra, dato o promesa que no esté en lo que dijiste, en tu instrucción o en la ficha; las cifras de la calculadora solo si se oyen; las transiciones solo en cortes que existen; el logo solo si la marca tiene uno; ninguna palabra que la marca marcó como «nunca»; nada que hayas apagado; tiempos dentro del video; piezas separadas; no inventa pasos numerados; lo que elegiste en el test manda sobre sus gustos. **Si la IA falla** (sin clave, sin saldo, sin internet, rechazo, sin tu confirmación), el video se hace igual con reglas y se explica por qué. Costo estimado antes de crear: ≈ US$ 0,10 por video con Opus 5.5 (cálculo con 3.500 tokens de entrada y 4.500 de salida; **sin medir con una clave real**), y el gasto del mes se suma en el mismo diálogo |
| Qué se envía a la IA | Solo con tu confirmación (casilla aparte, con fecha): el texto de lo que dices con sus tiempos, tu instrucción, la ficha de la marca y las respuestas del test. **Los videos, las canciones y los logos no se envían.** Solo si lo activas, 6 imágenes pequeñas del video. La clave se guarda en `app/datos/ia.json` con permisos 600 (o se lee del entorno) y **nunca vuelve al navegador** |
| **Test del director** | Diez preguntas cortas (público, tono, ritmo, música, acabado, piezas en pantalla, canal, palabra de cierre, qué nunca debe aparecer, referentes). Se guarda por marca o general. Cambia el ritmo y las piezas **con o sin IA**, y es la memoria que la IA recibe. En la Terminal, `./creador director` pasa tres encargos (uno con una trampa) por la IA real y califica cada plan con la **rúbrica** (`app/servidor/direccion/rubrica.py`: gancho en 3 s, cifras respaldadas, nada prohibido, zona segura, densidad, etc.) |
| Música | Subes tus canciones (MP3, WAV, M4A, FLAC…). Iris mide **tempo, pulsos, tiempos fuertes, energía, secciones y volumen** con números (método de Ellis 2007), elige la que encaja, **empieza en un tiempo fuerte**, la **baja unos 10 dB cuando hablas** y la sube en las pausas. Los acercamientos se apoyan en el pulso y hay un latido muy sutil sobre los tiempos fuertes, solo si el análisis es fiable (≥ 55 %). **Cada canción declara su licencia**; con una «sin confirmar» el video sale marcado como no publicable. **Nunca se suben canciones al repositorio** |
| Audio final | Voz: quitar graves, reducción de ruido solo si hay ruido de fondo, compresión y presencia. Volumen **−14 LUFS** y pico real **≤ −1 dBTP** en dos pasadas (EBU R 128; el objetivo es el de las maquetas, configurable en `herramientas/mezcla.py`) |
| Acabado visual | Ajuste suave de color y contraste de la toma (natural, cálido, frío, cine, vibrante) con una viñeta muy ligera, y título de gancho dentro de la zona segura (fuera del 14 % de arriba y del 35 % de abajo de Reels) |
| **Control de calidad** | Mide el video terminado: volumen y pico, silencio al inicio, fotogramas negros, imagen congelada, tamaño y formato, gancho en 3 s, zona segura, cifras y textos sin respaldo, palabras prohibidas, licencia de la música, **promesas que suelen pedir prueba** («garantizado», «el mejor»…), tarjetas con aspecto de reseña, **menores sin autorización de sus padres** y cifras calculadas por Iris que no se dijeron. Resultado: «Listo para revisar», «Revisa antes de publicar» o «Hay problemas». Mide lo medible; **no juzga el gusto** |
| Resultado | Siempre es un **borrador que tú revisas**. «Borrador rápido» lo hace a mitad de tamaño para probar |
| Cuentas | La primera se crea al abrir (con la casilla de términos **sin marcar de antemano**); desde el menú de tu avatar añades a más personas (todas ven el mismo panel de equipo). Una contraseña olvidada se restablece con `./creador cuenta restablecer` |
| **Privacidad y datos** | Textos de privacidad, términos, reembolsos y cookies dentro de la app (borrador: que los revise una persona de derecho de tu país). Menú de tu avatar → **Exportar mis datos** (un archivo legible, sin contraseñas ni claves) y **Eliminar mi cuenta** (con contraseña; opcionalmente también videos, referencias y música; la última cuenta borra además logos, test del director y clave de la IA). Aviso de cookies informativo: solo se usa una cookie de sesión y dos datos locales. Qué hace Iris con cada punto de tu lista: [CUMPLIMIENTO.md](CUMPLIMIENTO.md) |
| Seguridad | Por defecto solo escucha en `127.0.0.1` (nadie de tu red entra; el único desvío es el modo opcional `./creador iphone`, fila «Celular»); contraseñas con scrypt; sesión en cookie `HttpOnly` y `SameSite=Strict`; bloqueo tras 5 intentos fallidos durante 15 min; comprobación de `Host` y `Origin`; política de contenido estricta (sin código ajeno ni conexiones a otros sitios desde la página); telemetría de Hugging Face desactivada; Iris no pasa clave de licencia a Remotion |
| Datos | `app/datos/` (cuentas, trabajos, escenas subidas, canciones, logos en `marcas/`, ajustes de la IA; no se sube al repositorio). El video terminado también queda en `empresas/<marca>/salidas/`. Variables: `IRIS_DATOS`, `IRIS_MODELO_VOZ` (`small`), el modelo de la IA se elige en la pantalla, `IRIS_MAX_GB` (4) y `CREADOR_NAVEGADOR` |
| Celular | `./creador celular` (Android con depuración por USB y `adb`): usa `adb reverse`, así el celular abre Iris **por el cable** sin que el servidor salga de tu computador; en Chrome, menú ⋮ → «Añadir a la pantalla de inicio». **iPhone:** no hay cable equivalente, así que existe un modo **opcional por Wi-Fi de casa**: `./creador iphone`. Hay que confirmarlo escribiendo SI (avisa de que la conexión **no va cifrada**); escucha en `127.0.0.1` y en **una** dirección de tu red, solo atiende a aparatos de red local y al nombre exacto de tu Mac, y un aparato nuevo no ve nada hasta escribir un **código de 8 caracteres que solo aparece en la Terminal** (vence a los 10 min, sirve para 3 aparatos, se bloquea tras 5 fallos; Enter en la Terminal da otro). Los aparatos emparejados duran 12 horas y solo existen en memoria. Detalle y descartes: `DECISIONS.md` D12; código: `app/servidor/red.py` |
| Límites | Un video a la vez (los demás esperan en cola); hasta 24 escenas y 45 minutos por video; si se cierra la app a mitad, el video queda «interrumpido» y se vuelve a crear con un clic |

## La bóveda en Obsidian
1. Abre Obsidian → *Abrir carpeta como bóveda* → `creador-videos/boveda`.
2. Ajustes → Plugins del núcleo → activa *Plantillas*: la carpeta ya está configurada (`03-plantillas`).
3. Opcional: el plugin comunitario *Obsidian Git* sincroniza solo cada pocos minutos.
4. Para usar otra carpeta como bóveda: `CREADOR_BOVEDA=/ruta/a/tu/boveda ./creador informe`. Claude solo la ve si está dentro del repositorio.

El software **solo reescribe las notas marcadas `generado: true`** y se niega a tocar cualquier otra; escribe en un temporal y lo renombra, así que un corte a mitad no deja archivos a medias.

## Hacer videos con Remotion
[Remotion](https://www.remotion.dev) convierte un guion JSON en un video vertical 1080×1920 con la identidad de la empresa y las piezas del estilo de las maquetas (`boveda/01-conocimiento/tecnicas/estilo-cinetico-sobre-escena.md`). Los guiones viven en `empresas/<empresa>/formatos/`.

**De una toma en bruto a un video:**
```bash
# 1. Pon la toma en empresas/<empresa>/videos/propios/ y analízala (incluye la transcripción)
./creador analizar --empresa al-volante
# 2. Crea el guion borrador: subtítulos palabra por palabra y un acercamiento en una de cada dos frases
./creador guion toma1.mp4 --empresa al-volante                      # --diseno pleno para un solo cuadro; --nombre otro
# 3. Edítalo (palabras clave, capas, correcciones) y genera el video
./creador render toma1 --empresa al-volante                         # queda en empresas/al-volante/salidas/toma1.mp4
./creador estudio toma1 --empresa al-volante                        # o ajústalo viendo el resultado en el navegador
```
`./creador guion` no pisa un guion que ya existe (puede tener tus cambios). Ejemplos que funcionan sin tomas (`./creador render remotion/ejemplos/<nombre>.json --empresa al-volante`): `estilo-completo` (gancho, contador, insignias, palabra gigante, tarjeta y cierre con palabra clave), `elementos` (mira, texto curvo, tarjetas), `antes-despues` y `tutorial-pantalla`. Antes de renderizar, el guion se revisa y los errores salen en claro (qué escena, qué campo).

| Campo del guion | Qué es |
|---|---|
| `formato` | Nombre del video de salida |
| `diseno` | `pleno` (por defecto) o `antes-despues`: la toma cruda pequeña a la izquierda y la editada grande a la derecha |
| `base` | Toma continua `{ clip, desde, silenciar }`; las escenas y capas se dibujan encima. Con `base`, la duración se calcula sola |
| `duracion` | Segundos; obligatoria si no hay `escenas` ni `base` |
| `escenas[]` | `tipo`: `gancho` (texto enorme), `contenido` (texto abajo), `cta` (cierre; con `clave` muestra «Comenta «CLAVE»») o `pantalla` (grabación flotante con `zoom` y `focos`) · `duracion` · `texto` · `clip` y `desde` · `silenciar` |
| `capas[]` | Piezas con `ini` y `fin` (segundos) y posición `x`, `y` (% del cuadro): `contador` (`desde`, `hasta`, `prefijo`, `sufijo`), `insignia` (`numero`), `tarjeta` (`variante`: `comentario`, `notificacion`, `estadistica` o `foto`; `nombre`, `texto`, `cifra`, `etiqueta`, `meGusta`, `imagen`, `rotacion`), `mira` (`etiqueta`, `radio`), `texto-curvo` (`texto`, `forma`: `arco` u `onda`) y `palabra` (`texto`, `serif`, `color`, `tamano`) |
| `palabras` o `palabras_de` | Subtítulos palabra por palabra: la lista `[inicio, fin, palabra]`, o la ruta del `.analisis.json` de un video analizado |
| `estiloPalabras` | `maxPalabras`, `claves` (palabras grandes y en color de acento), `serif` (palabras en cursiva elegante), `posicion` (`arriba`, `centro`, `abajo`), `mayusculas` |
| `correcciones` | Arregla la transcripción: `{ "cloud": "Claude" }` |
| `zooms[]` | Acercamientos de la toma base: `ini`, `fin`, `escala`, `x`, `y` |
| `subtitulos[]` | Frases completas con `ini`, `fin` y `texto` |
| `voz`, `musica` | Audio de locución y música (`archivo`, `volumen`) |
| `ancho`, `alto`, `fps` | Opcionales; por defecto 1080×1920 a 30 fps |

Todas las rutas de archivos son relativas a `empresas/` (p. ej. `al-volante/videos/propios/toma1.mp4`). `marca.json` (opcional, por empresa): `{ "colores": { "fondo": "#0B0B0F", "texto": "#FFFFFF", "acento": "#FFC400" }, "fuente": "Impact", "fuenteSerif": "Georgia", "logo": "al-volante/logo.png", "usuario": "@alvolante" }`. Lo que no pongas toma valores neutros. Las fuentes son las del sistema: con las de tu marca instaladas en el Mac se usan tal cual.

## Qué mide
(Todo esto queda escrito en una nota por video dentro de la bóveda.)
- **Ritmo:** cortes por 10 s, plano mediano, cortes en los 3 primeros segundos, curva de cortes cada 5 s.
- **Audio:** volumen (LUFS), porcentaje de silencio, palabras por minuto y el gancho dicho (transcripción local con Whisper).
- **Alcance:** vistas, likes, comentarios y vistas por día, tal como las muestra la plataforma al descargar.
- **Fotogramas:** una tira con los 6 primeros segundos (el gancho), una hoja con 24 fotogramas repartidos y **un fotograma por plano**, para que Claude vea la edición y no solo los números.
- **Palabras con tiempo:** cada palabra con su segundo de inicio y fin, para medir el ritmo de los subtítulos y reconstruirlos en Remotion.

## Qué falta para estar completo
**De tu parte (datos y decisiones)**
1. Completar la ficha de cada empresa (`boveda/02-empresas/<empresa>/00-ficha.md`): sin ella, las ideas parten de suposiciones.
2. Un `marca.json` por empresa (colores, fuente, logo, usuario).
3. Referencias: al menos 3 por empresa para que se puedan ver patrones, y los enlaces de tus videos ya publicados.
4. Tomas en bruto de una empresa para la primera prueba real del estilo de las maquetas.
5. Las estadísticas de tus cuentas (retención por segundo, envíos, comentarios): es lo único que dice qué funciona de verdad.
6. Decidir si el repositorio pasa a privado (hoy es público) y si se prueba también el conector de InVideo.

**De mi parte (por construir)**
1. Pulido con tu marca real: fuentes de calidad (hoy se usan las del sistema), colores y el acabado de cada pieza (la calculadora, las transiciones y el logo animado), que solo se puede afinar con una toma real de cada empresa.
2. Que la mira siga la cara de la persona (hoy queda en una posición fija) y transiciones con desenfoque de movimiento.
3. Montaje a ráfagas sobre el pulso de la música.
4. Texto detrás de la persona con un modelo de recorte (por probar); el texto pegado al suelo seguirá siendo manual.
5. Cargar tus estadísticas en la bóveda y comparar contra las referencias.
6. Pruebas automáticas en cada cambio (hoy el autodiagnóstico se ejecuta a mano con `./creador probar`).
7. App: **variantes de gancho** (hoy la IA propone ideas alternativas pero no se renderizan), **estadísticas** (importar la retención a 3 y 10 segundos de cada plataforma y aprender qué gancho funciona en cada marca), publicación automática, texto detrás de la persona, acceso con passkey o verificación en dos pasos, una versión instalable para iPhone (hoy se abre en el navegador), cambiar el tamaño o la proporción del video (hoy es siempre vertical 1080×1920) y arrastrar para ordenar las escenas (hoy se ordena con «Subir» y «Bajar»).

**Sin probar en un Mac** (solo se probó en Linux): `instalar.sh`, la descarga real de referencias, `estudio`, abrir la bóveda en Obsidian, la velocidad de la transcripción y la app Iris en Safari (`./creador app`, soltar varias escenas desde Finder, reproducir el resultado). **Nunca probado**: el modo iPhone por Wi-Fi con un iPhone real y Safari, y con el cortafuegos de macOS (solo se probó con un navegador móvil simulado en Linux y un servidor real en dos direcciones); el director contra la API real de Claude (la nube de Claude no tiene clave; solo se probó con una IA simulada y con el SDK real contra un servidor falso, que comprueba el formato exacto de la petición, **incluido el esquema nuevo con calculadora, transiciones, sonidos y logo, que la API real aún no ha aceptado**), la mezcla, la música y los **efectos de sonido con el oído** (solo hay medidas), una toma real de iPhone girada (se probó el giro con un archivo sintético), el celular real (solo se probó el comando con un `adb` de mentira) y la **revisión legal** de los cuatro textos para tu país.

**«Sin ningún error» no se puede prometer.** Lo que sí hay: autodiagnóstico (`probar`), validador de la bóveda, escritura que no deja archivos a medias y notas generadas que nunca pisan las escritas a mano. Las descargas de YouTube, TikTok e Instagram pueden fallar cuando esas redes cambian; se arregla actualizando `yt-dlp`.

## Límites
- El algoritmo de cada red no es visible. Se infieren patrones de lo público (estructura, ritmo, métricas); la retención real solo la ves en las estadísticas de tus propias cuentas.
- Desde la nube de Claude no se pueden bajar videos de las redes: YouTube y TikTok bloquean esas IP. Descarga en tu Mac. Los videos que envías por el chat sí llegan a la sesión de Claude.
- Remotion es gratis para personas, empresas con hasta 3 empleados y organizaciones sin fines de lucro; una empresa mayor necesita licencia (remotion.pro) y las condiciones cambian con la versión 5. Confírmalo para tu negocio antes de publicar videos con fines comerciales.
- Los videos ajenos son referencia para estudiar estructura, no material para republicar.
- Los cortes se miden sobre el cuadro completo: en pantallas divididas o tomas continuas con gráficos encima el cambio real está en las capas y la cifra de cortes queda baja.
- App Iris, verificada en Linux con Chromium: cuentas, bloqueo por intentos, subida de varias escenas, interpretación del texto, videos creados de punta a punta (3 escenas reordenadas, con voz sintética en español, cifras habladas, calculadora, transiciones, 9 efectos de sonido y logo animado; con y sin IA simulada y música) con sus fotogramas en vivo, cancelación, escritorio y móvil, claro y oscuro, teclado (Tab y Esc), sin desplazamiento horizontal a 390 px, exportar y borrar cuenta, y una auditoría de accesibilidad automática (axe-core, 0 violaciones en acceso, panel, diálogos y textos legales). Modo iPhone por Wi-Fi: 48 comprobaciones del código de emparejamiento, de las defensas (host, origen, red privada, bloqueo) y de un servidor real escuchando en dos direcciones, más la página del código en un navegador móvil simulado. Las pruebas de pantalla (`pruebas_pantalla.py`) son opcionales: corren si tienes Playwright. Música: tempo exacto en 14 de 22 casos sintéticos (7 por octava, 1 mal), error de fase de unos 7 ms; mezcla a −14 LUFS con la música 7–10 dB más baja al hablar; control de calidad probado con videos sintéticos (negros, congelado, volumen alto, horizontal, mudo). Safari y un revisor humano de accesibilidad (VoiceOver) quedan sin probar.
- Verificado en Linux (no en Mac): autodiagnóstico completo, análisis y transcripción con 4 videos reales en español e inglés, notas e informes en la bóveda, validador con fallos provocados a propósito, instalación desde cero en una copia limpia, lectura de metadatos de YouTube y render con Remotion (escenas, clips, subtítulos, logo, audio).
