#!/home/jzamora/.virtualenvs/taskpilot-env/bin/python3
"""Despliegue de TaskPilot lanzado por la tarea programada de PythonAnywhere.

GitHub Actions no puede entrar al servidor (plan gratuito, sin SSH): lo único
que hace es publicar el SHA aprobado por CI en ``last_ci_ok_sha`` mediante la
Files API. Este script, ejecutado a diario desde la pestaña Tasks, despliega
ese SHA con tres garantías:

1. Solo se despliega lo que CI aprobó (marcador escrito por GitHub Actions).
2. El SHA debe seguir perteneciendo a la historia de ``origin/main``.
3. ``git merge --ff-only`` impide retrocesos y divergencias con producción.

Uso:
    python deploy_task.py --check     # informa del estado, no modifica nada
    python deploy_task.py --dry-run   # muestra el plan, no modifica nada
    python deploy_task.py             # despliegue normal (tarea diaria)
    python deploy_task.py --sha <sha> # despliegue manual de un commit de main
    python deploy_task.py --force      # re-ejecuta migrate/collectstatic/reload
"""

from __future__ import annotations

import argparse
import contextlib
import logging
import os
import re
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
MARKER_NAME = "last_ci_ok_sha"
DEPLOYED_NAME = "last_deployed_sha"
LOCK_NAME = "deploy.lock"
LOG_NAME = "deploy.log"
BACKUPS_TO_KEEP = 3
API_BASE = "https://www.pythonanywhere.com"
DEFAULT_USERNAME = "jzamora"
DEFAULT_DOMAIN = "jzamora.pythonanywhere.com"


class DeployError(RuntimeError):
    """Error controlado que aborta el despliegue sin efectos colaterales."""


def build_logger(log_path: Path | None) -> logging.Logger:
    logger = logging.getLogger("taskpilot.deploy")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(formatter)
    logger.addHandler(stream)
    if log_path is not None:
        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


def load_paths() -> tuple[Path, Path]:
    """Devuelve (directorio de estado, ruta de la BD) según la config de Django."""
    sys.path.insert(0, str(APP_DIR))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django
    from django.conf import settings

    django.setup()
    return Path(settings.DATA_DIR), Path(settings.DATABASES["default"]["NAME"])


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args], cwd=APP_DIR, text=True, capture_output=True, check=False
    )
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise DeployError(f"`git {' '.join(args)}` falló: {detail}")
    return result


def read_sha(path: Path) -> str | None:
    try:
        value = path.read_text(encoding="utf-8").strip().lower()
    except FileNotFoundError:
        return None
    return value if SHA_RE.match(value) else None


def write_sha(path: Path, sha: str) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(f"{sha}\n", encoding="utf-8")
    os.replace(temporary, path)


def acquire_lock(lock_path: Path):
    """Bloqueo exclusivo no bloqueante; None si otro despliegue está en curso."""
    handle = lock_path.open("w", encoding="utf-8")
    try:
        import fcntl
    except ImportError:  # Windows: sin bloqueo real, solo desarrollo local.
        return handle
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None
    return handle


def ensure_commit_available(sha: str, logger: logging.Logger) -> None:
    if git("cat-file", "-e", f"{sha}^{{commit}}", check=False).returncode == 0:
        return
    is_shallow = git("rev-parse", "--is-shallow-repository").stdout.strip() == "true"
    if not is_shallow:
        raise DeployError(f"El commit {sha} no existe en el clon de producción.")
    logger.info("Commit %s fuera del clon shallow; ejecutando fetch --unshallow.", sha)
    git("fetch", "--unshallow", "origin")
    if git("cat-file", "-e", f"{sha}^{{commit}}", check=False).returncode != 0:
        raise DeployError(f"El commit {sha} sigue sin estar disponible tras --unshallow.")


