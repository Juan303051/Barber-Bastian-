# Guía de uso, paso a paso

Para quien nunca ha usado la Terminal. Todo se hace en tu Mac. Lo que no esté probado en tu equipo figura en [README.md](README.md), sección «Qué falta».

## 1. Instalar (una sola vez, unos 10 minutos)
1. Abre **Terminal** (Cmd + Espacio, escribe «Terminal»).
2. Si te pide instalar las herramientas de desarrollo de Apple, acepta y espera.
3. Instala **Homebrew** siguiendo las instrucciones de https://brew.sh (una sola línea que copias y pegas) y **Obsidian** desde https://obsidian.md.
4. Descarga el proyecto y entra a la carpeta:
   ```bash
   git clone -b claude/exciting-clarke-hcbgb0 https://github.com/Juan303051/Barber-Bastian-.git
   cd Barber-Bastian-/creador-videos
   ```
5. Instala todo: `./instalar.sh` (pide tu contraseña de Mac si hace falta).
6. **Comprueba que funciona:** `./creador probar`. Debe terminar con «Todo en orden». Si algo falla, te dice qué y cómo arreglarlo; arregla lo primero y repite. La primera vez, la prueba de Remotion tarda porque descarga un navegador.

## 2. Abrir la memoria en Obsidian
Obsidian → *Abrir carpeta como bóveda* → elige `creador-videos/boveda`. Verás una carpeta por empresa. Empieza por `00-LEEME.md`.

## 3. Contar a cada empresa quién es
Para cada empresa, abre `02-empresas/<empresa>/00-ficha.md` y completa: qué vende, público, tono, redes y lo que nunca se hace. Sin esto, mis ideas parten de suposiciones.
Para que Remotion use sus colores, crea `empresas/<empresa>/marca.json` (ejemplo en el README, sección «Hacer videos con Remotion»).

## 4. Guardar videos de referencia
Tienes dos formas, por empresa:
- **Con enlaces:** pega un enlace por línea en `empresas/<empresa>/referencias.txt` (después de `#` puedes escribir por qué lo guardas). Tus videos ya publicados van en `propios.txt`.
- **Con archivos:** copia el .mp4 a `empresas/<empresa>/videos/referencias/` (o `propios/`). Sirve cuando un enlace no se deja descargar.

## 5. Analizar
```bash
./creador todo --empresa mundial-de-motos
```
Descarga lo que falte, mide cada video (cortes, ritmo, volumen, voz, fotogramas), escribe una nota por video en la bóveda y revisa que todo esté bien. La primera transcripción descarga un modelo de voz (150–460 MB). Abre en Obsidian `02-empresas/<empresa>/informe.md` para ver el resumen.
Para todas las empresas a la vez: `./creador todo`.

