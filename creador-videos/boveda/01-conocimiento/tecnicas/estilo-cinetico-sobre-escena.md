---
tipo: "conocimiento"
fecha: "2026-10-23"
confianza: "media"
fuentes_internas: ["maquetas-estilo"]
---
# Estilo cinético sobre escena

Receta común a las cuatro maquetas enviadas: una persona real habla a cámara (o recorre un lugar) y **cada idea tiene su propia pieza visual** —palabra gigante, tarjeta, número, mira— integrada en la escena. Lecturas detalladas:
[[02-empresas/maquetas-estilo/analisis/jeann-antes-despues]] · [[02-empresas/maquetas-estilo/analisis/kevinvelasquez-tour-casa]] · [[02-empresas/maquetas-estilo/analisis/dreomar-invideo-claude]] · [[02-empresas/maquetas-estilo/analisis/sandeep-realtor-contenido]]

> Son **4 videos**: lo que sigue son pistas, no leyes. Ninguno trae métricas públicas, así que «por qué funcionó» es hipótesis.

## Lo medido en los cuatro
| Video | Duración | Palabras/min | Cortes/10 s | Volumen | Gancho | CTA |
|---|---|---|---|---|---|---|
| @jeann_content | 87 s | 211 | 0.2 (toma continua con capas) | −14.1 LUFS | Pregunta de un seguidor | Comenta «Masterclass» |
| @kevinvelasquez_ | 88 s | 65 | 4.5 (a ráfagas) | −14.5 LUFS | Paradoja de marca | «Escríbeme y agendemos» |
| @dreomar | 40 s | 175 | 4.2 (3 tempos) | −14.1 LUFS | Resultado primero | Comenta «EDITOR» |
| @sandeep_rajkumar19 | 19 s | 188 | 1.6 (acción en los gráficos) | −13.5 LUFS | Pregunta a un público | «DM us» |

Constantes: volumen medio de **−14 LUFS** en los cuatro (picos entre −0.6 y +0.7 dBFS, al límite), subtítulos en el centro, **un color de acento por idea**, una sola persona, y un cierre con llamada a la acción. La tarjeta final y el usuario en las esquinas **no son edición**: son la marca de agua que Instagram añade al guardar un reel.

## Ingredientes y qué se puede automatizar
| Ingrediente | Dónde se ve | Con Remotion |
|---|---|---|
| Subtítulos palabra por palabra, palabra clave grande y de otro color | los cuatro | Automático: transcripción con tiempos por palabra → [[01-conocimiento/investigacion/subtitulos-palabra-por-palabra-con-remotion]] |
| Pareja tipográfica: sans gruesa para el texto base + serif cursiva para la palabra importante | @sandeep, @kevin | Automático |
| Insignias numeradas (1., 2., 3.) y contadores de cifras | @jeann | Automático |
| Tarjetas flotantes (fotos, comentarios con cifras, notificaciones, «Síguenos») | @jeann, @sandeep, @kevin | Automático; las cifras deben ser reales |
| Pantalla dividida «antes / después» | @jeann | Automático |
| Grabación de pantalla flotante con recuadro de foco y zoom | @dreomar | Automático (zoom y recuadro), con la grabación del cliente |
| Mira o aro con etiqueta alrededor de la cabeza | @sandeep | Semiautomático (posición fija; seguir la cara exige detección) |
| Texto curvado sobre una trayectoria | @kevin, @dreomar, @sandeep | Semiautomático (texto sobre trazado) |
| Montaje a ráfagas sobre la música | @kevin, @dreomar | Semiautomático: detectar el pulso de la música y generar la lista de cortes |
| Texto en perspectiva pegado al suelo o a la pared | @kevin, @sandeep | **Manual:** requiere seguimiento 3D → [[01-conocimiento/investigacion/texto-en-escena-seguimiento-y-mascaras]] |
| Texto detrás de la persona | @kevin, @dreomar | **Manual o con un modelo de recorte:** capa de texto entre el video y una copia recortada de la persona |
| Transiciones con desenfoque de movimiento (barridos) | @kevin, @dreomar | Semiautomático; mejor con la toma pensada para el barrido |
| Línea de tiempo del editor visible bajo el video | @kevin | Manual: captura de pantalla del proyecto |
| CTA con palabra clave + mensaje automático | @jeann, @dreomar | El texto sí; el mensaje automático es una herramienta externa → [[01-conocimiento/investigacion/cta-comenta-una-palabra-y-mensaje-automatico]] |

