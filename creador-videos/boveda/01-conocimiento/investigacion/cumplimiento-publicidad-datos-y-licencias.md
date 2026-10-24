---
tipo: "investigacion"
fecha: "2026-10-24"
estado: "revisado"
fuentes: ["https://www.ftc.gov/reports/bringing-dark-patterns-light", "https://www.ftc.gov/news-events/news/press-releases/2024/08/federal-trade-commission-announces-final-rule-banning-fake-reviews-testimonials", "https://www.ftc.gov/business-guidance/resources/complying-coppa-frequently-asked-questions", "https://ico.org.uk/about-the-ico/media-centre/news-and-blogs/2025/09/fact-vs-fiction-ico-debunks-myths-on-storage-and-access-technologies", "https://www.remotion.dev/docs/telemetry", "https://www.remotion.dev/docs/license/faq", "https://www.anthropic.com/legal/privacy"]
---
# Cumplimiento para una app de videos de marketing: patrones oscuros, reseñas, cobros, menores, cookies, datos y licencias

Pregunta: qué obligaciones y buenas prácticas tocan a Iris (una app local de una persona que crea publicidad para seis marcas) y cómo se reflejan en la pantalla. Aplicación: textos en `creador-videos/app/web/legal/`, consentimientos, exportar y borrar datos, avisos del control de calidad. La lista de lo pedido y dónde está cada cosa está en `creador-videos/CUMPLIMIENTO.md`.

**No es asesoría legal.** Son lecturas de fuentes oficiales y de segunda mano; las leyes cambian según el país y el texto debe revisarlo una persona de derecho. Consultado el 2026-10-24.

## Hallazgos
| Tema | Qué se encontró | Fuente | Confianza |
|---|---|---|---|
| Patrones oscuros | La Comisión Federal de Comercio de EE. UU. (FTC) publicó en septiembre de 2022 el informe «Bringing Dark Patterns to Light». La página confirma el título y la fecha, pero **no se leyó el PDF**, así que las categorías concretas no están verificadas aquí | [FTC](https://www.ftc.gov/reports/bringing-dark-patterns-light) | media (fecha) · baja (categorías) |
| Reseñas y testimonios falsos | La FTC aprobó el 14 de agosto de 2024 una norma final que prohíbe reseñas y testimonios falsos o de personas que no existen (incluidos los generados por IA), pagar por reseñas positivas o negativas, que personas de la empresa los publiquen sin revelar el vínculo y comprar seguidores falsos; en vigor desde el 21 de octubre de 2024. Verificar su estado actual | [FTC · comunicado](https://www.ftc.gov/news-events/news/press-releases/2024/08/federal-trade-commission-announces-final-rule-banning-fake-reviews-testimonials) y resúmenes de despachos de abogados | media |
| Cargos ocultos | La norma final de la FTC sobre cuotas desleales o engañosas (17 de diciembre de 2024) quedó **limitada a entradas a eventos en vivo y alojamiento de corta estancia**: exige mostrar el precio total con las tarifas obligatorias de forma más destacada que cualquier otro precio. No aplica a Iris, pero el principio (precio total antes de aceptar) se adopta | resúmenes de despachos de abogados (Reed Smith, Foley) | media |
| Menores y videos | La regla COPPA protege a menores de 13 años y exige consentimiento verificable de los padres **antes de recoger datos personales en línea de niños**. Fotos, videos y audios con la imagen o la voz de un niño cuentan como datos personales. Las preguntas frecuentes no tratan directamente a una empresa que produce sus propios videos con niños; las autoridades sugieren consultar a un abogado. Opiniones del personal de la FTC, no posiciones vinculantes | [FTC · preguntas frecuentes de COPPA](https://www.ftc.gov/business-guidance/resources/complying-coppa-frequently-asked-questions) | alta (lo que dice) · media (cómo aplica a Iris) |
| Cookies imprescindibles | La autoridad británica (ICO) explica que lo «estrictamente necesario» se juzga desde la perspectiva de la persona: sin eso no se puede prestar el servicio pedido; las cookies de sesión de acceso y de seguridad son ejemplos; analíticas y publicidad no entran. Su página de excepciones dio 404; se usaron su nota de septiembre de 2025 y resúmenes, y una fuente menciona una guía revisada el 29 de abril de 2026 sin confirmarla | [ICO](https://ico.org.uk/about-the-ico/media-centre/news-and-blogs/2025/09/fact-vs-fiction-ico-debunks-myths-on-storage-and-access-technologies) | media |
| Remotion: licencia | Gratis para personas, organizaciones con fines de lucro de hasta 3 empleados y organizaciones sin fines de lucro; las demás necesitan licencia de empresa. Existen planes de pago para creadores (por puesto) y para automatización (por render). El repositorio avisa de que la licencia cambiará en la versión 5 | [Remotion · preguntas frecuentes](https://www.remotion.dev/docs/license/faq) | media |
| Remotion: telemetría | Para renders en servidor la telemetría va ligada a la opción `licenseKey` (envía la clave, la IP y si el render es de video o imagen; no el contenido). Iris no pasa ninguna clave, así que no reporta. No se encontró documentación explícita de un render local por línea de comandos sin clave | [Remotion · telemetría](https://www.remotion.dev/docs/telemetry) | media |
| Hugging Face | La variable `HF_HUB_DISABLE_TELEMETRY=1` desactiva la telemetría opcional de la biblioteca; Iris la fija antes de descargar el modelo de voz. La fuente es una copia del código en un tercero | resultados de búsqueda | baja |
| Anthropic | La política de privacidad (vigente desde el 10 de septiembre de 2026) dice que no cubre el contenido que procesan por cuenta de clientes de sus ofertas de negocio: eso se rige por los acuerdos con el cliente. Por eso el texto de Iris remite a los términos de la cuenta de API de la persona | [Anthropic](https://www.anthropic.com/legal/privacy) | alta |

## Lo que se aplicó en Iris
- Tabla de datos con finalidad y plazo, tabla de terceros con lo que reciben y lo que no, y aviso de borrador en las cuatro páginas (privacidad, términos, reembolsos y cookies).
- Casilla de aceptación **nunca marcada** al crear cuenta; consentimiento aparte, con fecha, para enviar datos a la IA; la IA no recibe nada sin él.
- Exportar todos los datos de la persona y borrar la cuenta con o sin el resto de los datos.
- Aviso de cookies informativo con botones del mismo peso (solo hay una cookie imprescindible).
- Costo estimado antes de crear un video y gasto del mes en los ajustes de la IA.
- Control de calidad: avisa de afirmaciones que piden respaldo («garantizado», «el mejor», «sin riesgo»…), de tarjetas con aspecto de comentario de cliente y de menores sin la autorización de los padres.
- Prueba automática de que la página no carga nada de otros sitios.

## Qué falta
Revisión legal de los textos para el país de la persona; confirmar con Remotion si el uso encaja en la licencia gratuita; leer el informe completo de patrones oscuros de la FTC.
