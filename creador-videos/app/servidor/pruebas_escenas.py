"""Pruebas de las escenas (unir tomas de distinto tamaño, con y sin audio) y del logo, con archivos sintéticos de resultado conocido. Necesitan ffmpeg.
Se ejecutan con ./creador probar (o: python -m servidor.pruebas_escenas)."""
from __future__ import annotations

import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path


def _clip(ruta: Path, ancho: int, alto: int, segundos: float, audio: bool = True, color: str = "0x335577", rotacion: int = 0) -> None:
    entradas = ["-f", "lavfi", "-i", f"color=c={color}:s={ancho}x{alto}:d={segundos}:r=24"] + (["-f", "lavfi", "-i", f"sine=frequency=330:duration={segundos}"] if audio else [])
    subprocess.run(["ffmpeg", "-y", "-v", "error", *entradas, "-t", str(segundos), "-c:v", "libx264", "-pix_fmt", "yuv420p"] + (["-c:a", "aac"] if audio else []) + [str(ruta)], check=True)
    if rotacion:  # como un MOV de iPhone grabado de lado: los píxeles son horizontales y una marca dice «gíralo»
        girado = ruta.with_name("girado-" + ruta.name)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-display_rotation", str(rotacion), "-i", str(ruta), "-c", "copy", str(girado)], check=True)
        girado.replace(ruta)


def _png(ruta: Path, ancho: int, alto: int, alfa: bool) -> None:
    def pixel(x: int, y: int) -> bytes:
        return bytes((200, 30, 40, 255 if (x + y) % 3 else 0)) if alfa else bytes((200, 30, 40))

    filas = b"".join(b"\x00" + b"".join(pixel(x, y) for x in range(ancho)) for y in range(alto))

    def trozo(tipo: bytes, datos: bytes) -> bytes:
        return struct.pack(">I", len(datos)) + tipo + datos + struct.pack(">I", zlib.crc32(tipo + datos) & 0xFFFFFFFF)

    ruta.write_bytes(b"\x89PNG\r\n\x1a\n" + trozo(b"IHDR", struct.pack(">IIBBBBB", ancho, alto, 8, 6 if alfa else 2, 0, 0, 0)) + trozo(b"IDAT", zlib.compress(filas)) + trozo(b"IEND", b""))


