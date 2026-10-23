---
tipo: "investigacion"
fecha: "2026-10-23"
estado: "revisado"
fuentes: ["https://www.diyphotography.net/?p=274734", "https://aejuice.com/blog/how-to-3d-track-text-in-after-effects", "https://blog.motionarray.com/learn/davinci-resolve/text-behind-objects-in-davinci-resolve/", "https://www.rippletraining.com/?p=285734", "https://creativevideotips.com/tutorials/magic-mask-2-hack-for-better-edges", "https://www.capcut.com/resource/how-to-put-text-behind-a-person-in-capcut", "https://www.tourboxtech.com/en/news/how-to-put-text-behind-a-person-in-capcut.html"]
---
# Texto en la escena: seguimiento 3D y texto detrás de la persona

Pregunta: cómo se consigue el texto «pegado» al suelo, a la pared o detrás de la persona que se ve en [[02-empresas/maquetas-estilo/analisis/kevinvelasquez-tour-casa]] y [[02-empresas/maquetas-estilo/analisis/sandeep-realtor-contenido]].

## Hallazgos
| Hallazgo | Fuente | Consultada | Confianza |
|---|---|---|---|
| **After Effects:** analizar la toma con el seguimiento 3D de cámara, elegir un grupo de puntos sobre una superficie plana y crear texto y cámara; para poner a la persona delante, duplicar la toma, colocarla sobre el texto y recortar con Roto Brush | [DIY Photography](https://www.diyphotography.net/?p=274734) | 2026-10-23 | media (tutorial de la época de CS6) |
| Añadir luces ambientales y focales para que el texto parezca iluminado por la escena | [AEJuice](https://aejuice.com/blog/how-to-3d-track-text-in-after-effects) | 2026-10-23 | media |
| **DaVinci Resolve:** «sándwich de texto»: el texto entre la toma original y un duplicado recortado de la persona, con salida alfa; enmascarar solo donde se solapan | [Motion Array](https://blog.motionarray.com/learn/davinci-resolve/text-behind-objects-in-davinci-resolve/) | 2026-10-23 | media (guía para Resolve 17) |
| El recorte automático (Magic Mask) es de la versión Studio; el seguimiento de planos del propio Resolve es menos maduro y pide correcciones a mano | [Ripple Training](https://www.rippletraining.com/?p=285734), [4K Shooters](https://4kshooters.net/2018/03/29/how-to-easily-reveal-text-logos-from-behind-an-object-in-davinci-resolve-14) | 2026-10-23 | media |
| Si los bordes del recorte «tiemblan» en sujetos pequeños, ampliar la toma, recortar y reducir de nuevo | [Creative Video Tips](https://creativevideotips.com/tutorials/magic-mask-2-hack-for-better-edges) | 2026-10-23 | media |
| **CapCut:** el mismo sándwich con el recorte automático de persona, texto entre el video y la capa recortada | [CapCut](https://www.capcut.com/resource/how-to-put-text-behind-a-person-in-capcut), [TourBox](https://www.tourboxtech.com/en/news/how-to-put-text-behind-a-person-in-capcut.html) | 2026-10-23 | media |

## Qué hacer con esto
- El método es el mismo en las tres herramientas: **texto en medio de dos capas, la de arriba con la persona recortada.**
- Para el texto pegado al suelo hace falta seguimiento 3D (After Effects o Fusion en Resolve) y una toma con parallax y textura: no sirve en una toma estática y lisa.
- Sin automatizar en Remotion por ahora: se hace en el editor y se importa el resultado, o se explora un modelo de recorte de personas (pendiente de probar).

## Qué falta por verificar
Versiones actuales de cada programa (las guías son antiguas); calidad de un recorte automático por modelo sobre las tomas reales de cada empresa.