def requirements_changed(base: str | None, target: str, logger: logging.Logger) -> bool:
    if not base or git("cat-file", "-e", f"{base}^{{commit}}", check=False).returncode != 0:
        logger.info("Sin referencia de despliegue anterior: se instalarán dependencias.")
        return True
    diff = git("diff", "--quiet", base, target, "--", "requirements.txt", check=False)
    if diff.returncode not in (0, 1):
        raise DeployError(f"No se pudo comparar requirements.txt: {diff.stderr.strip()}")
    return diff.returncode == 1


def backup_database(db_path: Path, backup_dir: Path, logger: logging.Logger) -> Path:
    if not db_path.is_file():
        raise DeployError(f"No existe la base de datos en {db_path}; se aborta antes de migrar.")

    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = backup_dir / f"db_{stamp}.sqlite3"

    users = tasks = 0
    try:
        source = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        copy = sqlite3.connect(destination)
        try:
            source.backup(copy)
        finally:
            source.close()
            copy.close()

        with contextlib.closing(sqlite3.connect(destination)) as check:
            integrity = check.execute("PRAGMA integrity_check;").fetchone()
            if not integrity or integrity[0] != "ok":
                raise DeployError(f"El respaldo {destination} no pasó integrity_check.")
            try:
                users = check.execute("SELECT COUNT(*) FROM auth_user;").fetchone()[0]
                tasks = check.execute("SELECT COUNT(*) FROM todos_todotask;").fetchone()[0]
            except sqlite3.Error as exc:
                raise DeployError(f"El respaldo {destination} está vacío o incompleto: {exc}") from exc
    except DeployError:
        destination.unlink(missing_ok=True)
        logger.warning("Backup parcial o inválido eliminado: %s", destination)
        raise
    except Exception as exc:  # noqa: BLE001 - limpia el archivo parcial ante cualquier fallo
        destination.unlink(missing_ok=True)
        logger.warning("Backup parcial o inválido eliminado: %s", destination)
        raise DeployError(f"El respaldo falló: {exc}") from exc

    logger.info("Respaldo verificado: %s (usuarios=%s, tareas=%s)", destination, users, tasks)
    return destination


def rotate_backups(backup_dir: Path, keep: int, logger: logging.Logger) -> None:
    backups = sorted(backup_dir.glob("db_*.sqlite3"), key=lambda path: path.name)
    for stale in backups[:-keep] if len(backups) > keep else []:
        stale.unlink(missing_ok=True)
        logger.info("Respaldo antiguo eliminado: %s", stale)


def install_requirements(logger: logging.Logger) -> None:
    logger.info("requirements.txt cambió: instalando dependencias.")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
        cwd=APP_DIR,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()[-2000:]
        raise DeployError(f"pip install falló: {detail}")


