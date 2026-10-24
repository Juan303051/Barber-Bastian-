---
tipo: "investigacion"
fecha: "2026-10-24"
estado: "revisado"
fuentes: ["https://huggingface.co/rhasspy/piper-voices", "https://github.com/SYSTRAN/faster-whisper"]
---
# Cómo escribe Whisper las cifras que se dicen en voz alta

Pregunta: ¿por qué la app no reaccionaba a «cuesta ocho millones quinientos mil pesos»? Aplicación: `creador-videos/herramientas/numeros.py` y la calculadora de dinero de los videos.

## Medición
Medido el 2026-10-24 con el modelo `small` de faster-whisper (idioma español) sobre tres escenas habladas con una voz sintética en español de México (Piper, voz `es_MX-claude-high`). **Confianza media**: es una voz sintética y un solo modelo; con voces humanas puede variar y falta repetirlo con videos reales.

| Lo que se dijo | Lo que devolvió Whisper |
|---|---|
| ocho millones quinientos mil pesos | tres palabras: `8` `.500` `.000` seguidas de `pesos` |
| un millón de pesos | `un` `millón` `de` `pesos` (en letras) |
| trescientos mil pesos | `300` `mil` `pesos` (dígitos y letras) |
| siete millones quinientos mil pesos | `7` `.500` `.000` `pesos` |
| seis meses; uno o dos años (de un video real) | `seis`, `uno`, `dos` en letras |

## Consecuencias
- El contador original solo leía dígitos enteros de 100 en adelante en una sola palabra: no encontraba ninguna de estas cifras, y los subtítulos mostraban pedazos como «.500».
- `numeros.py` reúne los pedazos partidos, lee números en letras (hasta billones, «medio millón», «millón y medio»), distingue dinero, porcentaje y simple cantidad («seis meses» no es dinero) y convierte las cifras en pasos de calculadora (fijar, sumar, restar, total o solo mostrar). El resultado de cada operación lo calcula el código, nunca la IA, y se marca como «calculado por Iris» si no se dice en voz alta.
- La reunión de pedazos se hace al transcribir, así que también arregla los subtítulos.

## Qué falta
Repetir con videos de personas reales y con cifras con decimales o en otras monedas; los porcentajes sobre varios productos a la vez no se calculan.
