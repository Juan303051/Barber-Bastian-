"""Punto de entrada: ./creador app | celular | director | cuenta | musica | preparar | probar | descargar | analizar | informe | todo | validar | guion | render | estudio"""
from __future__ import annotations

import argparse
import sys

from comun import RAIZ, asegurar_carpetas, empresas, nombre


def main() -> int:
    ap = argparse.ArgumentParser(prog="creador", description=__doc__)
    ap.add_argument("accion", choices=["app", "celular", "director", "cuenta", "musica", "preparar", "probar", "descargar", "analizar", "informe", "todo", "validar", "guion", "render", "estudio"])
    ap.add_argument("guion", nargs="?", help="render/estudio: nombre del guion en empresas/<empresa>/formatos/ o ruta a un .json; guion: nombre del archivo de video")
    ap.add_argument("segundo", nargs="?", help="cuenta: el correo (./creador cuenta restablecer tu@correo.com); musica: dónde guardar el análisis completo (.json); celular: no se usa")
    ap.add_argument("--empresa", help="carpeta de la empresa (por defecto, todas)")
    ap.add_argument("--solo-metadatos", action="store_true", help="descargar: solo vistas, likes y textos, sin el video")
    ap.add_argument("--cookies-navegador", metavar="NAVEGADOR", help="descargar: safari, chrome, firefox… (para videos que piden sesión)")
    ap.add_argument("--extractor-args", help="descargar: avanzado, p. ej. youtube:player_client=tv")
    ap.add_argument("--max", type=int, default=5, help="descargar: tope de videos si pegas el perfil o lista de reproducción")
    ap.add_argument("--umbral", type=float, default=0.3, help="analizar: sensibilidad de corte, 0.1 detecta más, 0.5 menos")
    ap.add_argument("--sin-voz", action="store_true", help="analizar: no transcribir")
    ap.add_argument("--modelo-voz", default="base", help="analizar: tiny, base, small, medium")
    ap.add_argument("--diseno", choices=["pleno", "antes-despues"], default="antes-despues", help="guion: diseño del borrador")
    ap.add_argument("--nombre", help="guion: nombre del guion (por defecto, el del video)")
    ap.add_argument("--sin-navegador", action="store_true", help="app: no abrir el navegador al iniciar")
    ap.add_argument("--rapido", action="store_true", help="probar: omite la prueba de Remotion (la más lenta)")
    ap.add_argument("--forzar", action="store_true", help="analizar: rehacer lo ya analizado; guion: reemplazar un guion que ya existe")
    a = ap.parse_args()
    asegurar_carpetas()

    if a.accion in ("app", "cuenta", "celular", "director"):
        sys.path.insert(0, str(RAIZ / "app"))
        if a.accion == "director":
            from servidor import autoevaluacion
            return autoevaluacion.correr()
        from servidor import arranque
        if a.accion == "celular":
            return arranque.celular(a.guion)
        return arranque.iniciar(not a.sin_navegador) if a.accion == "app" else arranque.cuentas(a.guion, a.segundo)

    if a.accion == "musica":
        if not a.guion:
            ap.error("musica necesita el archivo: ./creador musica cancion.mp3")
        import json
        from pathlib import Path
        import musica
        try:
            analisis = musica.analizar(Path(a.guion).expanduser())
        except ValueError as error:
            print(f"No se pudo analizar: {error}")
            return 1
        print(f"{analisis['archivo']}: {musica.resumen(analisis)}")
        print("Secciones:", ", ".join(f"{s['ini']:.1f}s {s['nivel']}" for s in analisis["secciones"]))
        if analisis["caidas"]:
            print("Caídas hacia sección fuerte en:", ", ".join(f"{c:.1f}s" for c in analisis["caidas"]))
        if a.segundo:
            Path(a.segundo).expanduser().write_text(json.dumps(analisis, ensure_ascii=False), encoding="utf-8")
            print(f"Análisis completo guardado en {a.segundo}")
        return 0

    if a.accion == "preparar":
        print("Carpetas listas: en cada empresa ya puedes soltar videos en videos/referencias/ y videos/propios/.")
        return 0

    if a.accion == "probar":
        from diagnostico import probar
        return probar(a.rapido)

    if a.accion == "guion":
        if not a.empresa or not a.guion:
            ap.error("guion necesita --empresa y el video: ./creador guion <video.mp4> --empresa <empresa>")
        from guion import crear
        destino = crear(empresas(a.empresa)[0], a.guion, a.diseno, a.nombre, a.forzar)
        print(f"Guion creado: {destino.relative_to(destino.parents[2])}\nRevísalo (palabras clave, capas) y genera el video con:  ./creador render {destino.stem} --empresa {a.empresa}")
        return 0

    if a.accion in ("render", "estudio"):
        if not a.empresa or not a.guion:
            ap.error(f"{a.accion} necesita --empresa y el guion: ./creador {a.accion} <guion> --empresa <empresa>")
        from render import estudio, render
        carpeta = empresas(a.empresa)[0]
        return render(carpeta, a.guion).returncode if a.accion == "render" else estudio(carpeta, a.guion)

    if a.accion == "validar":
        from boveda import validar
        return 1 if validar() else 0

    for carpeta in empresas(a.empresa):
        print(f"\n== {nombre(carpeta)} ==")
        if a.accion in ("descargar", "todo"):
            from descargar import descargar
            descargar(carpeta, a.solo_metadatos, a.cookies_navegador, a.extractor_args, a.max)
        if a.accion in ("analizar", "todo") and not a.solo_metadatos:
            from analizar import analizar
            n = analizar(carpeta, a.umbral, not a.sin_voz, a.modelo_voz, a.forzar)
            print(f"  {n} videos analizados")
        if a.accion in ("informe", "todo"):
            from notas import generar
            print(f"  {generar(carpeta)} notas escritas en la bóveda")
    if a.accion in ("informe", "todo") and not a.solo_metadatos:
        from boveda import validar
        print("\n== Revisión de la bóveda ==")
        return 1 if validar() else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
