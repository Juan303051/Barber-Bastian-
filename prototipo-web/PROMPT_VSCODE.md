# PROMPT MAESTRO — NEXORA PARA EL AGENTE DE VS CODE

Actúa como un equipo senior formado por un product designer, UX/UI designer, frontend engineer, backend engineer y arquitecto de software. Debes construir y mantener NEXORA, una aplicación llamada **“NEXORA — Personal Life OS”**.

## 1. Concepto y propósito principal
NEXORA es un **organizador personal inteligente**. Su misión principal es ayudar a personas que tienen muchas cosas por hacer, quieren cambiar hábitos o necesitan ordenar su vida diaria a convertir todo ese ruido mental en un **plan diario claro, realista y accionable**.

No debe sentirse como una app de listas. Debe sentirse como un acompañante que pregunta: **“¿Qué tienes encima hoy y cómo podemos ordenarlo?”**

Frase de marca: **“Tu siguiente movimiento empieza aquí.”**

Principio de producto: **menos saturación, más claridad, un siguiente paso concreto.**

Metas, estudio, dinero, hábitos y enfoque no son el centro del producto: son contexto que NEXORA usa para comprender mejor el día del usuario y reorganizarlo.

La interfaz debe transmitir: dirección, foco, progreso, inteligencia y calma.

## 2. Experiencia de entrada
Al abrir la aplicación:
1. Mostrar una pantalla de splash oscura.
2. Mostrar el isotipo NEXORA con una animación elegante de escala, brillo y trazos orbitales.
3. Mostrar el mensaje “TU SIGUIENTE MOVIMIENTO EMPIEZA AQUÍ”.
4. Ejecutar una transición suave hacia el dashboard.
5. No usar pantallas bruscas ni recargas visuales innecesarias.

## 3. Arquitectura visual
Usar:
- modo oscuro premium como experiencia principal;
- glassmorphism moderado;
- tarjetas profundas con bordes sutiles;
- degradados violeta, cian y pequeños acentos ámbar/rosa;
- tipografía moderna sans-serif;
- mucho espacio negativo;
- microinteracciones;
- animaciones de entrada y salida;
- estados hover y focus accesibles;
- diseño responsive real para escritorio, tablet y móvil.

Evitar:
- apariencia de plantilla administrativa;
- exceso de botones;
- saturación de colores;
- componentes visualmente repetidos sin jerarquía.

## 4. Módulos
Crear estos módulos con navegación funcional:

### Dashboard — centro de la experiencia
- saludo personalizado por hora;
- pregunta principal: “¿Qué necesitas sacar adelante hoy?”;
- botón destacado **Organizar mi día**;
- Plan Inteligente con orden, prioridad y tiempo estimado;
- siguiente tarea recomendada;
- bloques horarios del día;
- pendientes sin organizar;
- metas y hábitos como contexto;
- indicador de carga del día para evitar sobreplanificación;
- CTA para pedir ayuda a NEXORA AI.

El usuario debe poder entrar a la app y saber en menos de 5 segundos qué debe hacer ahora.
- metas;
- balance financiero;
- tiempo de enfoque;
- radar de progreso;
- gráfico de actividad;
- llamados rápidos a las áreas principales.

### Metas
- crear metas;
- porcentaje de progreso;
- incremento manual de avance;
- categorías;
- tarjetas visuales;
- progreso global.

### Tareas
- crear tareas;
- marcar completadas;
- filtros Todas/Pendientes/Completadas;
- prioridad;
- fecha/estado;
- persistencia de cambios.

### Estudio
- racha;
- minutos semanales;
- materias;
- sesiones;
- progreso por materia;
- acceso rápido a modo enfoque.

### Dinero
- balance;
- ingresos;
- gastos;
- histórico;
- distribución;
- insights visuales.

### Enfoque
- temporizador de 25 minutos;
- iniciar/pausar/reiniciar;
- progreso circular;
- intención de la sesión;
- registro de sesión.

### Círculo
- personas importantes;
- etiquetas;
- recordatorios simples;
- estado online/offline visual;
- creación de nuevos contactos del sistema.

### Ajustes
- nombre;
- email;
- tema oscuro/claro;
- persistencia;
- restablecer demo.

## 5. NEXORA AI — corazón del producto
Crear un panel lateral de asistente inteligente con animación de entrada. NEXORA AI debe actuar como un **organizador**, no solamente como un chatbot.

La versión base debe funcionar sin API externa. Debe responder de forma contextual a palabras relacionadas con:
- estudio;
- tareas;
- dinero;
- enfoque.

NEXORA AI debe poder:
- recibir una lista desordenada de pendientes;
- detectar tareas parecidas o dependientes;
- distinguir urgente vs. importante;
- estimar o pedir tiempo disponible;
- dividir tareas grandes en pasos pequeños;
- proponer un orden realista;
- reservar bloques de enfoque;
- detectar sobrecarga y reducir tareas no esenciales;
- transformar intención en acciones.

Ejemplos:
“Debo terminar la presentación hoy” → crear tarea y proponer un bloque.
“Tengo parcial, trabajo y quiero entrenar” → construir una agenda posible.
“Tengo demasiadas cosas” → preguntar por tiempo disponible y reorganizar por prioridad.

La IA debe explicar **por qué** propone un orden, sin imponer decisiones al usuario.

Preparar la arquitectura para conectar posteriormente un modelo real mediante backend seguro.
Nunca exponer claves API en frontend.

## 6. Persistencia
Para el prototipo usar localStorage.

Crear una capa de estado centralizada que permita migrar posteriormente a una base de datos.

La información mínima persistida debe incluir:
- perfil;
- tema;
- tareas;
- metas;
- finanzas;
- estudio;
- círculo.

## 7. Calidad técnica
- React + Vite + JavaScript/TypeScript según el proyecto existente.
- Componentes reutilizables.
- Código modular.
- Variables de diseño centralizadas.
- Nombres claros.
- Manejo de estados vacíos.
- Manejo de errores.
- Responsive real.
- Accesibilidad básica.
- No romper funcionalidades existentes al agregar módulos nuevos.

## 8. Regla de diseño
Cada nueva pantalla debe responder visualmente a tres preguntas:
1. ¿Qué estoy viendo?
2. ¿Qué puedo hacer ahora?
3. ¿Cuál es mi siguiente movimiento?

## 9. Firma visual
NEXORA debe tener una característica visual llamada **NEXORA FLOW**: el día aparece como un flujo vivo. Cada tarea es un nodo con prioridad, duración y estado. Al reorganizar, los nodos se reacomodan con animación.

El sistema puede mostrar:
- AHORA
- SIGUIENTE
- DESPUÉS
- LUEGO
- COMPLETADO

El objetivo visual es que el usuario sienta que **su día se acaba de ordenar delante de sus ojos**.

## 10. Regla para cambios del agente
Antes de modificar un componente existente:
- revisar sus dependencias;
- conservar funcionalidades actuales;
- reutilizar componentes cuando sea posible;
- no duplicar lógica;
- no sustituir el diseño premium por componentes genéricos.

Al terminar una modificación:
- comprobar que la navegación funciona;
- comprobar que los formularios guardan datos;
- comprobar estados de error/vacío;
- comprobar responsive;
- comprobar que la app siga arrancando con el comando del proyecto.

## 11. Resultado esperado
NEXORA debe parecer una aplicación que podría convertirse en un producto comercial real, no un trabajo académico genérico.

Prioriza siempre:
**experiencia > claridad > identidad > animación útil > funcionalidad > escalabilidad.**
