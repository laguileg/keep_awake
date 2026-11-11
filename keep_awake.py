#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KEEP AWAKE
Mantiene un equipo Windows activo durante procesos largos (cargas de datos,
descargas, respaldos): evita la suspensión, la hibernación y, si quieres,
el apagado de la pantalla, usando la API nativa de Windows
SetThreadExecutionState (la misma que usan PowerToys Awake o Caffeine).
Opcionalmente genera un pulso de red periódico para que una VPN no se
desconecte por falta de tráfico.

Lee:     keep_awake.ini junto al script o al .exe. Si no existe, lo crea
         con valores por defecto en el primer arranque.
Genera:  keep_awake.log con la actividad (si log_to_file = true).

Requiere: solo la biblioteca estándar de Python (sin pip install).
          Para crear el .exe: py -m pip install pyinstaller

Uso:
  py keep_awake.py
  keep_awake.bat
  py keep_awake.py --help

Para detener: Ctrl+C en la consola, o cerrar la ventana. Al salir, el
equipo vuelve a su comportamiento normal de energía.
"""

import argparse
import ctypes
import configparser
import os
import signal
import socket
import sys
import time
import logging
from datetime import datetime

# ---------------------------------------------------------------------------
# Constantes de la API de Windows (kernel32.SetThreadExecutionState)
# ---------------------------------------------------------------------------
ES_CONTINUOUS       = 0x80000000  # el estado persiste hasta el proximo llamado
ES_SYSTEM_REQUIRED  = 0x00000001  # evita suspension / hibernacion del sistema
ES_DISPLAY_REQUIRED = 0x00000002  # evita que se apague la pantalla

VERSION     = "1.0.0"
APP_NAME    = "KeepAwake"
INI_NAME    = "keep_awake.ini"

# Plantilla del archivo de parametros que se crea si no existe.
DEFAULT_INI = """\
# ============================================================
#  keep_awake.ini - Parametros de KeepAwake
#  Edita los valores y vuelve a ejecutar el programa.
# ============================================================

[general]
# Mantener la pantalla encendida ademas del sistema (true / false).
# Si solo te interesa que el equipo no se suspenda pero la pantalla
# puede apagarse, pon false.
keep_display_on = true

# Cada cuantos segundos se re-afirma el estado "mantener activo".
# 30 es suficiente y muy liviano.
refresh_interval_sec = 30

# Tiempo maximo de ejecucion en minutos (0 = indefinido, hasta que lo cierres).
# Util si sabes que tu proceso dura ~180 min: ponlo y el programa se libera solo.
max_runtime_min = 0

# Registrar actividad en un archivo de log (true / false).
log_to_file = true
log_file = keep_awake.log

[network_keepalive]
# Activa esto SOLO si tu VPN se cae por inactividad de TRAFICO de red
# (no por suspension del equipo, que ya queda cubierta arriba).
enabled = false

# IMPORTANTE: usa un host INTERNO accesible a traves de la VPN, para que
# el trafico viaje por el tunel y cuente como actividad. Ejemplo: la IP de
# un servidor interno o controlador de dominio. (8.8.8.8:53 es solo ejemplo.)
host = 8.8.8.8
port = 53

# Cada cuantos segundos se genera el pulso de red.
interval_sec = 60

# Timeout de cada intento de conexion (segundos).
timeout_sec = 5
"""

_stop = False


def _on_signal(signum, frame):
    global _stop
    _stop = True


def base_dir() -> str:
    """Carpeta donde esta el EXE (o el .py si se ejecuta sin compilar)."""
    if getattr(sys, "frozen", False):  # ejecutado como EXE (PyInstaller)
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def load_config() -> configparser.ConfigParser:
    """Carga el .ini junto al ejecutable; lo crea con defaults si no existe."""
    ini_path = os.path.join(base_dir(), INI_NAME)
    if not os.path.exists(ini_path):
        try:
            with open(ini_path, "w", encoding="utf-8") as f:
                f.write(DEFAULT_INI)
            print(f"Se creo el archivo de parametros: {ini_path}")
        except OSError as e:
            print(f"No se pudo crear {ini_path}: {e}")

    cfg = configparser.ConfigParser()
    cfg.read_string(DEFAULT_INI)   # valores por defecto en memoria
    try:
        cfg.read(ini_path, encoding="utf-8")  # sobrescribe con lo del archivo
    except (configparser.Error, OSError) as e:
        print(f"Advertencia leyendo {INI_NAME}, se usan valores por defecto: {e}")
    return cfg


def setup_logging(cfg: configparser.ConfigParser) -> None:
    handlers = [logging.StreamHandler(sys.stdout)]
    if cfg.getboolean("general", "log_to_file", fallback=True):
        log_path = os.path.join(base_dir(), cfg.get("general", "log_file",
                                                     fallback="keep_awake.log"))
        try:
            handlers.append(logging.FileHandler(log_path, encoding="utf-8"))
        except OSError as e:
            print(f"No se pudo abrir el log de archivo: {e}")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
    )


def set_keep_awake(keep_display_on: bool) -> bool:
    """Indica a Windows que no se suspenda. Devuelve True si tuvo exito."""
    flags = ES_CONTINUOUS | ES_SYSTEM_REQUIRED
    if keep_display_on:
        flags |= ES_DISPLAY_REQUIRED
    result = ctypes.windll.kernel32.SetThreadExecutionState(flags)
    return result != 0  # 0 = fallo


def release_keep_awake() -> None:
    """Libera el bloqueo: el equipo vuelve a su comportamiento normal."""
    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)


def network_pulse(host: str, port: int, timeout: float) -> bool:
    """Abre y cierra una conexion TCP para generar trafico saliente."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


