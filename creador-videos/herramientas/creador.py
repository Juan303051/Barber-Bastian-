"""Punto de entrada: ./creador descargar | analizar | informe | todo"""
from __future__ import annotations

import argparse
import sys

from comun import empresas, nombre


def main() -> int:
    ap = argparse.ArgumentParser(prog="creador", description=__doc__)
    ap.add_argument("accion", choices=["descargar", "analizar", "informe", "todo"])
    ap.add_argument("--empresa", help="carpeta de la empresa (por defecto, todas)")
    ap.add_argument("--solo-metadatos", action="store_true", help="descargar: solo vistas, likes y textos, sin el video")
    ap.add_argument("--cookies-navegador", metavar="NAVEGADOR", help="descargar: safari, chrome, firefox… (para videos que piden sesión)")
    ap.add_argument("--extractor-args", help="descargar: avanzado, p. ej. youtube:player_client=tv")
    ap.add_argument("--max", type=int, default=5, help="descargar: tope de videos si pegas el perfil o lista de reproducción")
    ap.add_argument("--umbral", type=float, default=0.3, help="analizar: sensibilidad de corte, 0.1 detecta más, 0.5 menos")
    ap.add_argument("--sin-voz", action="store_true", help="analizar: no transcribir")
    ap.add_argument("--modelo-voz", default="base", help="analizar: tiny, base, small, medium")
    ap.add_argument("--forzar", action="store_true", help="analizar: rehacer lo ya analizado")
    a = ap.parse_args()

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
            from informe import informe
            salida = informe(carpeta)
            print(f"  informe: {salida.relative_to(carpeta.parent.parent)}" if salida else "  sin análisis todavía")
    return 0


if __name__ == "__main__":
    sys.exit(main())
