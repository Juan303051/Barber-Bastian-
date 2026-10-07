# Funciones

## 1. Jarvis (voz)

- **Activación por palabra clave "Jarvis"**, procesada en el dispositivo.
  - **Mac:** siempre activo mientras la app corre (se inicia con el sistema).
  - **iPhone:** Apple no permite que una app de terceros escuche en segundo plano de forma permanente. Se activa con el **Botón de Acción**, un atajo de Shortcuts, el widget de pantalla bloqueada o "Oye Siri, Jarvis". Con la app abierta sí escucha la palabra clave.
- Funciona con **AirPods/audífonos**: recibe la voz y responde por el mismo canal.
- Comandos de ejemplo: "Jarvis, ¿qué tengo hoy?", "añade recordatorio mañana 3 pm entregar informe", "reorganiza mi día", "tómame lección de cálculo".
- Respuesta hablada y en pantalla. Si no hay internet, usa el modelo local.

## 2. Despertar y rutina diaria

- **Alarma a las 6:00 am** (configurable) con notificaciones locales y alarma de iOS; en el Mac, notificación + voz de Jarvis.
- **Resumen matutino:** clima (si hay internet), clases del día, entregas próximas, plan sugerido.
- **Cierre del día:** qué se hizo, qué se mueve a mañana, repaso corto de lo visto en clase.
- Recordatorios con voz o texto, repetitivos o únicos.

## 3. Organizar el día (NEXORA)

- Tareas, metas, hábitos, finanzas, enfoque (Pomodoro), círculo de personas.
- Botón **Organizar mi día**: ordena por urgencia, importancia y tiempo estimado; explica el porqué.
- **Intensidad dinámica:** la carga del día se mide en puntos (tareas × duración × prioridad). Con carga baja Jarvis te empuja a avanzar; con carga alta recorta lo no esencial, agenda descansos y baja el tono.
- Flujo visual **AHORA → SIGUIENTE → DESPUÉS → LUEGO → COMPLETADO**.

## 4. Modo Estudiante

- **Horario de clases** y calendario académico (importable desde calendario o a mano).
- **Materias**: profesor, créditos, notas, porcentaje de cada corte, nota necesaria para aprobar.
- **Entregas y parciales**: fechas, peso, plan de preparación hacia atrás.
- **Temas vistos en clase**: después de cada clase dices o escribes "hoy vimos…" y Jarvis actualiza su memoria de la materia. Esto se acumula y es la base de todo lo demás.
- **Apuntes y archivos**: importa PDF, fotos de cuaderno (OCR), documentos. Todo indexado localmente para buscar y preguntar.
- **Repaso espaciado**: tarjetas y preguntas generadas desde tus apuntes, programadas con repetición espaciada.
- **Tómame lección / simulacros** por materia y tema, con corrección y explicación.
- **Sesiones de enfoque** ligadas a materia; racha de estudio; horas por materia.
- **Explicar y practicar**: explica un tema con tus propios apuntes, resuelve ejercicios paso a paso.

## 5. Taller de documentos

Flujo: subes enunciado/rúbrica → eliges materia → Jarvis usa tus apuntes y tu perfil (nombre, carrera, universidad, código, profesor, formato) → genera un **borrador** con portada, estructura, contenido y referencias → lo revisas, lo editas y lo exportas (PDF/Word/Pages).

- Plantillas de portada y normas de formato (APA, etc.).
- Marca de borrador y checklist de revisión (datos, fuentes, que entiendas cada parte).
- Los textos generados quedan guardados con su historial de versiones.

## 6. Memoria personal

Jarvis conoce: perfil, carrera, materias, horarios, hábitos, metas, preferencias de estudio, personas, fechas importantes. Todo se guarda **en el dispositivo**; tú puedes ver, editar y borrar cada dato.

## 7. Guía de usuario integrada

Sección "Ayuda": tour inicial, "¿cómo hago X?", y Jarvis responde dudas sobre la propia app usando [`GUIA_USUARIO.md`](GUIA_USUARIO.md).

## 8. Offline y actualización

- Sin internet: todo lo local sigue funcionando (agenda, alarmas, apuntes, repaso, IA local).
- Con internet: se sincroniza vía iCloud, se actualiza la información y se puede usar un modelo en la nube para tareas pesadas (documentos largos).
- Actualización continua del conocimiento: cada tema nuevo visto en clase entra al índice y a las tarjetas de repaso.