class FormateadorAyuda(argparse.RawDescriptionHelpFormatter):
    """Formateador de argparse con el encabezado 'uso:' en español."""

    def add_usage(self, usage, actions, groups, prefix=None):
        return super().add_usage(usage, actions, groups, prefix if prefix is not None else "uso: ")


def crear_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="keep_awake.py",
        description=("Mantiene Windows activo (sin suspenderse) mientras el programa esté abierto. "
                     "Los parámetros se editan en keep_awake.ini, junto al script o al .exe."),
        epilog=(
            "Ejemplos:\n"
            "  py keep_awake.py\n"
            "      mantiene el equipo activo hasta que presiones Ctrl+C\n"
            "  keep_awake.bat\n"
            "      lo mismo, con doble clic desde el Explorador\n"
            "  keep_awake.exe\n"
            "      versión empaquetada (ver README para crearla)\n\n"
            "Parámetros principales de keep_awake.ini:\n"
            "  keep_display_on       true/false: mantener también la pantalla encendida\n"
            "  max_runtime_min       minutos máximos de ejecución (0 = sin límite)\n"
            "  [network_keepalive]   pulso de red para que la VPN no se desconecte"
        ),
        formatter_class=FormateadorAyuda,
        add_help=False,
    )
    parser._optionals.title = "opciones"
    parser.add_argument("-h", "--help", action="help", help="muestra esta ayuda y termina")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}",
                        help="muestra la versión y termina")
    return parser


def main() -> int:
    crear_parser().parse_args()

    if os.name != "nt":
        print("Este programa esta disenado para Windows.")
        return 1

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _on_signal)
        except (ValueError, OSError):
            pass

    cfg = load_config()
    setup_logging(cfg)

    keep_display_on  = cfg.getboolean("general", "keep_display_on", fallback=True)
    refresh_interval = cfg.getint("general", "refresh_interval_sec", fallback=30)
    max_runtime_min  = cfg.getint("general", "max_runtime_min", fallback=0)

    net_enabled  = cfg.getboolean("network_keepalive", "enabled", fallback=False)
    net_host     = cfg.get("network_keepalive", "host", fallback="8.8.8.8")
    net_port     = cfg.getint("network_keepalive", "port", fallback=53)
    net_interval = cfg.getint("network_keepalive", "interval_sec", fallback=60)
    net_timeout  = cfg.getfloat("network_keepalive", "timeout_sec", fallback=5.0)

    if not set_keep_awake(keep_display_on):
        logging.error("SetThreadExecutionState fallo. Sin privilegios suficientes?")
        return 1

    logging.info("%s %s iniciado. Pantalla activa=%s | keepalive de red=%s",
                 APP_NAME, VERSION, keep_display_on, net_enabled)
    if max_runtime_min > 0:
        logging.info("Se detendra automaticamente en %d minutos.", max_runtime_min)
    logging.info("Para salir: Ctrl+C o cerrar la ventana.")

    start = time.time()
    last_refresh = 0.0
    last_pulse = 0.0
    deadline = start + max_runtime_min * 60 if max_runtime_min > 0 else None

    try:
        while not _stop:
            now = time.time()

            if deadline and now >= deadline:
                logging.info("Tiempo maximo alcanzado. Finalizando.")
                break

            if now - last_refresh >= refresh_interval:
                set_keep_awake(keep_display_on)
                last_refresh = now

            if net_enabled and now - last_pulse >= net_interval:
                ok = network_pulse(net_host, net_port, net_timeout)
                logging.info("Pulso de red -> %s:%s : %s",
                             net_host, net_port, "OK" if ok else "sin respuesta")
                last_pulse = now

            time.sleep(1)
    finally:
        release_keep_awake()
        logging.info("%s finalizado. El equipo vuelve a su comportamiento normal.",
                     APP_NAME)
    return 0


if __name__ == "__main__":
    sys.exit(main())
