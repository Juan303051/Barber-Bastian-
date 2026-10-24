---
tipo: "investigacion"
fecha: "2026-10-24"
estado: "revisado"
fuentes: ["https://developer.apple.com/design/human-interface-guidelines/color", "https://developer.apple.com/design/human-interface-guidelines/typography", "https://developer.apple.com/design/human-interface-guidelines/materials", "https://developer.apple.com/design/human-interface-guidelines/motion", "https://developer.apple.com/design/human-interface-guidelines/managing-accounts", "https://developer.apple.com/design/human-interface-guidelines/progress-indicators", "https://developer.apple.com/design/human-interface-guidelines/text-fields", "https://developer.apple.com/design/human-interface-guidelines/buttons", "https://developer.apple.com/design/human-interface-guidelines/layout", "https://developer.apple.com/design/human-interface-guidelines/accessibility", "https://developer.apple.com/design/human-interface-guidelines/drag-and-drop"]
---
# Diseño de Apple (Human Interface Guidelines) para la app de videos

Pregunta: qué dice la guía oficial de Apple y cómo se aplica a una app web local de una pantalla, con paleta arcoíris, inicio de sesión y progreso de creación en vivo. Aplicación: `creador-videos/app/`.

## Hallazgos
Todas las filas vienen de las páginas oficiales de la guía (leídas el 2026-10-24 a través de los datos que Apple publica para cada página). Confianza **alta** salvo donde se indica.

