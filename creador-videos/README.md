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

## Qué mide
- **Ritmo:** cortes por 10 s, plano mediano, cortes en los 3 primeros segundos, curva de cortes cada 5 s.
- **Audio:** volumen (LUFS), porcentaje de silencio, palabras por minuto y el gancho dicho (transcripción local con Whisper).
- **Alcance:** vistas, likes, comentarios y vistas por día, tal como las muestra la plataforma al descargar.
- **Fotogramas:** una tira con los 6 primeros segundos (el gancho) y una hoja con 24 fotogramas repartidos, para que Claude vea la edición y no solo los números.

## Límites
- El algoritmo de cada red no es visible. Se infieren patrones de lo público (estructura, ritmo, métricas); la retención real solo la ves en las estadísticas de tus propias cuentas.
- Desde la nube de Claude no se pueden bajar videos: YouTube y TikTok bloquean esas IP. Descarga en tu Mac.
- Los videos ajenos son referencia para estudiar estructura, no material para republicar.
- Verificado en Linux con un video sintético (cortes, silencio, fotogramas, informe) y con la lectura de metadatos de YouTube. `instalar.sh` (Homebrew) y la descarga real en tu Mac aún no se han probado.
