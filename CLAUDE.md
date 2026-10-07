# CLAUDE.md — JARVIS · NEXORA

App nativa SwiftUI (Mac + iPhone 17), offline-first, para una sola persona. Documentación en `docs/`; referencia de diseño en `prototipo-web/`.

## Reglas del proyecto
- Idioma de la interfaz y la documentación: español.
- Una información, un archivo: no duplicar entre `docs/*`.
- Datos locales primero (SwiftData); la nube es opcional. Nunca claves API en el cliente.
- Los trabajos generados son borradores que el usuario revisa. No se construye ni se documenta ningún uso durante evaluaciones supervisadas.
- Claude trabaja en Linux y no puede compilar Swift: el código se escribe aquí y se compila y prueba en Xcode por el usuario. Decirlo siempre que una fase no esté verificada.
- Orden de construcción: ver `docs/ROADMAP.md`.
