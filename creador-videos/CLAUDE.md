# Creador de videos — reglas para Claude

Sistema para seis empresas (Mundial de Motos, Masa Motos, Cositas Chulas Kids, Al volante, Tu Licencia, Pádel Luxury Store). No tiene relación con la app JARVIS·NEXORA del resto del repositorio.

- **Memoria = la bóveda `boveda/`.** Antes de trabajar en una empresa lee `boveda/00-LEEME.md` y, de esa empresa, `00-ficha.md`, `informe.md` y las últimas notas de `analisis/` e `ideas/`. Después escribe lo aprendido en la carpeta que corresponda. Las reglas de escritura están en `00-LEEME.md` y no se repiten aquí.
- **Una empresa por carpeta.** Nunca mezclar información de empresas; lo común va en `boveda/01-conocimiento/`. `maquetas-estilo` no es una empresa: es la biblioteca de videos modelo.
- **Investigar con fuente.** Toda afirmación de una investigación lleva enlace, fecha de consulta y confianza; las cifras de blogs sin fuente primaria no son reglas. Preferir fuentes oficiales.
- **Después de escribir en la bóveda, ejecutar `./creador validar`** y dejarlo en 0 errores antes de hacer commit.
- **No tocar notas con `generado: true` a mano:** se reescriben con `./creador informe`. La lectura va en `analisis/`.
- **Lo que no se puede hacer desde la nube:** descargar videos de YouTube, TikTok o Instagram (bloquean la IP) ni acceder al computador del usuario. Los videos se analizan en el Mac del usuario o llegan por el chat; los archivos de video nunca se suben al repositorio.
- **Videos de otros creadores:** solo para estudiar estructura y técnica. No republicar, no quitar marcas de agua.
- **Estado de verificación:** decir siempre qué se probó en Linux y qué falta por probar en el Mac del usuario.
