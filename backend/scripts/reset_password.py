"""CLI para repor a palavra-passe do dono do arquivo.

Uso::

    # interativo (pede a nova password sem mostrar no terminal)
    python -m backend.scripts.reset_password

    # explícito
    python -m backend.scripts.reset_password --username diogo --password novaPassXYZ123

Funciona offline contra o ficheiro SQLite — útil quando o utilizador se
esqueceu da palavra-passe e a aplicação não tem fluxo de recuperação por
e-mail (é, por desenho, ``local-first``).
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import sys

from sqlalchemy import select

from backend.core.database import AsyncSessionLocal, init_db
from backend.core.security import hash_password
from backend.models.user import User


async def _run(username: str | None, new_password: str) -> int:
    """Atualiza o hash da palavra-passe. Devolve um ``exit code``."""
    if len(new_password) < 8:
        print("✗ A nova palavra-passe tem de ter pelo menos 8 caracteres.", file=sys.stderr)
        return 2

    await init_db()                                   # garante schema actualizado

    async with AsyncSessionLocal() as db:
        if username:
            stmt = select(User).where(User.username == username)
        else:
            # Por defeito, atualiza o owner — o caso típico em local-first.
            stmt = select(User).where(User.is_owner.is_(True))

        result = await db.execute(stmt)
        user   = result.scalar_one_or_none()

        if not user:
            target = username or "owner"
            print(f"✗ Utilizador '{target}' não encontrado na base de dados.", file=sys.stderr)
            return 3

        user.hashed_password = hash_password(new_password)
        await db.commit()

        print(f"✓ Palavra-passe atualizada para '{user.username}'.")
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reset da palavra-passe (uso local — sem confirmação por e-mail).",
    )
    parser.add_argument("--username", help="Nome de utilizador. Por defeito é o dono do arquivo.")
    parser.add_argument("--password", help="Nova palavra-passe. Se omitida, é pedida interativamente.")
    args = parser.parse_args()

    new_password = args.password
    if not new_password:
        new_password = getpass.getpass("Nova palavra-passe: ")
        confirmation = getpass.getpass("Confirma: ")
        if new_password != confirmation:
            print("✗ As palavras-passe não coincidem.", file=sys.stderr)
            sys.exit(2)

    code = asyncio.run(_run(args.username, new_password))
    sys.exit(code)


if __name__ == "__main__":
    main()
