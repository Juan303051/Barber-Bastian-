# Arquitectura

## Plataformas

- **iOS 26+ (iPhone 17)** y **macOS 26+**, una sola base de código SwiftUI multiplataforma.
- Lenguaje: Swift 6. IDE: Xcode.

## Capas

```
UI (SwiftUI)  ─ Hoy · Estudio · Taller · Jarvis · Ajustes · Ayuda
   │
Dominio       ─ Planificador · Intensidad · Repaso espaciado · Generador de documentos
   │
Servicios     ─ Voz · IA · Notificaciones · Índice de apuntes · Sincronización
   │
Datos         ─ SwiftData (local) + iCloud (CloudKit privado)
```

## Servicios clave

| Servicio | Tecnología | Offline |
|---|---|---|
| Palabra clave "Jarvis" | Porcupine (keyword "Jarvis" incluida) o detector propio sobre `AVAudioEngine` | Sí |
| Voz a texto | `SpeechAnalyzer` / `SFSpeechRecognizer` con reconocimiento en el dispositivo; Whisper local como respaldo | Sí |
| Texto a voz | `AVSpeechSynthesizer` | Sí |
| IA local | Foundation Models (Apple Intelligence) y/o MLX con un modelo pequeño | Sí |
| IA en la nube (opcional) | API de Claude a través de un pequeño backend propio; **la clave nunca va en la app** | No |
| Alarmas y recordatorios | `UserNotifications` (time-sensitive), AlarmKit en iOS 26 | Sí |
| Búsqueda en apuntes | Embeddings locales + índice vectorial en SwiftData | Sí |
| OCR de cuadernos | Vision (`VNRecognizeTextRequest`) | Sí |
| Importar archivos | `PDFKit`, `UniformTypeIdentifiers` | Sí |
| Atajos / Siri | App Intents (Botón de Acción, Shortcuts, widget) | Sí |
| Sincronización | SwiftData + CloudKit (base privada del usuario) | Diferida |

## Modelo de datos (SwiftData)

`Perfil`, `Tarea`, `Meta`, `Habito`, `Movimiento` (finanzas), `Persona`, `Materia`, `SesionClase`, `Evaluacion`, `TemaVisto`, `Apunte` (archivo + texto + embedding), `TarjetaRepaso`, `SesionEstudio`, `Documento` (+ `VersionDocumento`), `Recordatorio`, `Conversacion`.

## Intensidad dinámica

`carga = Σ (minutos × peso_prioridad × peso_cercania)` de lo pendiente hoy, dividido por las horas disponibles.

| Carga | Modo | Comportamiento de Jarvis |
|---|---|---|
| < 0.5 | Ligero | Propone adelantar trabajo y repaso |
| 0.5–0.9 | Normal | Plan equilibrado |
| > 0.9 | Intenso | Recorta lo no esencial, bloques de enfoque cortos, descansos obligatorios |

## Modo híbrido de IA

1. Siempre intenta primero el modelo **local**.
2. Si la tarea es pesada (documento largo) y hay internet, ofrece usar la nube.
3. Sin internet, degrada con elegancia y lo dice.

## Seguridad y privacidad

- Datos en el dispositivo y en el iCloud privado del usuario.
- Micrófono solo tras la palabra clave; el audio no se guarda.
- Sin claves API en el cliente. Secretos en Keychain.
- Una sola persona: sin cuentas, sin analítica de terceros.

## Estructura de carpetas prevista

```
Jarvis/
  App/            punto de entrada, navegación
  Features/       Hoy, Estudio, Taller, Jarvis, Ajustes, Ayuda
  Domain/         planificador, intensidad, repaso espaciado
  Services/       voz, IA, notificaciones, indexado, sync
  Data/           modelos SwiftData
  Resources/
Tests/
docs/
prototipo-web/    referencia de diseño (React/Vite)
```
