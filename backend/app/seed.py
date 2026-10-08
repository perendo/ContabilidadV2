"""Seed de usuarios iniciales para desarrollo (S1 del quickstart).

Requisito: contraseñas >= 8 caracteres, hash argon2. Idempotente.
"""

from sqlmodel import Session, select

from app.db import engine
from app.models import Ejercicio, Usuario
from app.pgc import sembrar_pgc
from app.services.seguridad import hash_password

SEEDS = [
    {"username": "admin", "email": "admin@contab.local", "password": "admin-2026", "rol": "admin"},
    {
        "username": "contable",
        "email": "contable@contab.local",
        "password": "contable-2026",
        "rol": "contable",
    },
]


def crear_usuarios(session: Session) -> None:
    for data in SEEDS:
        existe = session.exec(select(Usuario).where(Usuario.username == data["username"])).first()
        if existe:
            continue
        session.add(
            Usuario(
                username=data["username"],
                email=data["email"],
                hashed_password=hash_password(data["password"]),
                rol=data["rol"],
            )
        )
    session.commit()


def sembrar_pgc_ejercicios(session: Session) -> int:
    """Rellena el cuadro PGC base en ejercicios creados sin cuentas. Idempotente."""
    total = 0
    for ejercicio in session.exec(select(Ejercicio)).all():
        total += sembrar_pgc(session, ejercicio.id)
    session.commit()
    return total


def main() -> None:
    with Session(engine) as session:
        crear_usuarios(session)
        cuentas = sembrar_pgc_ejercicios(session)
        print("Seed completado. Usuarios: " + ", ".join(s["username"] for s in SEEDS))
        if cuentas:
            print(f"PGC base sembrado en ejercicios existentes: {cuentas} cuentas")


if __name__ == "__main__":
    main()
