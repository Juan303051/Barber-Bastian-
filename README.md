# NEXORA — Personal Life OS

NEXORA es un organizador personal inteligente: ayuda a convertir todo lo que una persona tiene pendiente en un plan diario claro, realista y accionable. Las metas, estudio, dinero, hábitos y enfoque sirven como contexto para que NEXORA AI pueda reorganizar el día.

## Ejecutar en VS Code

Requisitos:
- Node.js 20+ recomendado
- VS Code

Pasos:

```bash
npm install
npm run dev
```

Luego abre la dirección que muestre Vite, normalmente `http://localhost:5173`.

Para probar el build de producción:

```bash
npm run build
npm run preview
```

## Qué incluye

- Splash de entrada animado con identidad NEXORA.
- Dashboard centrado en el flujo diario y el “Plan Inteligente”.
- Botón “Organizar mi día” para reordenar pendientes por prioridad y tiempo estimado.
- Dashboard responsive con microinteracciones.
- Metas con progreso.
- Tareas con filtros y persistencia.
- Módulo de estudio.
- Finanzas con métricas y gráfico SVG.
- Temporizador Focus de 25 minutos.
- Círculo personal.
- Asistente NEXORA AI local/demo orientado a reorganizar pendientes y convertir intención en acciones.
- Ajustes de perfil y tema oscuro/claro.
- Persistencia completa con `localStorage`.
- Diseño responsive para escritorio y móvil.

## Nota sobre IA real

El asistente incluido es una versión local/demo para que el proyecto funcione sin claves externas. Para conectarlo a un modelo real, crea un backend seguro (por ejemplo Node/Express o una API route) y guarda la clave del proveedor únicamente en el servidor.
