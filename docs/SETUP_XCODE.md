# Preparar el entorno (Mac + iPhone 17)

## Requisitos
- Mac con la última versión de macOS y **Xcode** instalado (App Store).
- Cuenta Apple (el Apple ID gratuito sirve para instalar en tu propio iPhone; vence cada 7 días. La cuenta de desarrollador de pago evita eso).
- iPhone 17 con modo desarrollador activado: Ajustes → Privacidad y seguridad → Modo de desarrollador.
- Mismo Apple ID en Mac e iPhone, con **iCloud** activado, para sincronizar.

## Pasos
1. Clona el repositorio y ábrelo: `git clone <url>` → abre `Jarvis.xcodeproj` (cuando exista, Fase 1).
2. En Xcode, selecciona el target **Jarvis** → *Signing & Capabilities* → elige tu equipo.
3. Capabilities necesarias: iCloud (CloudKit), Background Modes (audio), Push/Time-sensitive notifications, Siri.
4. Conecta el iPhone por cable, selecciónalo como destino y pulsa **Run**.
5. Para el Mac, elige *My Mac* como destino y pulsa **Run**.
6. Acepta los permisos de micrófono, reconocimiento de voz, notificaciones y calendario.

## Que Jarvis arranque con el Mac
Ajustes del Mac → General → Ítems de inicio → añade Jarvis. La app incluye también la opción "Abrir al iniciar sesión".

## Prototipo web (referencia)
```bash
cd prototipo-web
npm install
npm run dev
```
