# Creador de videos

Herramientas para guardar videos de referencia por empresa, medir cómo están hechos y compararlos con los tuyos. Corren en tu Mac: los videos se quedan allí, y al repo solo suben las métricas, los informes y las hojas de fotogramas, que es lo que Claude lee para analizar y proponer.

## Empresas
`empresas/` tiene una carpeta por empresa: Mundial de Motos, Masa Motos, Cositas Chulas Kids, Al volante, Tu Licencia y Pádel Luxury Store. Cada una trae:

| Archivo | Para qué |
|---|---|
| `README.md` | Ficha de marca: público, tono, redes, lo que nunca se hace |
| `referencias.txt` | Enlaces de videos que quieres tomar como modelo, con un comentario de por qué |
| `propios.txt` | Enlaces de tus videos ya publicados de esa empresa |
| `videos/referencias/`, `videos/propios/` | Los archivos descargados. También puedes soltar ahí un .mp4 a mano |
| `analisis/` | Métricas (`.meta.json`, `.analisis.json`) y hojas de fotogramas (`.jpg`) |
| `informe.md` | Resumen generado: ranking, comparación referencias vs. tuyos |
| `formatos/` | Guiones JSON de los videos que se van a hacer (los lee Remotion) |
| `marca.json` | Opcional: colores, fuente, logo y usuario de la marca para Remotion |
| `salidas/` | Videos generados por Remotion (no se suben al repo) |

## Uso
```bash
./instalar.sh                          # una sola vez
./creador todo                         # descarga, analiza e informa de todas las empresas
./creador todo --empresa al-volante    # solo una
./creador descargar --cookies-navegador safari   # si una red pide sesión
./creador analizar --sin-voz           # sin transcripción (más rápido)
./creador analizar --forzar            # rehacer lo ya analizado
```
Después sube los resultados para que Claude los lea: `git add -A && git commit -m "Nuevas referencias" && git push`.

## Hacer videos con Remotion
[Remotion](https://www.remotion.dev) convierte un guion JSON en un video vertical 1080×1920 con la identidad de la empresa. Los formatos que salgan del análisis se guardan como guiones en `empresas/<empresa>/formatos/`.
```bash
./creador render ejemplo --empresa al-volante                  # guion en empresas/al-volante/formatos/ejemplo.json
./creador render remotion/ejemplo.json --empresa al-volante    # o una ruta; este ejemplo no necesita clips
./creador estudio ejemplo --empresa al-volante                 # previsualizar y ajustar en el navegador
```
El video queda en `empresas/<empresa>/salidas/<formato>.mp4`. Un guion se ve así (ver `remotion/ejemplo.json`):

| Campo | Qué es |
|---|---|
| `formato` | Nombre del video de salida |
| `escenas[]` | `tipo`: `gancho` (texto enorme), `contenido` (toma con texto abajo) o `cta` (cierre con logo y usuario) · `duracion` en segundos · `texto` · `clip` y `desde` (ruta relativa a `empresas/`, p. ej. `al-volante/videos/propios/toma1.mp4`) · `silenciar` |
| `subtitulos[]` | `ini`, `fin` (segundos) y `texto` |
| `voz`, `musica` | Audio de locución y música (`archivo`, `volumen`), rutas relativas a `empresas/` |
| `ancho`, `alto`, `fps` | Opcionales; por defecto 1080×1920 a 30 fps |

`marca.json` (opcional, por empresa): `{ "colores": { "fondo": "#0B0B0F", "texto": "#FFFFFF", "acento": "#FFC400" }, "fuente": "Impact", "logo": "al-volante/logo.png", "usuario": "@alvolante" }`. Lo que no pongas toma valores neutros.

## Qué mide
- **Ritmo:** cortes por 10 s, plano mediano, cortes en los 3 primeros segundos, curva de cortes cada 5 s.
- **Audio:** volumen (LUFS), porcentaje de silencio, palabras por minuto y el gancho dicho (transcripción local con Whisper).
- **Alcance:** vistas, likes, comentarios y vistas por día, tal como las muestra la plataforma al descargar.
- **Fotogramas:** una tira con los 6 primeros segundos (el gancho) y una hoja con 24 fotogramas repartidos, para que Claude vea la edición y no solo los números.

## Límites
- El algoritmo de cada red no es visible. Se infieren patrones de lo público (estructura, ritmo, métricas); la retención real solo la ves en las estadísticas de tus propias cuentas.
- Desde la nube de Claude no se pueden bajar videos: YouTube y TikTok bloquean esas IP. Descarga en tu Mac.
- Remotion es gratis para personas y empresas con hasta 3 empleados; una empresa mayor necesita licencia (remotion.pro).
- Los videos ajenos son referencia para estudiar estructura, no material para republicar.
- Verificado en Linux: análisis con un video sintético, lectura de metadatos de YouTube y render con Remotion (escenas, clips, subtítulos, logo, audio). Sin probar: `instalar.sh` (Homebrew), la descarga real en tu Mac, `estudio` en un Mac y la transcripción con voz real.
