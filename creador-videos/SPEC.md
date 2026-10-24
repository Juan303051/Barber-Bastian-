# SPEC — Iris (creador de videos)

Qué es y qué no es Iris. El cómo se usa está en `GUIA.md`; lo que ya funciona y lo que falta, en `README.md`; el porqué de cada decisión, en `DECISIONS.md`.

## Qué es
Una app local de una sola pantalla para una persona que crea videos de marketing para seis marcas. Se suben las escenas grabadas, se cuenta en texto cómo se quieren y Iris entrega un **borrador** que la persona revisa. Todo corre en el equipo; la única conexión externa opcional es la IA de Anthropic, con la clave guardada en el servidor.

## Alcance
| Dentro | Fuera (por ahora) |
|---|---|
| Varias escenas por video, unidas en orden | Publicar en redes |
| Subtítulos, calculadora de dinero, contadores, pasos, tarjetas, gancho, cierre | Estadísticas de retención y ciclo de aprendizaje |
| Transiciones, efectos de sonido sintetizados, logo animado por marca | Voz sintética propia del video |
| Música propia analizada (pulso, energía) y mezclada con la voz | Descargar música de bibliotecas |
| Director con IA que propone; el código decide | IA que inventa datos |
| Control de calidad medible (volumen, picos, negros, zonas seguras, cifras) | Juzgar el gusto |
| Cuentas locales, exportar y borrar los propios datos | Cuentas en la nube, cobros, anuncios |

## Reglas que no se negocian
1. Solo escucha en `127.0.0.1`, salvo el modo opcional del iPhone por Wi-Fi (`DECISIONS.md` D12): se enciende a mano, avisa de que no va cifrado y exige un código que solo se ve en la Terminal. Los datos viven en `app/datos/` y no se suben.
2. La IA propone y el código decide: ninguna cifra, dato o promesa que no salga del video, el brief o la ficha.
3. Si la IA falla, el video sale con reglas y se dice por qué.
4. Todo lo que se pidió en el texto aparece al final como «hecho», «parcial» o «no se pudo», con el motivo.
5. Videos, canciones, logos y claves nunca van al repositorio.
6. Interfaz en español claro; todo se puede usar con teclado.

## Criterios de aceptación de esta fase
- [x] Un video de 3 escenas con cifras habladas sale con calculadora que suma, resta y muestra el resultado, sincronizada con la voz. *(Linux, voz sintética; falta una toma real)*
- [x] Transiciones en los cortes, efectos de sonido y logo animado funcionan y se pueden apagar uno a uno. *(medido; falta oírlo)*
- [x] El formato se elige o lo decide Iris según el texto; ningún aviso «todavía no» para lo que ya existe.
- [x] Cada cosa pedida en el texto se verifica contra el video y se informa («Lo que pediste»).
- [x] Páginas de privacidad, términos, reembolsos y cookies; consentimiento al crear la cuenta; exportar y borrar datos. *(falta la revisión legal por país)*
- [x] `./creador probar` en verde y la pantalla probada en un navegador real (axe sin violaciones, teclado, móvil). *(Chromium en Linux; Safari sin probar)*
- [x] El iPhone puede usar Iris por la Wi-Fi de casa en un modo opcional con emparejamiento. *(servidor real y navegador móvil simulado en Linux; falta un iPhone real)*

## Sin verificar desde la nube
IA real (incluido el esquema nuevo de la petición), oído humano sobre las mezclas y los efectos, Mac y Safari del usuario, un iPhone y un celular reales, una toma de iPhone girada real, la licencia de Remotion para el negocio y la revisión legal de los textos. Se marcan `[x]` los criterios cumplidos *en Linux*; ninguno se da por verificado en el Mac hasta que la persona lo pruebe.
