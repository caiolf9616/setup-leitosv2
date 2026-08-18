"""Sincroniza credenciais, enfermarias e leitos do catálogo oficial.

Uso:
    cd backend
    python -m scripts.seed_data

A sincronização é idempotente. Leitos antigos com histórico não são apagados:
ficam bloqueados para preservar a auditoria. Registros antigos sem eventos são
removidos quando não pertencem mais ao catálogo.
"""

from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect

from app.auth import hash_password
from app.bed_catalog import UNIT_CATALOG
from app.database import SessionLocal, engine
from app.models import Bed, BedEvent, UserAccount, UserRole, Ward
from app.settings import get_settings

COORDENADOR_UNIT_GROUP = "COORDENACAO"
ADMINISTRADOR_LOGIN = "ADMINISTRADOR"
settings = get_settings()


def _require_current_schema() -> None:
    """Impede o seed de alterar dados antes de todas as migrações rodarem."""
    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    script = ScriptDirectory.from_config(config)
    expected_revision = script.get_current_head()

    tables = set(inspect(engine).get_table_names())
    if not tables:
        raise RuntimeError(
            "Banco sem schema. Execute `python -m alembic upgrade head` antes do seed."
        )

    with engine.connect() as connection:
        current_revision = MigrationContext.configure(connection).get_current_revision()
    if current_revision != expected_revision:
        raise RuntimeError(
            "Schema desatualizado. Execute `python -m alembic upgrade head` antes do seed. "
            "Para um banco existente criado antes do Alembic e já conferido, use uma única "
            "vez `python -m alembic stamp head`."
        )


def _get_or_create_ward(db, unit_group: str, key: str, label: str) -> Ward:
    ward = db.query(Ward).filter_by(name=key).one_or_none()
    if ward is None:
        ward = Ward(name=key, display_name=label, unit_group=unit_group)
        db.add(ward)
        db.flush()
    else:
        ward.unit_group = unit_group
        ward.display_name = label
    return ward


def run() -> None:
    _require_current_schema()

    db = SessionLocal()
    created_wards = created_beds = archived_beds = removed_beds = 0
    try:
        catalog_keys: set[str] = set()

        for unit_group, (display_name, wards) in UNIT_CATALOG.items():
            for ward_data in wards:
                catalog_keys.add(ward_data.key)
                ward_exists = db.query(Ward.id).filter_by(name=ward_data.key).first() is not None
                ward = _get_or_create_ward(
                    db, unit_group, ward_data.key, ward_data.label
                )
                if not ward_exists:
                    created_wards += 1

                expected = set(ward_data.beds)
                existing = {bed.number: bed for bed in ward.beds}
                for number in ward_data.beds:
                    bed = existing.get(number)
                    if bed is None:
                        db.add(Bed(ward_id=ward.id, number=number))
                        created_beds += 1
                    elif bed.blocked:
                        bed.blocked = False

                for number, bed in existing.items():
                    if number in expected:
                        continue
                    has_events = db.query(BedEvent.id).filter_by(bed_id=bed.id).first() is not None
                    if has_events:
                        if not bed.blocked:
                            bed.blocked = True
                            archived_beds += 1
                    else:
                        db.delete(bed)
                        removed_beds += 1

        # Wards antigas que não constam mais no catálogo seguem a mesma regra:
        # preserva histórico, remove somente dados vazios/de demonstração.
        old_wards = db.query(Ward).filter(~Ward.name.in_(catalog_keys)).all()
        for ward in old_wards:
            for bed in list(ward.beds):
                has_events = db.query(BedEvent.id).filter_by(bed_id=bed.id).first() is not None
                if has_events:
                    if not bed.blocked:
                        bed.blocked = True
                        archived_beds += 1
                else:
                    db.delete(bed)
                    removed_beds += 1
            db.flush()
            # A coleção ORM ainda pode conter objetos marcados para exclusão
            # nesta transação; consulte o banco após o flush.
            if db.query(Bed.id).filter_by(ward_id=ward.id).first() is None:
                db.delete(ward)

        coordinator_account = (
            db.query(UserAccount)
            .filter_by(username=COORDENADOR_UNIT_GROUP)
            .one_or_none()
        )
        if coordinator_account is None:
            if not settings.seed_coordinator_password:
                raise RuntimeError(
                    "Defina SEED_COORDINATOR_PASSWORD para criar a conta inicial "
                    "da coordenação."
                )
            db.add(
                UserAccount(
                    username=COORDENADOR_UNIT_GROUP,
                    full_name="Coordenação",
                    password_hash=hash_password(settings.seed_coordinator_password),
                    unit_group=COORDENADOR_UNIT_GROUP,
                    role=UserRole.COORDENADOR,
                    employment_type="coordenador_geral",
                    active=True,
                )
            )

        administrator = (
            db.query(UserAccount)
            .filter_by(username=ADMINISTRADOR_LOGIN)
            .one_or_none()
        )
        if administrator is None:
            if not settings.seed_admin_password:
                raise RuntimeError(
                    "Defina SEED_ADMIN_PASSWORD para criar a conta inicial "
                    "de administração."
                )
            db.add(
                UserAccount(
                    username=ADMINISTRADOR_LOGIN,
                    full_name="Administrador do sistema",
                    password_hash=hash_password(settings.seed_admin_password),
                    unit_group=COORDENADOR_UNIT_GROUP,
                    role=UserRole.COORDENADOR,
                    employment_type="administrador",
                    active=True,
                )
            )
            print(f"Administrador criado: login={ADMINISTRADOR_LOGIN}")

        db.commit()
        total_wards = db.query(Ward).filter(Ward.name.in_(catalog_keys)).count()
        total_beds = (
            db.query(Bed)
            .join(Ward)
            .filter(Ward.name.in_(catalog_keys), Bed.blocked.is_(False))
            .count()
        )
        print(
            "Sincronização concluída: "
            f"{total_wards} enfermarias, {total_beds} leitos reais; "
            f"{created_wards} enfermarias e {created_beds} leitos criados; "
            f"{archived_beds} leitos antigos bloqueados e {removed_beds} removidos."
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