def correr() -> list[str]:
    from . import escenas

    fallos: list[str] = []

    def ok(condicion: bool, titulo: str) -> None:
        print(("  ✓ " if condicion else "  ✗ ") + titulo)
        if not condicion:
            fallos.append(titulo)

    with tempfile.TemporaryDirectory(prefix="iris-escenas-") as carpeta:
        base = Path(carpeta)
        a, b, c = base / "a.mp4", base / "b.mp4", base / "c.mp4"
        _clip(a, 360, 640, 3.0)
        _clip(b, 640, 360, 2.0, color="0x775533")
        _clip(c, 360, 640, 2.0, audio=False, color="0x337755")

        print("Leer las escenas")
        sa, sb, sc = escenas.sondear(a), escenas.sondear(b), escenas.sondear(c)
        ok(abs(sa["duracion"] - 3.0) < 0.2 and sa["vertical"] and sa["audio"] and (sa["ancho"], sa["alto"]) == (360, 640), f"una toma vertical con audio: {sa}")
        ok(not sb["vertical"] and (sb["ancho"], sb["alto"]) == (640, 360), "una toma horizontal se reconoce como tal")
        ok(not sc["audio"], "una toma sin audio se reconoce")
        girada = base / "girada.mp4"
        try:
            _clip(girada, 640, 360, 2.0, rotacion=90)
            sg = escenas.sondear(girada)
            ok(sg["vertical"] and (sg["ancho"], sg["alto"]) == (360, 640), f"un video grabado de lado con marca de rotación se lee como vertical ({sg['ancho']}×{sg['alto']})")
        except subprocess.CalledProcessError:
            print("  · (este ffmpeg no sabe escribir la marca de rotación: se omite esa prueba)")
        (base / "falso.mp4").write_bytes(b"esto no es un video")
        try:
            escenas.sondear(base / "falso.mp4")
            ok(False, "un archivo falso se rechaza")
        except ValueError:
            ok(True, "un archivo que no es video se rechaza con un error claro")

        print("Unir las escenas")
        union = escenas.unir([{"archivo": a, "duracion": sa["duracion"], "audio": True}, {"archivo": b, "duracion": sb["duracion"], "audio": True},
                              {"archivo": c, "duracion": sc["duracion"], "audio": False}], base / "union.mp4", 360, 640)
        su = escenas.sondear(base / "union.mp4")
        esperado = sa["duracion"] + sb["duracion"] + sc["duracion"]
        ok(abs(su["duracion"] - esperado) < 0.25 and (su["ancho"], su["alto"]) == (360, 640) and su["audio"], f"tres escenas de distinto tamaño y una sin audio dan un solo video de {su['duracion']} s en 360×640 con audio")
        ok(union["limites"] == [round(sa["duracion"], 3), round(sa["duracion"] + sb["duracion"], 3)], f"los límites entre escenas quedan donde terminan las anteriores: {union['limites']}")
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=duration", "-of", "csv=p=0", str(base / "union.mp4")], capture_output=True, text=True)
        ok(abs(float(r.stdout.strip()) - su["duracion"]) < 0.3, "el audio dura lo mismo que la imagen (no se desfasa al unir)")
        muestra = subprocess.run(["ffmpeg", "-v", "error", "-ss", "4.0", "-i", str(base / "union.mp4"), "-frames:v", "1", "-vf", "scale=1:1,format=rgb24", "-f", "rawvideo", "-"], capture_output=True).stdout
        ok(len(muestra) == 3 and muestra[0] > muestra[2], "la escena horizontal se recorta para llenar el cuadro vertical (su color naranja se ve a los 4 s)")
        una = escenas.unir([{"archivo": a, "duracion": sa["duracion"], "audio": True}], base / "una.mp4", 360, 640)
        ok(una["limites"] == [] and abs(una["duracion"] - sa["duracion"]) < 0.01, "con una sola escena no hay límites")
        try:
            escenas.unir([], base / "nada.mp4")
            ok(False, "unir sin escenas falla")
        except RuntimeError as error:
            ok("No hay escenas" in str(error), "unir sin escenas da un error claro")
        try:
            escenas.unir([{"archivo": base / "falso.mp4", "duracion": 2.0, "audio": True}], base / "malo.mp4")
            ok(False, "unir un archivo roto falla")
        except RuntimeError as error:
            ok("No pude unir" in str(error), "unir un archivo roto da un error claro, no un fallo de ffmpeg sin explicar")

        print("Logo de la marca")
        con, sin, jpg = base / "con.png", base / "sin.png", base / "foto.jpg"
        _png(con, 64, 48, True)
        _png(sin, 64, 48, False)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(sin), str(jpg)], check=True)
        lc, ls, lj = escenas.sondear_imagen(con), escenas.sondear_imagen(sin), escenas.sondear_imagen(jpg)
        ok((lc["ancho"], lc["alto"], lc["transparente"]) == (64, 48, True), f"un PNG con transparencia se reconoce ({lc})")
        ok(not ls["transparente"] and not lj["transparente"], "un PNG sin transparencia y un JPG se reconocen como opacos")
        for nombre, contenido in (("falso.png", b"no es una imagen"), ("diminuto.png", None)):
            ruta = base / nombre
            if contenido is None:
                _png(ruta, 4, 4, True)
            else:
                ruta.write_bytes(contenido)
            try:
                escenas.sondear_imagen(ruta)
                ok(False, f"{nombre} se rechaza")
            except ValueError:
                ok(True, f"{nombre}: se rechaza con un error claro")
    return fallos


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "herramientas"))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.exit(1 if correr() else 0)