| Tema | Lo que dice Apple | Fuente |
|---|---|---|
| Color | Usar colores del sistema y semánticos; no escribir sus valores a mano. Dar variante clara, oscura y de contraste alto. «Evitar depender solo del color»: acompañarlo de texto o forma | [Color](https://developer.apple.com/design/human-interface-guidelines/color) |
| Color sobre vidrio | El Liquid Glass «no tiene color propio y toma el del contenido de detrás». Aplicar color «con moderación»: reservar el tinte para estados o acción principal y **no añadir color al fondo de varios controles** | Color |
| Colores del sistema (claro, oscuro) | Rojo 255,56,60 · 255,66,69; naranja 255,141,40 · 255,146,48; amarillo 255,204,0 · 255,214,0; verde 52,199,89 · 48,209,88; menta 0,200,179 · 0,218,195; turquesa 0,195,208 · 0,210,224; cian 0,192,232 · 60,211,254; azul 0,136,255 · 0,145,255; índigo 97,85,245 · 109,124,255; morado 203,48,224 · 219,52,242; rosa 255,45,85 · 255,55,95. Apple avisa de que pueden cambiar entre versiones | Color |
| Tipografía | Fuente San Francisco (SF Pro). Tamaño por defecto 17 pt y mínimo 11 pt en iOS; 13 y 10 en macOS. Usar pesos Regular, Medium, Semibold o Bold; evitar Ultralight, Thin y Light. Jerarquía con peso, tamaño y color; pocas tipografías. Estilos iOS: Título grande 34, Título 1 28, Título 2 22, Título 3 20, Headline 17 seminegrita, Cuerpo 17, Callout 16, Subtítulo 15, Nota 13, Pie 12 y 11 | [Typography](https://developer.apple.com/design/human-interface-guidelines/typography) |
| Materiales | Dos tipos: Liquid Glass (capa funcional de controles y navegación que flota sobre el contenido) y materiales estándar (fondos y contenido). **No usar Liquid Glass en la capa de contenido** ni en muchos controles a la vez. Variante «clara» solo sobre medios y con una capa oscura al 35 % si el fondo es brillante. Materiales más gruesos dan más contraste al texto fino; evitar el nivel cuaternario en materiales finos | [Materials](https://developer.apple.com/design/human-interface-guidelines/materials) |
| Movimiento | Con propósito, no decorativo; breve y ligado a una acción; **no animar interacciones frecuentes**; permitir cancelar y no obligar a esperar; no usar el movimiento como única señal | [Motion](https://developer.apple.com/design/human-interface-guidelines/motion) |
| Reducir movimiento | Con el ajuste activo, reducir animaciones automáticas y repetitivas (zoom, escala), reducir el rebote, cambiar transiciones por fundidos y evitar entrar o salir de desenfoques | [Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility) |
| Contraste | Texto hasta 17 pt: **4.5:1**; 18 pt: 3:1; negrita de cualquier tamaño: 3:1. Revisar en claro y oscuro | Accessibility |
| Tamaño de controles | iOS: 44×44 pt por defecto y 28×28 mínimo; macOS: 28×28 y 20×20. Separación de unos 12 pt alrededor de controles con borde | Accessibility |
| Texto ampliable | Permitir ampliar el texto al menos un 200 % | Accessibility |
| Cuentas | Pedir cuenta «solo si la función principal lo requiere» y **retrasar el inicio de sesión** cuanto se pueda; **explicar los beneficios** de crear la cuenta; preferir llaves de acceso (passkeys) o «Iniciar con Apple»; si hay contraseñas, añadir verificación en dos pasos; **nombrar el método de autenticación** («Entrar con contraseña», no «Entrar»); quien puede crear una cuenta debe poder **eliminarla** desde la app | [Managing accounts](https://developer.apple.com/design/human-interface-guidelines/managing-accounts) |
| Progreso | Usar indicadores **determinados** siempre que se pueda; avanzar a ritmo parejo (no 90 % en 5 s y el resto en 5 min); mantenerlos en movimiento y explicar si algo se detiene; pasar de indeterminado a determinado en cuanto se pueda; descripción corta y precisa (evitar «Cargando»); **ubicación constante**; incluir **Cancelar** cuando no haya efectos negativos y **avisar antes de cancelar** si se pierde avance; no cambiar de círculo a barra | [Progress indicators](https://developer.apple.com/design/human-interface-guidelines/progress-indicators) |
| Campos de texto | Etiqueta permanente además del texto de ejemplo; campo seguro para contraseñas; validar el correo al salir del campo y el usuario o contraseña antes de salir; botón de borrar; espaciar parejo y apilar con anchos consistentes | [Text fields](https://developer.apple.com/design/human-interface-guidelines/text-fields) |
| Botones | Estilo prominente solo para la acción más probable, **uno o dos por vista**; destacar por estilo, no por tamaño; etiquetas que empiezan con verbo; zona táctil mínima de 44×44; rol destructivo en rojo y nunca como principal; indicador de actividad con etiqueta alterna («Creando…») mientras tarda; estado de pulsado en los personalizados | [Buttons](https://developer.apple.com/design/human-interface-guidelines/buttons) |
| Diseño | Importancia arriba y al inicio; alinear; agrupar con espacio negativo o contenedores; **revelación progresiva** (menús, opciones plegables); controles de vidrio separados del contenido; adaptarse al tamaño sin que la función dependa de él; **en macOS evitar controles o información crítica en la parte inferior de la ventana** | [Layout](https://developer.apple.com/design/human-interface-guidelines/layout) |
| Arrastrar y soltar | Mostrar la imagen arrastrada; resaltar el destino **solo si el contenido es válido** y quitar el resaltado al salir; si es inválido, sin pista o con señal de «no permitido»; **marcador de posición y progreso** mientras se transfiere; fallo con retroalimentación visual; permitir deshacer; **no depender solo de arrastrar** (ofrecer un botón o menú) | [Drag and drop](https://developer.apple.com/design/human-interface-guidelines/drag-and-drop) |

## Cómo se aplica en la app
| Decisión | Por qué (guía) |
|---|---|
| El arcoíris vive en el **fondo** (resplandor detrás del vidrio), en la **barra de progreso**, en la marca y en un borde fino de la acción principal; los controles son de vidrio neutro con un solo tinte | Color con moderación sobre vidrio; no colorear varios controles |
| Cada etapa de la creación lleva color, **icono y texto** | No depender solo del color |
| La acción «Crear» va **arriba a la derecha**, fija, y es el único botón prominente de la vista | Uno o dos prominentes; no poner lo crítico abajo en macOS |
| Barra de progreso **determinada** con etapa en texto concreto («Transcribiendo la voz», no «Cargando»), tiempo restante, mismo lugar siempre, botón **Cancelar** con confirmación | Progreso |
| Inicio de sesión: la pantalla de bienvenida explica el beneficio; el método se nombra («Entrar con contraseña»); correo se valida al salir del campo; etiqueta fija + ejemplo; campo seguro con botón de mostrar; **eliminar cuenta** dentro del menú de usuario | Cuentas y campos de texto |
| Opciones avanzadas plegadas por defecto | Revelación progresiva |
| Zona de soltar videos resalta solo con archivos de video, rechaza otros con mensaje y trae botón «Elegir archivo» | Arrastrar y soltar |
| Animaciones breves y con propósito; con «reducir movimiento» se cambian por fundidos y se apagan las repetitivas | Movimiento y accesibilidad |
| Texto en `rem`, base 17 px, estilos de la tabla; sin pesos finos; contraste mínimo 4.5:1 | Tipografía y accesibilidad |

## Decisiones propias (no vienen de la guía)
- **Esquinas concéntricas** y radios grandes (20–28 px): criterio de diseño inspirado en el estilo actual de Apple, no una regla citada.
- **El vidrio es una aproximación** hecha con `backdrop-filter`; no es el material Liquid Glass de Apple y no se comporta igual.
- **Fuente:** pila `-apple-system, BlinkMacSystemFont, "SF Pro Text"…`: en un Mac se ve San Francisco; en otros sistemas, la fuente del sistema. No se incluye ni se descarga la fuente de Apple (la guía dice que no se incrusten).
- **Llaves de acceso y verificación en dos pasos** quedan fuera por ahora: la app es local y las cuentas solo protegen el equipo; se anota como mejora.
- Los valores de color pueden cambiar entre versiones del sistema (lo avisa Apple): se usan como referencia.

## Qué falta por verificar
Cómo se ve la app con el texto ampliado al 200 % en un Mac real, y con «Aumentar contraste» activo.