## Qué ya está construido en Remotion
Subtítulos palabra por palabra con claves y serif · insignias numeradas · contadores · tarjetas (comentario, notificación, estadística, foto) · pantalla dividida «antes / después» · grabación de pantalla flotante con zoom y recuadros de foco · mira con etiqueta · texto curvo (arco y onda) · palabra gigante extruida · cierre con palabra clave · acercamientos en la toma base. Los nombres de cada pieza en el guion y sus campos están en el README de `creador-videos`. Falta construir: la mira que siga la cara, las transiciones con desenfoque de movimiento y el montaje sobre el pulso de la música. Siguen siendo manuales: el texto pegado al suelo y el texto detrás de la persona.

## Cuatro formatos base
**F1 · Antes y después** (de @jeann). Pantalla dividida: toma cruda pequeña a la izquierda, resultado editado grande a la derecha. Sirve para consejos con prueba y para mostrar la edición. Estructura: pregunta (0–3 s) → promesa → lista numerada con una prueba con cifra → oferta → CTA con palabra clave. Graba: una toma continua de 60–90 s.

**F2 · Texto en escena** (de @kevin y @sandeep). La persona camina o recorre un espacio y las palabras viven en el lugar. Sirve para tiendas, productos, rutas y tours. Estructura: gancho que nombra al público o plantea una paradoja (0–3 s) → una idea por frase, cada una con su visual literal → prueba (detalle o dato) → cierre en plano más tranquilo. Graba: caminata con estabilizador, tomas de detalle, una toma sentada para el cierre, y opcionalmente dron.

**F3 · Tutorial en pantalla con foco** (de @dreomar). Resultado primero (5–7 s), grabación de pantalla sin cortes con recuadro de foco (15–20 s), resultado otra vez y CTA. Sirve para trámites, apps, configuradores y procesos. Graba: grabación de pantalla y una toma a cámara.

**F4 · Línea de tiempo visible** (de @kevin). El video terminado arriba y su línea de tiempo real debajo. Sirve para la **marca personal del creador** («así se hizo»), no para las empresas.

## Reglas de trabajo (hipótesis a probar)
1. **Gancho en 3 s con texto legible**, que nombre a quién habla o plantee una paradoja o un resultado.
2. **Una idea, una pieza visual** y un solo color de acento fuerte por idea.
3. **Voz según la emoción:** educación o servicios, 175–210 palabras por minuto; lujo y calma, unas 65 con música que respire.
4. **Un insert cada 3–6 s** en videos de una sola toma; ráfagas de cortes (≈0.3 s) solo en 2–3 momentos para marcar el pulso, el resto planos largos.
5. **Nunca tapar la cara** con texto; subtítulos al centro, cifras y tarjetas junto a las manos.
6. **Volumen en torno a −14 LUFS** y pico máximo −1 dBFS (los cuatro ejemplos llegan a 0: margen para distorsión). Recomendación mía, a comprobar al exportar.
7. **CTA con palabra clave** corta, repetida del gancho al cierre cuando se pueda, y solo si hay algo real que entregar después.
8. **Que el texto no sea todo el video:** Instagram dice reducir la visibilidad de reels «mayormente texto» → [[01-conocimiento/investigacion/como-rankea-instagram-reels]]. En los cuatro ejemplos siempre hay una persona o un lugar visibles.

## Qué no copiar
- Marca de agua de descarga, usuario en esquinas y tarjeta final.
- Cifras, capturas de ingresos o tarjetas de «353K views» que no sean verdaderas.
- Marcas de terceros sin relación comercial.

## Lo que no sabemos
Alcance y retención de estos videos, cuánto debe a la cuenta y no al formato, y si funciona igual en las industrias de las seis empresas. Medirlo con las estadísticas propias de cada cuenta (retención por segundo, envíos, comentarios) es la única prueba válida.
