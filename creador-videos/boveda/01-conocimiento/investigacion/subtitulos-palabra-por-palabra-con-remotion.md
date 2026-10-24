---
tipo: "investigacion"
fecha: "2026-10-23"
estado: "revisado"
fuentes: ["https://www.remotion.dev/docs/captions/create-tiktok-style-captions", "https://www.remotion.dev/docs/captions/displaying"]
---
# Subtítulos palabra por palabra con Remotion

Pregunta: cómo producir los subtítulos animados de las maquetas con nuestro propio software.

## Hallazgos
| Hallazgo | Fuente | Consultada | Confianza |
|---|---|---|---|
| `createTikTokStyleCaptions({ captions, combineTokensWithinMilliseconds })` de `@remotion/captions` agrupa palabras con tiempos en «páginas»; un valor bajo da animación palabra por palabra, uno alto mete muchas palabras por página | [Remotion](https://www.remotion.dev/docs/captions/create-tiktok-style-captions) | 2026-10-23 | alta (documentación oficial) |
| Cada `Caption` lleva `text`, `startMs`, `endMs`, `timestampMs`, `confidence`; **el texto debe incluir el espacio inicial** de cada palabra o todo se junta en una página | misma | 2026-10-23 | alta |
| `breakOnSilenceAfterMilliseconds` (desde la 4.0.514) corta página tras un silencio; `pageBreakAfter` (desde la 4.0.517) fuerza el corte; cada página trae `tokens` con `fromMs` y `toMs` para saber qué palabra está activa | misma | 2026-10-23 | alta |
| Se muestran con una `<Sequence>` por página y se resalta la palabra activa comparando el tiempo actual con `fromMs` y `toMs`; el contenedor necesita `white-space: pre` | [Remotion, «Displaying captions»](https://www.remotion.dev/docs/captions/displaying) | 2026-10-23 | alta |

## Qué hacer con esto
- Nuestra transcripción local (`./creador analizar`) ya guarda `palabras` como `[inicio, fin, palabra]` en segundos: se convierte a `Caption` multiplicando por 1000 y anteponiendo un espacio.
- Para el estilo de las maquetas: páginas de 1–3 palabras, palabra clave en tamaño mayor y color de acento, y una segunda fuente (serif cursiva) para la palabra importante.
- Hay que **corregir la transcripción** antes de renderizar: los nombres, cifras y términos técnicos salen mal (se vio en las cuatro maquetas).

## Qué falta por verificar
Probar la tipografía y la sincronía con voz real de una empresa; el rendimiento con videos largos.
