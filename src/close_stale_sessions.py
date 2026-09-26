#!/usr/bin/env python3
"""
Cierra los entrenamientos que llevan demasiado tiempo abiertos.

Una sesión "abierta" es aquella que se empezó pero nunca se terminó
(``ended_at IS NULL``). Si se deja así, la app la considera en curso para
siempre. Este script marca como terminadas (``ended_at``) las que llevan más
de ``--days`` días abiertas, usando como referencia la hora de inicio.

Uso:
    python close_stale_sessions.py                 # cierra las de más de 7 días
    python close_stale_sessions.py --days 14       # otro umbral
    python close_stale_sessions.py --dry-run       # solo lista, no modifica
    python close_stale_sessions.py --now 2026-09-01T00:00:00  # fecha fija (tests)

Pensado para ejecutarse desde cron o un timer de systemd. En docker:
    docker compose exec api python close_stale_sessions.py
"""
import argparse
import sys
from datetime import datetime, timedelta
from typing import Optional

from app.db.base import SessionLocal
from app.models.session import Session as ClimbingSession


def find_stale_sessions(db, cutoff: datetime):
    """Devuelve las sesiones abiertas cuyo inicio es anterior a ``cutoff``.

    Se ordenan por fecha de inicio para que el log sea legible.
    """
    return (
        db.query(ClimbingSession)
        .filter(
            ClimbingSession.ended_at.is_(None),
            ClimbingSession.started_at < cutoff,
        )
        .order_by(ClimbingSession.started_at.asc(), ClimbingSession.id.asc())
        .all()
    )


def close_stale_sessions(db, days: int = 7, now: Optional[datetime] = None, dry_run: bool = False):
    """Cierra las sesiones abiertas de más de ``days`` días.

    Devuelve la lista de sesiones afectadas (o que se habrían afectado en
    modo ``dry_run``).
    """
    now = now or datetime.utcnow()
    cutoff = now - timedelta(days=days)
    sessions = find_stale_sessions(db, cutoff)

    for session in sessions:
        # El cierre no puede ser anterior al inicio. Para sesiones muy
        # antiguas se cierra una hora después de empezar (duración razonable).
        ended_at = min(now, session.started_at + timedelta(hours=1))
        print(
            f"  - id={session.id} user_id={session.user_id} "
            f"inicio={session.started_at} "
            f"-> cierre={ended_at if not dry_run else '(dry-run)'}"
        )
        if not dry_run:
            session.ended_at = ended_at

    if not dry_run and sessions:
        db.commit()

    return sessions


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Cierra entrenamientos abiertos durante más de N días."
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Antigüedad mínima en días para cerrar una sesión (por defecto 7).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo muestra las sesiones que se cerrarían, sin modificar la BD.",
    )
    parser.add_argument(
        "--now",
        type=str,
        default=None,
        help="Fecha/hora de referencia en formato ISO (por defecto, ahora). "
        "Útil para probar.",
    )
    args = parser.parse_args()

    if args.days < 0:
        parser.error("--days no puede ser negativo")

    now = None
    if args.now:
        try:
            now = datetime.fromisoformat(args.now)
        except ValueError:
            parser.error(f"--now no es una fecha válida: {args.now!r}")

    db = SessionLocal()
    try:
        print(
            f"Buscando sesiones abiertas desde hace más de {args.days} días"
            f"{' (dry-run)' if args.dry_run else ''}..."
        )
        sessions = close_stale_sessions(
            db, days=args.days, now=now, dry_run=args.dry_run
        )
        if sessions:
            verb = "se cerrarían" if args.dry_run else "cerradas"
            print(f"{len(sessions)} sesión(es) {verb}.")
        else:
            print("No hay sesiones antiguas abiertas.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
