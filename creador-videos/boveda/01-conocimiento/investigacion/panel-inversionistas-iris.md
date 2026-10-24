---
tipo: "investigacion"
fecha: "2026-10-24"
estado: "revisado"
fuentes: ["https://submagic.co/pricing", "https://www.opus.pro/pricing", "https://ads.tiktok.com/business/en-US/blog/audio-library-royalty-free-music", "https://www.remotion.dev/docs/license"]
---
# Panel de inversionistas: la idea de Iris, criticada sin piedad

Formato «Shark Tank»: cinco inversionistas que **no quieren que la idea salga bien**, cada uno con su pregunta más incómoda, una respuesta honesta y **lo que se cambió en la app por esa crítica**. Los hechos de mercado salen de páginas públicas de precios (leídas el 2026-10-24); los costos de la IA son **estimaciones**, no mediciones (no hay una clave de IA en la nube de Claude para medirlos).

## Los hechos del mercado
| Competidor | Precio público | Qué hace (según su propia página) | Fuente |
|---|---|---|---|
| Submagic | Inicial 19 USD/mes (15 videos de hasta 2 min), Pro 39 USD (40 videos, 5 min), Business 69 USD (100 videos, 30 min); anual ≈ 12 / 23 / 41 USD | Subtítulos animados, limpieza de audio, quitar silencios y malas tomas, títulos de gancho con IA, b-roll y audio gratuitos, plantillas de marca | [Submagic](https://submagic.co/pricing) |
| OpusClip | Gratis (con marca de agua), Inicial 15 USD/mes, Pro 29 USD, Business a medida | Cortes con IA, gancho automático, limpieza del habla, transiciones, efectos de sonido con IA, b-roll con IA, plantillas de marca, exportar a Premiere y DaVinci, API | [OpusClip](https://www.opus.pro/pricing) |
| Costo por video en Submagic Pro | 39 USD ÷ 40 videos ≈ **0,98 USD** (mensual) o ≈ 0,58 USD (anual) | — | cálculo propio |

**Lectura:** subtítulos animados, quitar silencios, ganchos con IA y plantillas de marca **ya son mercancía** por menos de 40 USD al mes. Competir ahí es perder.

## Los cinco inversionistas

### 1. El de los números — «¿Dónde está el negocio?»
- **Crítica:** «Tienes una herramienta, no una empresa. Submagic y OpusClip cobran 15–69 USD y ya hacen lo que hace tu app. ¿Por qué alguien te pagaría?»
- **Respuesta honesta:** como producto para vender, hoy **no hay foso**. Como herramienta para **un creador que atiende seis marcas**, el valor es otro: horas ahorradas × tarifa por hora, y consistencia de marca. El costo de la IA por video es bajo: con 3 000 palabras de contexto y un razonamiento de 3 000–8 000 tokens, **unos 0,05–0,20 USD por video con Claude Opus 5.5 (4 USD / 20 USD por millón de tokens) y la mitad con Sonnet 5.5 (2 / 10)**; el render corre en el Mac, sin costo de nube. Estimación sin medir.
- **Lo que cambié:** la app muestra el **costo estimado de la IA de cada video** y permite elegir el modelo económico; la IA se puede apagar y todo sigue funcionando con reglas.

### 2. La directora creativa — «Esto se va a ver igual que todo lo demás»
- **Crítica:** «Subtítulos grandes al centro y zoom cada dos frases es el look de cualquier app. Un director con 20 años no corta por reglas: corta por intención. Y las maquetas que me enseñaste tienen texto detrás de la persona y texto pegado al suelo; tu app no lo hace.»
- **Respuesta honesta:** correcto en las dos cosas. **No hay forma honesta de prometer calidad de director senior con reglas, ni con una IA que no ve el material.** Lo que sí se puede hacer es ponerle al sistema lo que un director tendría: el brief de la marca, su ficha de la bóveda, el guion hablado con tiempos, una prueba de cómo quiere el ritmo la persona y, **si lo permite**, algunos fotogramas del material. Y un control que mida lo medible. El texto detrás de la persona y el texto en 3D siguen **manuales**.
- **Lo que cambié:** un **director con IA** (Claude, desde el servidor) que propone el concepto, el gancho, las palabras clave, los momentos de énfasis y el acabado, **dentro de límites que el código hace cumplir**; una **entrevista de marca** («test del director»); el **acabado de color** y el pulso sutil sobre la música; y un **control de calidad** con avisos concretos. No hay efectos que no pueda comprobar.

### 3. El abogado — «Esto te va a costar una demanda»
- **Crítica:** «Usas canciones. Las bibliotecas de las plataformas no son para anuncios de marca, y tus referencias son videos de otros creadores.»
- **Respuesta honesta:** TikTok lo dice claro: su biblioteca general **no** está liberada para contenido de marca y usarla es «riesgo de infracción de derechos de autor»; su Commercial Music Library (más de 600 000 pistas) sí, solo para cuentas de empresa y dentro de TikTok. Para Instagram no encontré texto oficial sobre anuncios pagados. La app **no puede saber** si una canción tiene licencia. Las referencias se usan **solo para medir ritmo y voz**, nunca se republican; el repositorio es público y los videos no se suben.
- **Lo que cambié:** cada canción pide **declarar su licencia** (propia, licenciada, biblioteca de plataforma, sin confirmar); si está «sin confirmar», el video sale marcado como **borrador no publicable** y el control de calidad lo dice. **Ninguna canción se sube al repositorio.** Además, la IA **no puede inventar cifras ni promesas**: todo número o dato que aparezca en pantalla tiene que estar en lo que dijo la persona o en el brief; las palabras que la marca nunca usa se bloquean.

### 4. La de distribución — «¿Y el día después de crear el video?»
- **Crítica:** «Crear un video es el 20 % del trabajo. Publicarlo, medir y aprender cuál gancho retiene es el 80 %. Sin ese ciclo, no mejoras nunca.»
- **Respuesta honesta:** tiene razón y **eso no está construido**: no hay publicación, ni importación de estadísticas, ni pruebas A/B reales. Lo único que sí hay es base para ello: cada video guarda qué plan, qué gancho y qué música usó.
- **Lo que cambié:** el plan de cada video queda guardado (concepto, tipo de gancho, música y acabado) para poder compararlo con las estadísticas de cada plataforma cuando se importen. **Queda en la hoja de ruta:** importar estadísticas de retención a 3 s y 10 s y proponer el siguiente gancho según lo que funcionó en esa marca.

### 5. El técnico — «¿Y si se cae a las 2 de la mañana con 40 videos en cola?»
- **Crítica:** «Una app local con un solo hilo, en el computador de una persona, sin copias de seguridad, con claves de IA guardadas en un archivo.»
- **Respuesta honesta:** es lo que corresponde a **un usuario**; escalar a un equipo exige renderizar en la nube y una licencia de Remotion (gratuita para empresas de hasta 3 empleados; más grande, pago). La clave de IA es el punto más delicado.
- **Lo que cambié:** la clave **nunca viaja al navegador ni se devuelve**; se lee de una variable de entorno o de un archivo con permisos solo de lectura para quien lo creó, fuera del repositorio; el servidor solo escucha en `127.0.0.1`; y **si la IA falla (clave inválida, sin conexión, saldo, rechazo), el video se hace igual con reglas** y se explica por qué. Lo enviado a la IA se declara: guion con tiempos, ficha de la marca y, solo si se activa, 6 imágenes pequeñas.

## Veredicto del panel
«**Oferta condicionada.** No inviertan en esto como producto de software para vender: ya existe y es más barato. Sí tiene sentido como **taller propio de un creador con varias marcas**, si cumple tres condiciones: (1) que **mida la calidad en vez de prometerla**; (2) que **no meta riesgo legal** a los clientes con música o promesas inventadas; (3) que **aprenda de las estadísticas**. Hoy cumple la (1) y la (2) en lo que se puede automatizar; la (3) está pendiente.»

## Lo que sigue sin existir (dicho sin adornos)
- Calidad de director senior garantizada: **no se puede garantizar**; se acerca con brief, memoria de marca, medición y revisión humana.
- Texto detrás de la persona, texto en 3D pegado a superficies, transiciones con desenfoque y efectos de sonido: **manuales** por ahora.
- Publicación automática, importación de estadísticas y pruebas A/B con datos reales.
- Pasar la app al celular: una app local no vive en el teléfono; el paso real es una app web instalable con servidor propio o una app nativa.
