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
3. **Referencias:** suelta uno o varios videos que te gusten (o pega un enlace; si la red no deja descargarlo, sube el archivo). Iris aprende su ritmo.
4. **Tus videos:** suelta la toma, escribe qué quieres con tus palabras (por ejemplo «subtítulos dinámicos, resalta dinero y gratis, quita las pausas y cierra pidiendo que comenten EDITOR») y mira «Esto entendí»: ahí ves qué hará y qué no puede hacer todavía. Los botones de abajo escriben frases por ti.
5. Pulsa **Crear video** (o «Crear N videos» arriba para todos a la vez). Verás el video construyéndose. Cuando termine, mira el resultado y descárgalo. Si algo no te gusta, «Cambiar y volver a crear».
6. Para probar rápido, activa «Borrador rápido» en Opciones avanzadas: sale a mitad de tamaño. El resultado siempre es un borrador que tú revisas antes de publicar.
Para cerrar la app: Control + C en la Terminal.

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
| Un video de la app queda en «interrumpido» | Se cerró la app mientras trabajaba: pulsa «Intentar de nuevo» |
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
