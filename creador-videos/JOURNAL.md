# JOURNAL — Iris

Qué se hizo y qué se encontró, por sesión. Lo más nuevo, arriba. Solo hechos comprobados; lo no probado se dice.

## 2026-10-24 · iPhone por Wi-Fi (modo opcional)
**Pedido:** «descarga el repositorio en este celular y ponlo a correr». Desde la nube no hay acceso al celular, y un celular no puede correr Iris (Python, ffmpeg, Whisper, Remotion); se explicó y la persona eligió el modo opcional por Wi-Fi de casa.
**Hecho:** `./creador iphone` y `app/servidor/red.py` (decisión y límites: `DECISIONS.md` D12); página de emparejamiento (`app/web/emparejar.*`); aviso en pantalla cuando se usa por Wi-Fi; textos de privacidad y cookies actualizados (nueva cookie `iris_dispositivo`); `GUIA.md` y `README.md`.
**Comprobado en Linux:** `pruebas_red.py` (48): código, vencimiento, usos, bloqueo, 12 h, host y origen ajenos, dirección de Internet rechazada, nada accesible sin emparejar, emparejado ≠ sesión iniciada, y un servidor real escuchando en `127.0.0.1` y en la dirección de la red; la página del código en un navegador con pantalla de iPhone simulada (teclado en mayúsculas, sin desplazamiento horizontal, axe sin violaciones, flujo completo hasta la pantalla de entrada).
**Corregido de paso:** (1) `README.md` y `GUIA.md` decían que una escena podía ser una foto; el servidor solo acepta videos como escena (las imágenes solo valen para el logo). (2) Una comprobación de la pantalla esperaba un tiempo fijo en vez de esperar el aviso: fallaba de vez en cuando.
**Sin verificar:** un iPhone real y Safari, el cortafuegos de macOS, redes Wi-Fi que aíslan aparatos, y que «Añadir a pantalla de inicio» conserve o pida de nuevo el código (depende de iOS).

## 2026-10-24 · Segunda ronda tras probarla en el Mac
**Lo que dijo la persona:** con la clave de IA conectada la app «no tiene en cuenta casi nada del texto»; transiciones, efectos de sonido y logo animado salían como «todavía no»; algunos botones no respondían; se graba por escenas; el formato solo tenía dos opciones; faltan páginas de privacidad y cumplimiento.

**Diagnóstico (probado en Chromium con una voz sintética en español y Whisper `small`):**
- Whisper escribe las cifras habladas partidas o en letras: `8.500.000` llega como tres palabras «8», «.500», «.000»; «un millón» en letras; «300 mil». El contador solo entendía dígitos enteros ≥ 100 y nunca se activaba. También salían subtítulos rotos («.500»).
- La IA solo podía pedir cuatro tipos de momento (acercamiento, insignia, contador, tarjeta): no tenía forma de expresar calculadora, transiciones, sonidos ni logo.
- El panel «Esto entendí» lo calcula un intérprete de reglas, no la IA, y leía mal frases largas («Palabras en grande: y los valores importantes»).
- Los atajos insertaban frases sin terminar («Resalta las palabras: ») y, al pulsar otro, el texto siguiente se leía como las palabras: parecían botones muertos. Mecánicamente todos los controles responden en Chromium (sin errores de consola).
- Un video = un solo archivo.

**Hecho en esta ronda** (el detalle de cada pieza está en `README.md`, «La app Iris»; el porqué, en `DECISIONS.md` D3–D11):
- Escenas múltiples con orden, unión y respeto del giro del iPhone; formatos elegibles o decididos por Iris.
- Cifras habladas reconstruidas (`herramientas/numeros.py`) y calculadora, transiciones, efectos de sonido sintetizados y logo animado, cada uno con su interruptor; la IA puede pedirlos y el código valida cada instante y cada cifra.
- «Lo que pediste»: cada requisito se compara con el video terminado (hecho / parcial / no / omitido).
- Privacidad y cumplimiento: cuatro textos legales como borrador, aceptación sin casilla marcada, consentimiento aparte para la IA con costo estimado, exportar y borrar datos, aviso de cookies informativo, avisos de calidad para afirmaciones, reseñas y menores. Mapa de los 20 puntos: `CUMPLIMIENTO.md`.
- Interfaz: nueva jerarquía visual, controles por teclado, contraste corregido (4 fallos de axe encontrados y arreglados), aviso de cookies que ya no tapa el botón de crear.

**Comprobado en Linux:** pruebas del servidor, de cifras, de escenas, de privacidad, de audio, del director y de la API (`--completo`); Remotion (`npm run probar`, `tsc`); un video de punta a punta (3 escenas, logo, transiciones, 9 efectos, −14,0 LUFS / −1,0 dBFS); la pantalla en Chromium con axe (0 violaciones) en claro, oscuro y móvil.
**Hallazgo grave de la propia prueba (corregido):** `pruebas_direccion` importaba los datos antes de apuntar a una carpeta temporal, así que `./creador probar` escribía en la carpeta de datos **real**: pisaba los ajustes de la IA y borraba la clave guardada (`guardar_ajustes({"clave": ""})`). Ahora la carpeta temporal se fija antes de cualquier import, hay una comprobación de aislamiento en la propia prueba y se verificó con un `ia.json` de mentira que queda intacto. Si la persona ya había guardado su clave y luego ejecutó `./creador probar` con la versión anterior, la clave pudo borrarse: hay que volver a pegarla en «Director con IA».
**Otros hallazgos de la propia prueba:** el aviso de cookies tapaba el botón de envío (una animación quitaba su centrado); el texto de varios enlaces y botones no llegaba al contraste mínimo; las pruebas de IA necesitaron fijar el consentimiento después de añadirlo; el algoritmo de un efecto («whoosh») sonaba más grave de lo previsto y se recentró.
**Sin verificar:** IA real (el esquema nuevo no se ha enviado a la API de verdad), oído humano sobre mezclas y efectos, Mac y Safari, celular real, una toma de iPhone girada real, la licencia de Remotion para el negocio, la revisión legal de los textos y el punto «6 datos de…» de la lista (la imagen se cortaba; se interpretó como datos de las personas que aparecen en los videos).
**Pendiente de decidir por la persona:** cómo abrir Iris en un iPhone (hoy solo Android por cable; un modo opcional por Compartir Internet por USB relajaría la regla de `127.0.0.1`) y si el repositorio pasa a privado.