def run_manage(command: str, logger: logging.Logger, *args: str) -> None:
    logger.info("manage.py %s", command)
    result = subprocess.run(
        [sys.executable, "manage.py", command, *args],
        cwd=APP_DIR,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()[-2000:]
        raise DeployError(f"manage.py {command} falló: {detail}")


def reload_webapp(logger: logging.Logger) -> None:
    token = (os.getenv("API_TOKEN") or os.getenv("PA_API_TOKEN") or "").strip()
    if not token:
        raise DeployError("No hay token de API (API_TOKEN) para recargar la web app.")
    username = os.getenv("TASKPILOT_USERNAME", DEFAULT_USERNAME)
    domain = os.getenv("TASKPILOT_WEBAPP_DOMAIN", DEFAULT_DOMAIN)
    url = f"{API_BASE}/api/v0/user/{username}/webapps/{domain}/reload/"
    request = urllib.request.Request(
        url, data=b"", method="POST", headers={"Authorization": f"Token {token}"}
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read().decode("utf-8", "replace").strip()
            status = response.status
    except urllib.error.HTTPError as exc:
        raise DeployError(f"La recarga devolvió HTTP {exc.code}.") from exc
    except urllib.error.URLError as exc:
        raise DeployError(f"No se pudo contactar la API de PythonAnywhere: {exc.reason}") from exc
    if status != 200:
        raise DeployError(f"La recarga devolvió HTTP {status}: {body}")
    logger.info("Web app recargada (%s): %s", domain, body or "sin cuerpo")


def deploy(args: argparse.Namespace, logger: logging.Logger) -> int:
    state_dir, db_path = load_paths()
    backup_dir = Path(os.getenv("TASKPILOT_BACKUP_DIR") or (Path.home() / "backups"))
    marker = state_dir / MARKER_NAME
    deployed = state_dir / DEPLOYED_NAME

    if args.sha:
        target = args.sha.strip().lower()
        if not SHA_RE.match(target):
            raise DeployError(f"SHA inválido: {args.sha!r}")
        logger.info("SHA indicado manualmente: %s", target)
    else:
        target = read_sha(marker)
        if not target:
            logger.info("Sin marcador válido en %s: CI no ha aprobado nada nuevo.", marker)
            return 0
        logger.info("SHA aprobado por CI: %s", target)

    head = git("rev-parse", "HEAD").stdout.strip()
    last_deployed = read_sha(deployed)
    logger.info("HEAD=%s último_desplegado=%s", head, last_deployed)

    if head == target and last_deployed == target and not args.force:
        logger.info("Producción ya está en %s; no hay nada que hacer.", target)
        return 0

    git("fetch", "--prune", "origin", "main")
    ensure_commit_available(target, logger)

    ancestors = git("merge-base", "--is-ancestor", target, "origin/main", check=False)
    if ancestors.returncode == 1:
        raise DeployError(f"{target} no pertenece a la historia de origin/main; se aborta.")
    if ancestors.returncode != 0:
        raise DeployError(f"No se pudo comprobar la ascendencia de {target}: {ancestors.stderr}")

    if args.check or args.dry_run:
        mode = "check" if args.check else "dry-run"
        logger.info("[%s] merge --ff-only %s", mode, target)
        logger.info("[%s] respaldo en %s", mode, backup_dir / "db_<UTC>.sqlite3")
        logger.info("[%s] pip si cambió requirements.txt, migrate, collectstatic, clearsessions, reload", mode)
        return 0

    if head != target:
        git("merge", "--ff-only", target)
    if git("rev-parse", "HEAD").stdout.strip() != target:
        raise DeployError("El HEAD de producción no coincide con el SHA aprobado.")

    if args.force or requirements_changed(last_deployed, target, logger):
        install_requirements(logger)

    backup = backup_database(db_path, backup_dir, logger)
    rotate_backups(backup.parent, BACKUPS_TO_KEEP, logger)

    run_manage("migrate", logger, "--noinput")
    run_manage("collectstatic", logger, "--noinput")
    run_manage("clearsessions", logger)
    reload_webapp(logger)

    write_sha(deployed, target)
    logger.info("Despliegue completado: %s (respaldo %s)", target, backup.name)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Despliega en TaskPilot el SHA aprobado por CI.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--sha", help="SHA de main a desplegar (por defecto, el marcado por CI)")
    parser.add_argument("--check", action="store_true", help="solo informar del estado")
    parser.add_argument("--dry-run", action="store_true", help="mostrar el plan sin ejecutarlo")
    parser.add_argument("--force", action="store_true", help="re-ejecuta migrate/collectstatic/reload aunque HEAD ya esté en el SHA aprobado")
    args = parser.parse_args(argv)

    try:
        state_dir, _ = load_paths()
    except Exception as exc:  # noqa: BLE001 - se reporta como fallo del despliegue
        print(f"ERROR: no se pudo cargar la configuración de Django: {exc}", file=sys.stderr)
        return 1

    logger = build_logger(None if (args.check or args.dry_run) else state_dir / LOG_NAME)

    lock = None
    if not (args.check or args.dry_run):
        lock = acquire_lock(state_dir / LOCK_NAME)
        if lock is None:
            logger.info("Ya hay un despliegue en curso; se sale sin hacer nada.")
            return 0

    try:
        return deploy(args, logger)
    except DeployError as exc:
        logger.error("Despliegue abortado: %s", exc)
        return 1
    except Exception as exc:  # noqa: BLE001 - cualquier fallo inesperado aborta el deploy
        logger.exception("Error inesperado durante el despliegue: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
