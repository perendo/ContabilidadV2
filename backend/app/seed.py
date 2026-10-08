"""Seed de usuarios iniciales para desarrollo (S1 del quickstart).

Requisito: contraseñas >= 8 caracteres, hash argon2. Idempotente.
"""

from sqlmodel import Session, select

from app.db import engine
from app.models import Usuario
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


def main() -> None:
    with Session(engine) as session:
        crear_usuarios(session)
        print("Seed completado. Usuarios: " + ", ".join(s["username"] for s in SEEDS))


if __name__ == "__main__":
    main()
