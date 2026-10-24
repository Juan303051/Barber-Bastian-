---
tipo: "investigacion"
fecha: "2026-10-24"
estado: "revisado"
fuentes: ["https://www.w3.org/WAI/WCAG22/Understanding/dragging-movements.html", "https://uploadcare.com/blog/file-uploader-ux-best-practices/", "https://carbondesignsystem.com/components/file-uploader/usage", "https://blog.filestack.com/file-upload-ui-patterns-improve-completion-rates/"]
---
# Subir varias escenas, ordenarlas y que sea fácil: qué dicen las guías

Pregunta: cómo debe comportarse la carga de varias tomas (la gente graba por escenas) para que un creador no se pierda. Aplicación: tarjeta de video de `creador-videos/app/web/trabajo.js`. Complementa [[01-conocimiento/investigacion/diseno-apple-hig]] (arrastrar y soltar, revelación progresiva).

## Hallazgos
Consultado el 2026-10-24. La búsqueda de la guía de Nielsen Norman Group no devolvió su página: lo de carga de archivos viene de guías de producto y de un sistema de diseño, por eso su confianza es **media**.

| Tema | Lo que dicen | Fuente | Confianza |
|---|---|---|---|
| Mover sin arrastrar | WCAG 2.2, criterio 2.5.7 (nivel AA): lo que se hace arrastrando debe poder hacerse con **un solo puntero sin arrastrar**. Alternativas típicas para reordenar listas: seleccionar el elemento y moverlo con botones de subir y bajar, o un menú emergente con las opciones de mover | [WCAG 2.2 · Dragging Movements](https://www.w3.org/WAI/WCAG22/Understanding/dragging-movements.html) | alta |
| Soltar y elegir | Combinar arrastrar y soltar con «hacer clic para elegir»: el arrastre no existe en el teclado ni en pantallas táctiles | [Uploadcare](https://uploadcare.com/blog/file-uploader-ux-best-practices/), [Filestack](https://blog.filestack.com/file-upload-ui-patterns-improve-completion-rates/) | media |
| Reglas a la vista | Decir dentro de la zona qué tipos de archivo, qué tamaño y cuántos se admiten, no en una ayuda lejana | Uploadcare | media |
| Varios archivos | Aceptar varios a la vez por defecto cuando el caso lo pide; cambiar el borde de la zona al arrastrar encima | [Carbon Design System](https://carbondesignsystem.com/components/file-uploader/usage) | media |
| Errores | Validar al elegir y **nombrar el archivo que falló y por qué**, no un error general | Uploadcare | media |
| Móvil | La zona se convierte en un objetivo táctil grande | Uploadcare | media |

## Lo que se aplicó en Iris
- Una zona que acepta **varios videos a la vez** (arrastrados o elegidos), ordenados por nombre natural (`toma2` antes que `toma10`), con barra de avance por archivo y el error con el nombre del archivo.
- Orden con botones **Subir** y **Bajar** por escena (cumple 2.5.7 sin arrastrar), anunciado a lectores de pantalla («Escena movida a la posición 2»); la primera no sube y la última no baja.
- Cada escena muestra miniatura, nombre y duración; el total («3 escenas · 21 s») sale debajo.
- Las reglas (MP4, MOV, WEBM · puedes elegir varias) están dentro de la zona.

## Qué falta
Arrastrar para reordenar con el ratón (los botones ya lo permiten todo). Probar el flujo con tomas reales del iPhone (MOV con rotación): el lector de escenas ya aplica la rotación y lo cubre una prueba con un video sintético girado, pero no se probó con un archivo del teléfono.
