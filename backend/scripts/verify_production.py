"""Valida a configuração antes de iniciar ou atualizar a produção."""

import argparse
from pathlib import Path

from app.settings import Settings


PLACEHOLDER_PARTS = {
    "troque",
    "defina",
    "gere",
    "remova",
    "exemplo",
    "senha",
    "secret",
    "change-me",
}


def _looks_like_placeholder(value: str | None) -> bool:
    normalized = (value or "").strip().lower()
    return not normalized or any(part in normalized for part in PLACEHOLDER_PARTS)


def validate(settings: Settings, *, initial_seed: bool = False) -> list[str]:
    errors: list[str] = []
    database_url = settings.database_url.lower()

    if settings.environment != "production":
        errors.append("ENVIRONMENT precisa ser production")
    if not settings.cookie_secure and not settings.allow_insecure_internal_http:
        errors.append("COOKIE_SECURE precisa ser true ou o HTTP interno precisa ser autorizado explicitamente")
    if not database_url.startswith("postgresql+psycopg://"):
        errors.append("DATABASE_URL precisa usar PostgreSQL com o driver psycopg")
    if _looks_like_placeholder(settings.secret_key) or len(settings.secret_key) < 32:
        errors.append("SECRET_KEY precisa ser real, aleatória e ter ao menos 32 caracteres")
    if settings.allow_homologation_data:
        errors.append("ALLOW_HOMOLOGATION_DATA precisa ser false")

    seed_values = (
        settings.seed_coordinator_password,
        settings.seed_admin_password,
    )
    if initial_seed:
        if any(_looks_like_placeholder(value) or len(value or "") < 12 for value in seed_values):
            errors.append("senhas iniciais precisam ser reais e ter ao menos 12 caracteres")
    elif any(seed_values):
        errors.append("remova SEED_COORDINATOR_PASSWORD e SEED_ADMIN_PASSWORD após o seed")

    return errors


def run() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--env-file",
        default=".env.production",
        help="arquivo de ambiente de produção",
    )
    parser.add_argument(
        "--initial-seed",
        action="store_true",
        help="permite e valida as duas senhas usadas apenas no primeiro seed",
    )
    args = parser.parse_args()
    env_file = Path(args.env_file).resolve()
    if not env_file.is_file():
        raise RuntimeError(f"Arquivo de produção não encontrado: {env_file}")

    settings = Settings(_env_file=env_file)
    errors = validate(settings, initial_seed=args.initial_seed)
    if errors:
        raise RuntimeError("Configuração de produção inválida:\n- " + "\n- ".join(errors))
    print(f"Configuração de produção aprovada: {env_file}")


if __name__ == "__main__":
    run()
