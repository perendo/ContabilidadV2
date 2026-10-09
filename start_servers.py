"""Arranca el backend (uvicorn) y el frontend (Next.js) de forma portable (Windows/Linux/macOS).
Aplica las migraciones, siembra los usuarios de desarrollo, abre los procesos por servidor,
espera a que ambos estén operativos y abre el navegador.
"""
from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
BACKEND_PORT = 8000
FRONTEND_PORT = 3000
WAIT_TIMEOUT = 90.0

IS_WINDOWS = sys.platform.startswith("win")
CREATE_NEW_CONSOLE = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass


def log(msg: str = "") -> None:
    print(msg, flush=True)


def port_pids(port: int) -> list[str]:
    """PIDs que están escuchando en el puerto indicado."""
    if IS_WINDOWS:
        try:
            out = subprocess.run(
                ["netstat", "-ano"], capture_output=True, text=True, check=False
            ).stdout
        except OSError:
            return []
        pids: list[str] = []
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 5 and parts[3] == "LISTENING" and parts[1].endswith(f":{port}"):
                pids.append(parts[4])
        return pids
    else:
        try:
            out = subprocess.run(
                ["lsof", "-t", f"-i:{port}"], capture_output=True, text=True, check=False
            ).stdout
            return [line.strip() for line in out.splitlines() if line.strip()]
        except OSError:
            return []


def stop_port(port: int, name: str) -> None:
    pids = port_pids(port)
    if not pids:
        log(f"      [OK] Puerto {port} ({name}) libre.")
        return
    log(f"      [AVISO] Puerto {port} ({name}) ocupado por PID(s): {', '.join(pids)}. Deteniendo...")
    for pid in pids:
        if IS_WINDOWS:
            subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True, check=False)
        else:
            try:
                os.kill(int(pid), signal.SIGTERM)
            except OSError:
                pass
    time.sleep(1)
    log("      [OK] Servidor previo detenido.")


def run_step(step: str, args: list[str], cwd: Path) -> None:
    log(step)
    result = subprocess.run(args, cwd=str(cwd), check=False)
    if result.returncode != 0:
        log(f"[ERROR] El comando falló (código {result.returncode}): {' '.join(args)}")
        if sys.stdin.isatty():
            input("Pulsa Enter para salir...")
        sys.exit(result.returncode)


def launch(title: str, command: str, cwd: Path) -> subprocess.Popen:
    """Abre el proceso en consola independiente si está en Windows, o como subproceso en Unix."""
    log(f"      Iniciando proceso: {title}")
    if IS_WINDOWS:
        return subprocess.Popen(
            f'cmd /k "{command}"',
            cwd=str(cwd),
            creationflags=CREATE_NEW_CONSOLE,
            shell=False,
        )
    else:
        return subprocess.Popen(
            command,
            cwd=str(cwd),
            shell=True,
        )


def wait_port(port: int, name: str, timeout: float = WAIT_TIMEOUT) -> bool:
    log(f"      Esperando a {name} (puerto {port})...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1.0)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                log(f"      [OK] {name} operativo en el puerto {port}.")
                return True
        time.sleep(1.0)
    log(f"      [AVISO] {name} no respondió en el puerto {port} tras {int(timeout)} s.")
    return False


def main() -> int:
    log("=" * 44)
    log("  ContabilidadV2 - Arranque de desarrollo")
    log("=" * 44)
    log()
    python = sys.executable

    log("[0/4] Comprobando servidores previos en los puertos...")
    stop_port(BACKEND_PORT, "backend")
    stop_port(FRONTEND_PORT, "frontend")
    log()

    run_step(
        "[1/4] Aplicando migraciones de la base de datos...",
        [python, "-m", "alembic", "upgrade", "head"],
        BACKEND,
    )
    log()

    run_step(
        "[2/4] Sembrando usuarios de desarrollo...",
        [python, "-m", "app.seed"],
        BACKEND,
    )
    log()

    if not (FRONTEND / "node_modules").exists():
        npm_cmd = ["cmd", "/c", "npm install"] if IS_WINDOWS else ["npm", "install"]
        run_step(
            "[*] Dependencias del frontend no encontradas; ejecutando npm install...",
            npm_cmd,
            FRONTEND,
        )
        log()

    log(f"[3/4] Iniciando backend (uvicorn) en http://127.0.0.1:{BACKEND_PORT} ...")
    launch(
        "ContabilidadV2 - Backend",
        f'"{python}" -m uvicorn app.main:app --reload --port {BACKEND_PORT}',
        BACKEND,
    )
    log()

    log(f"[4/4] Iniciando frontend (Next.js) en http://127.0.0.1:{FRONTEND_PORT} ...")
    launch("ContabilidadV2 - Frontend", "npm run dev", FRONTEND)
    log()

    ok_backend = wait_port(BACKEND_PORT, "Backend")
    ok_frontend = wait_port(FRONTEND_PORT, "Frontend")
    log()

    log("=" * 44)
    log("  Entorno en marcha")
    log("=" * 44)
    log(f"  Backend  -> http://127.0.0.1:{BACKEND_PORT}/docs")
    log(f"  Frontend -> http://127.0.0.1:{FRONTEND_PORT}")
    log()
    log("  Usuarios seed: admin/admin-2026 | contable/contable-2026")
    log()

    if ok_backend or ok_frontend:
        log("Abriendo el navegador...")
        if ok_frontend:
            webbrowser.open(f"http://127.0.0.1:{FRONTEND_PORT}")
        if ok_backend:
            webbrowser.open(f"http://127.0.0.1:{BACKEND_PORT}/docs")
    else:
        log("[AVISO] Ningún servidor respondió; no se abre el navegador.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
