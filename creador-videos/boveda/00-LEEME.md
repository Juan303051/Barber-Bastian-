---
tipo: "leeme"
---
# Bóveda de Creador de videos

Memoria del proyecto: lo que se aprende de cada video y de cada investigación, separado por empresa. Se abre con Obsidian (carpeta `boveda/`) y la lee y escribe Claude desde el repositorio.

## Carpetas
| Carpeta | Qué guarda |
|---|---|
| `01-conocimiento/` | Lo que sirve a todas las empresas: `investigacion/` (con fuentes) y `tecnicas/` (ganchos, ritmo, subtítulos, audio…) |
| `02-empresas/<empresa>/` | Todo lo de una sola empresa. Nada se mezcla entre empresas |
| `03-plantillas/` | Plantillas de Obsidian para cada tipo de nota |
| `99-bandeja/` | Notas sueltas por clasificar |

`02-empresas/maquetas-estilo/` no es una empresa: es la biblioteca de videos modelo que sirve a todas. Dentro de `02-empresas/<empresa>/`:

| Carpeta o archivo | Qué guarda | Quién lo escribe |
|---|---|---|
| `00-ficha.md` | Qué vende, público, tono, redes, lo que nunca se hace | Tú |
| `referencias/` | Una nota por video de referencia: métricas, ritmo, desglose por plano, transcripción | `./creador informe` (no se edita a mano) |
| `propios/` | Lo mismo, para tus videos ya publicados | `./creador informe` |
| `analisis/` | Una nota por video con la lectura detallada: por qué funciona y cómo replicarlo | Claude y tú |
| `investigacion/` | Investigaciones específicas de la empresa (público, competencia, tendencias) | Claude y tú |
| `formatos/` | Una nota por formato replicable; apunta a su guion en `empresas/<empresa>/formatos/*.json` | Claude y tú |
| `ideas/` | Ideas de videos y escenas | Claude y tú |
| `medios/` | Fotogramas generados por cada video. **No se suben a git** (pueden ser de otros creadores y el repositorio es público): se regeneran con los videos | `./creador analizar` |
| `informe.md` | Ranking, comparación referencias vs. propios y análisis pendientes | `./creador informe` |

## Reglas para que nada se rompa
1. **Cada nota empieza con propiedades** (frontmatter) con `tipo` y, dentro de `02-empresas/`, `empresa` igual al nombre de su carpeta. Es lo que evita mezclar empresas.
2. **Lo generado y lo escrito a mano no se pisan.** El software solo reescribe notas con `generado: true` y se niega a tocar cualquier otra, aunque el nombre coincida. Tu lectura va siempre en `analisis/`.
3. **Nombres sin espacios ni acentos** (`youtube-abc123`, `consejo-rapido`). Los enlaces entre notas llevan la ruta completa: `[[02-empresas/al-volante/analisis/youtube-abc123]]`.
4. **Ni videos ni archivos de más de 5 MB.** Los videos se quedan en tu Mac (`empresas/<empresa>/videos/`), nunca aquí.
5. **Investigación con fuente.** Cada hallazgo lleva enlace y fecha de consulta, y un nivel de confianza (`alta`, `media`, `baja`). Sin fuente, la nota queda en `estado: "borrador"`.
6. **Antes de trabajar en una empresa**, Claude lee su `00-ficha.md`, su `informe.md` y las últimas notas de `analisis/`. **Después**, escribe lo aprendido en la carpeta que corresponda.
7. Revisión mecánica: `./creador validar` detecta enlaces rotos, empresas mezcladas, videos dentro de la bóveda y notas sin propiedades.

## Cómo viaja la bóveda entre tu Mac y Claude
Es una carpeta de archivos Markdown dentro del repositorio. Claude escribe en la nube y tú recibes los cambios con `git pull`; lo que escribas en Obsidian llega a Claude con `git add -A && git commit && git push`. El plugin comunitario *Obsidian Git* puede hacerlo solo cada pocos minutos. Para usar otra carpeta como bóveda, define `CREADOR_BOVEDA=/ruta/a/tu/boveda`; Claude solo la ve si esa carpeta está en el repositorio.
