# DECISIONS — Iris

Cada decisión: qué, por qué y qué se descartó. Las más nuevas, arriba. D1–D7 describen cosas hechas; D8–D11, la política de textos, de opciones y de datos.

## D11 · Las pruebas de pantalla son opcionales (2026-10-24)
`pruebas_pantalla.py` usa un navegador real (Playwright) y, si se quiere, axe-core (`CREADOR_AXE`). Quien no los tiene no debe ver fallar `./creador probar`: se omiten con un aviso. Se ejecutan a mano o en una máquina que los tenga, y son la única prueba de teclado y contraste.
Descartado: hacerlas obligatorias (instalar un navegador de más de 100 MB para usar la app).

## D10 · Consentimiento y datos: la persona decide, el servidor lo exige, el aviso solo informa (2026-10-24)
- **Términos:** casilla nunca marcada de antemano; el servidor exige `acepto: true` y guarda versión y fecha (`VERSION_POLITICAS`). Si cambia la versión, se vuelve a pedir.
- **IA:** consentimiento aparte y fechado; sin él `activa` es falso y el video sale con reglas. Se muestra el costo estimado antes de crear y el gasto del mes (estimaciones, y lo dicen).
- **Cookies:** solo se usa una cookie de sesión y dos datos locales, todo imprescindible, así que el aviso informa con dos botones del mismo peso y no bloquea (criterio del ICO; si algún día hay analíticas o publicidad se cambia a consentimiento previo con «Rechazar» igual de fácil).
- **Datos propios:** exportar (sin contraseñas ni claves) y borrar la cuenta con contraseña; la última cuenta borra también logos, perfiles y `ia.json`.
- **Menores:** una marca infantil o un video que habla de niños pide una casilla de autorización de los padres; sin ella el control de calidad no lo da por listo, pero se puede confirmar después sin recrear el video.
- **Lo que no aplica** (enlace de baja de correos, cobros, reembolsos de compras) se dice como «no aplica y por qué» (D8).
Descartado: bloquear la pantalla con un muro de cookies (no hace falta y es un patrón oscuro), pedir permiso a cada paso.

## D9 · Cuánto se le pide a la persona: lo que escribe manda, los interruptores solo corrigen (2026-10-24)
Antes cada ajuste tenía un valor fijo guardado y el texto solo «sugería» con un botón; la persona sentía que nada respondía. Ahora un ajuste que la persona **no tocó** sigue lo que pidió en el texto (o el valor por defecto); uno que tocó, manda. El servidor devuelve el valor efectivo y el motivo («lo pediste en tu texto»).
Descartado: tres estados Auto/Sí/No en cada fila (demasiado ruido visual).

## D8 · Páginas legales como borrador, no como asesoría (2026-10-24)
Privacidad, términos, reembolsos y cookies se escriben para lo que Iris realmente hace (app local, sin cobros, un solo servicio externo opcional). Llevan la marca «borrador: que lo revise una persona de derecho» porque dependen del país. No se citan leyes que no se hayan verificado.
Lo que no aplica a una app local de una persona (reseñas, enlace de baja de correos, cobros) se dice como «no aplica y por qué»; no se inventan pantallas para cumplir una lista.

## D7 · El logo vive en `app/datos/marcas/`, no en `empresas/` (2026-10-24)
`empresas/` sí se sube al repositorio, que es público. El logo lo sube la persona, queda en datos privados y se enlaza a la carpeta ignorada `empresas/<marca>/videos/propios/` solo mientras dura el render.

## D6 · Efectos de sonido sintetizados con numpy (2026-10-24)
Sin bibliotecas de sonidos: no hay licencia que confirmar ni archivos que subir. Cada efecto (whoosh, tecla, caja, impacto, tic) es una fórmula determinista y se mezcla bajo la voz con el mismo nivelado final (−14 LUFS, −1 dBTP).
Descartado: descargar efectos libres (licencias variables, red).

## D5 · Transiciones solo en cortes que existen (2026-10-24)
Se colocan en los límites entre escenas y en los cortes de pausas quitadas; la IA elige el estilo, nunca el instante. Las transiciones son superposiciones sobre una sola toma continua (destello, barrido, golpe de zoom): no hay disolvencia real porque la toma base ya está unida.

## D4 · La calculadora solo usa cifras dichas (2026-10-24)
Cada operando tiene que oírse en el video (se reconocen dígitos partidos por Whisper como «8 .500 .000», «300 mil», «un millón», «ocho millones quinientos mil»). El resultado que la calculadora muestra se **calcula** a partir de lo dicho y el control de calidad lo marca como «calculado por Iris, revísalo» si no se dice en voz alta.

## D3 · Escenas: se unen antes de transcribir (2026-10-24)
Las escenas se normalizan (tamaño, fps, audio) y se unen en un solo archivo; todo lo demás (pausas, voz, dirección, render) trabaja sobre esa toma única, como ya hacía con un video. Los límites entre escenas se guardan para las transiciones.
Descartado: transcribir y renderizar escena por escena (duplica el costo y complica la sincronía).

## D2 · La IA propone, el código decide (2026-10-23)
Ver `README.md`. Es la regla que impide cifras o promesas inventadas.

## D1 · Solo `127.0.0.1` (2026-10-22)
Android entra por `adb reverse`. Para iPhone no existe una vía por cable que mantenga esa regla: queda pendiente de decisión de la persona (modo opcional por Compartir Internet por USB).
