# Creador de videos

**¿Primera vez? Empieza por [GUIA.md](GUIA.md).** Este archivo es la referencia.

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
./creador probar                       # autodiagnóstico: dice si todo funciona y cómo arreglar lo que no (--rapido omite Remotion)
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
1. Pulido con tu marca real: fuentes de calidad (hoy se usan las del sistema), colores, logo y el acabado de cada pieza, que solo se puede afinar con una toma real de cada empresa.
2. Que la mira siga la cara de la persona (hoy queda en una posición fija) y transiciones con desenfoque de movimiento.
3. Montaje a ráfagas sobre el pulso de la música.
4. Texto detrás de la persona con un modelo de recorte (por probar); el texto pegado al suelo seguirá siendo manual.
5. Cargar tus estadísticas en la bóveda y comparar contra las referencias.
6. Pruebas automáticas en cada cambio (hoy el autodiagnóstico se ejecuta a mano con `./creador probar`).

**Sin probar en un Mac** (solo se probó en Linux): `instalar.sh`, la descarga real de referencias, `estudio`, abrir la bóveda en Obsidian y la velocidad de la transcripción.

**«Sin ningún error» no se puede prometer.** Lo que sí hay: autodiagnóstico (`probar`), validador de la bóveda, escritura que no deja archivos a medias y notas generadas que nunca pisan las escritas a mano. Las descargas de YouTube, TikTok e Instagram pueden fallar cuando esas redes cambian; se arregla actualizando `yt-dlp`.

## Límites
- El algoritmo de cada red no es visible. Se infieren patrones de lo público (estructura, ritmo, métricas); la retención real solo la ves en las estadísticas de tus propias cuentas.
- Desde la nube de Claude no se pueden bajar videos de las redes: YouTube y TikTok bloquean esas IP. Descarga en tu Mac. Los videos que envías por el chat sí llegan a la sesión de Claude.
- Remotion es gratis para personas y empresas con hasta 3 empleados; una empresa mayor necesita licencia (remotion.pro).
- Los videos ajenos son referencia para estudiar estructura, no material para republicar.
- Los cortes se miden sobre el cuadro completo: en pantallas divididas o tomas continuas con gráficos encima el cambio real está en las capas y la cifra de cortes queda baja.
- Verificado en Linux (no en Mac): autodiagnóstico completo, análisis y transcripción con 4 videos reales en español e inglés, notas e informes en la bóveda, validador con fallos provocados a propósito, instalación desde cero en una copia limpia, lectura de metadatos de YouTube y render con Remotion (escenas, clips, subtítulos, logo, audio).