## 6. Pasar el trabajo a Claude y recibir su análisis
```bash
git add -A && git commit -m "Nuevas referencias" && git push
```
La primera vez, git te pedirá iniciar sesión en GitHub. Lo más fácil es instalar **GitHub Desktop** (https://desktop.github.com), o ejecutar `brew install gh` y luego `gh auth login`. Luego, en la conversación con Claude: «Analiza las referencias nuevas de Mundial de Motos». Claude lee la bóveda, escribe el análisis y las ideas, y sube los cambios. Tú los recibes con `git pull`. Mientras Claude trabaje en la nube no ve tus archivos de video: los videos que le envías por el chat sí le llegan.

## 7. Crear videos con la app (lo más fácil)
1. En la Terminal, dentro de `creador-videos`: `./creador app`. Se abre el navegador. **Deja esa ventana de la Terminal abierta** mientras trabajas.
2. La primera vez, crea tu cuenta (nombre, correo y contraseña). Las siguientes, entra con ellas. Si olvidas la contraseña: `./creador cuenta restablecer tu@correo.com`.
3. **Referencias:** suelta uno o varios videos que te gusten (o pega un enlace; si la red no deja descargarlo, sube el archivo). Iris aprende su ritmo. Son solo para estudiar cómo están hechos: no se republican.
4. **Música (opcional):** suelta tus canciones. Iris mide su pulso y energía solo. **Declara la licencia de cada una** (propia, comprada o de la biblioteca de música comercial de tu plataforma); con «sin confirmar», el video sale como borrador y no debes publicarlo.
5. **Test del director (2 minutos, una vez por marca):** en el aviso de arriba o en el menú de tu avatar. Son diez preguntas: tono, ritmo, música, acabado, qué nunca debe aparecer… Iris las usa en cada video.
6. **IA (opcional):** menú de tu avatar → «Director con IA…». Pega tu clave de Anthropic, **marca la casilla que confirma qué se envía** (sin ella la IA no recibe nada) y pulsa «Probar conexión». Con IA, un director propone el formato, el gancho, qué resaltar, la calculadora, las transiciones, los sonidos y el acabado; sin IA, Iris usa reglas y el resultado sigue saliendo. Ahí mismo ves cuánto cuesta cada video (unos 10 centavos de dólar con el modelo de máxima calidad) y lo gastado en el mes.
7. **Logo de la marca (una vez por marca, opcional):** en la tarjeta de tu video, botón «Logo». Sube el archivo (PNG con fondo transparente es lo mejor) y confirma que tienes derecho a usarlo. Aparece animado en el cierre.
8. **Tus videos:**
   - **Sube las escenas** como las grabaste (varias a la vez, o de una en una). Se ordenan solas por el número del nombre; si no, usa «Subir» y «Bajar» y «Quitar» en cada una. Pueden ser videos o fotos.
   - **Escribe qué quieres** con tus palabras (por ejemplo «contador de dinero: suma el precio y resta el descuento, transiciones, efectos de sonido, quita las pausas y cierra pidiendo que comenten EDITOR») o toca un atajo para insertar la frase completa.
   - **Formato:** déjalo en «Automático» o elige Subtítulos, Dinero, Antes y después o Pasos. Cambiarlo no borra tu texto.
   - **«Esto haré»:** muestra qué entendió y por qué. Cada extra (calculadora, transiciones, efectos de sonido, logo) tiene su interruptor; si no lo tocas, sigue lo que escribiste; si lo tocas, manda tu decisión.
   - Si aparecen niños en el video, marca que tienes la autorización de sus padres o tutores (si no, el informe no lo da por listo).
9. Pulsa **Crear video** (o «Crear N videos» arriba para todos a la vez). Verás el video construyéndose. Cuando termine, lee **«Lo que pediste»** (qué se hizo, qué se hizo a medias y qué no, con el motivo), el **informe de calidad** y **cómo lo dirigió Iris**; mira el resultado y descárgalo. Si algo no te gusta, «Cambiar y volver a crear».
10. Para probar rápido, activa «Borrador rápido» en Más opciones: sale a mitad de tamaño. El resultado siempre es un borrador que tú revisas antes de publicar.
Para cerrar la app: Control + C en la Terminal.

### Tus datos y los textos legales
- Al crear la cuenta lees y **marcas tú** la casilla de privacidad y términos (nunca viene marcada). Los cuatro textos (privacidad, términos, reembolsos, cookies) están abajo de cada pantalla y en el menú de tu avatar. **Son un borrador: que los revise una persona de derecho de tu país antes de usarlos con clientes.**
- Menú de tu avatar → **Exportar mis datos** (descarga un archivo con tus cuentas, videos y ajustes; nunca contraseñas ni claves) y **Eliminar mi cuenta** (pide tu contraseña y te deja borrar también tus videos, referencias y música).
- Iris no cobra nada. Lo único que puede costar dinero es la IA de Anthropic (se muestra antes de crear cada video). Lista completa de lo que hace Iris con cada punto de privacidad y accesibilidad: [CUMPLIMIENTO.md](CUMPLIMIENTO.md).

### Pasar Iris al celular (Android, por cable)
1. En el Mac, una vez: `brew install --cask android-platform-tools`.
2. En el celular: Ajustes → Acerca del teléfono → toca 7 veces «Número de compilación»; luego Opciones de desarrollador → activa «Depuración por USB».
3. Conecta el cable, acepta el aviso del celular («Permitir depuración por USB») y ejecuta en el Mac: `./creador celular`.
4. El celular abre Iris por el cable. En Chrome: menú ⋮ → «Añadir a la pantalla de inicio». Deja la Terminal abierta mientras lo uses.
Con **iPhone** no hay una vía equivalente por cable que mantenga Iris solo en tu computador: dime si quieres una versión instalable y la preparamos.

## 8. Crear un video desde la Terminal (avanzado)
1. Pon tu toma (la persona hablando a cámara) en `empresas/<empresa>/videos/propios/` y analízala: `./creador analizar --empresa <empresa>`.
2. Crea el guion borrador: `./creador guion toma1.mp4 --empresa <empresa>`. Ya trae subtítulos palabra por palabra y acercamientos. Se guarda en `empresas/<empresa>/formatos/toma1.json`.
3. Ábrelo y ajusta: palabras importantes en `claves`, correcciones de lo que la transcripción entendió mal, y capas (contadores, insignias, tarjetas). Si quieres ideas de qué poner, pídeme un guion de una de las ideas de `02-empresas/<empresa>/ideas/`.
4. Genera el video: `./creador render toma1 --empresa <empresa>`. Queda en `empresas/<empresa>/salidas/toma1.mp4`. Para ajustarlo viéndolo en el navegador: `./creador estudio toma1 --empresa <empresa>`.
Para ver qué piezas existen, prueba los ejemplos: `./creador render remotion/ejemplos/estilo-completo.json --empresa al-volante` (los otros: `elementos`, `antes-despues`, `tutorial-pantalla`).

## 9. Cada día
`git pull` → trabajar → `./creador informe` si cambió algo en las métricas → `./creador validar` → `git add -A && git commit -m "..." && git push`.

## Si algo falla
| Qué ves | Qué hacer |
|---|---|
| Cualquier cosa rara | `./creador probar` y seguir lo que diga |
| La página de la app dice «No puedo hablar con Iris» | La ventana de la Terminal con `./creador app` se cerró: ábrela de nuevo |
| «Demasiados intentos» al entrar | Espera los minutos que indica, o restablece la contraseña con `./creador cuenta restablecer` |
| Un video de la app queda en «interrumpido» | Se cerró la app mientras trabajaba (o el archivo del video se borró): pulsa «Intentar de nuevo» |
| «Sin IA: …» en las notas de un video | La IA falló por la razón que dice (clave, saldo, internet): el video salió igual con reglas. Revisa «Director con IA…» en el menú de tu avatar |
| El informe de calidad dice «licencia sin confirmar» | Declara la licencia de esa canción en la sección Música; si no la tienes, no publiques ese video |
| El informe de calidad pide la autorización de los padres | Hay niños en la marca o en el video: pulsa «Confirmo que tengo la autorización de los padres» en la tarjeta del video (no hace falta volver a crearlo) |
| «Falta confirmar qué datos se envían…» | Menú de tu avatar → «Director con IA…» y marca la casilla de confirmación; mientras tanto el video sale con reglas |
| «Lo que pediste» dice «no» en la calculadora | No se oyeron cifras claras (o no se dijeron en voz alta): di los montos con el número completo, por ejemplo «ocho millones quinientos mil» |
| El logo no aparece | Sube el logo de esa marca (botón «Logo» en la tarjeta del video) y confirma que tienes derecho a usarlo; si lo apagaste, enciende «Logo animado» |
| No puedo arrastrar para ordenar las escenas | Aún no existe arrastrar: usa «Subir» y «Bajar» en cada escena |
| Quiero un video horizontal o cuadrado | Hoy todo sale vertical 1080×1920; el cambio de tamaño aún no está hecho |
| `./creador celular` dice que no ve el celular | Revisa el cable, activa «Depuración por USB» y acepta el aviso en la pantalla del celular |
| «Falta instalar» | `./instalar.sh` |
| «Sign in to confirm you're not a bot» (YouTube) o «login required» (Instagram) | Repite con `--cookies-navegador safari` (o `chrome`) con la sesión abierta en ese navegador |
| «Your IP address is blocked» (TikTok) | Descarga el video desde el teléfono y cópialo a `videos/referencias/` |
| Una descarga que antes funcionaba deja de funcionar | Las redes cambian: `.venv/bin/pip install -U yt-dlp` |
| «Faltan archivos (rutas relativas a empresas/)» | El guion apunta a un archivo que no está: revisa el nombre y la carpeta |
| «El guion … tiene problemas» | Cada línea dice qué escena o capa y qué campo falta o está mal; corrígelo y repite |
| «ya existe y puede tener tus cambios» | `./creador guion` no pisa tus guiones: usa `--nombre otro` o `--forzar` |
| `./creador validar` muestra errores | Cada línea dice qué nota y qué falla (enlace roto, empresa mezclada, falta `tipo`…). Arregla esa nota |
| «no la toco» al generar notas | Hay una nota escrita a mano en el lugar de una generada; renómbrala |
| Obsidian no muestra las imágenes de los videos | Los fotogramas no viajan por git: `./creador analizar --forzar` con los videos en tu Mac los regenera |
