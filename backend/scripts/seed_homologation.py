"""Gera histórico determinístico para homologação funcional.

O script recusa produção, exige autorização explícita e só aceita uma base sem
eventos. Assim, não mistura dados artificiais com histórico real.
"""
from datetime import datetime, timedelta, timezone

from app.database import SessionLocal
from app.models import Bed, BedEvent, EventType
from app.settings import get_settings


def run() -> None:
    settings = get_settings()
    if settings.environment != "test":
        raise RuntimeError(
            "Dados de homologação só podem ser gerados com ENVIRONMENT=test."
        )
    if not settings.allow_homologation_data:
        raise RuntimeError(
            "Defina ALLOW_HOMOLOGATION_DATA=true somente no ambiente de homologação."
        )

    db = SessionLocal()
    try:
        if db.query(BedEvent.id).first() is not None:
            raise RuntimeError(
                "A base já possui eventos. Use um banco vazio e descartável para homologação."
            )

        beds = db.query(Bed).filter(Bed.blocked.is_(False)).order_by(Bed.id).all()
        if not beds:
            raise RuntimeError("Nenhum leito ativo encontrado. Execute o seed inicial primeiro.")

        now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        events: list[BedEvent] = []

        def add_event(bed: Bed, event_type: EventType, occurred_at: datetime) -> None:
            events.append(
                BedEvent(
                    bed_id=bed.id,
                    event_type=event_type,
                    occurred_at=occurred_at,
                    recorded_by_unit=bed.ward.unit_group,
                    recorded_by_user="HOMOLOGACAO",
                )
            )

        for bed in beds:
            # Pequena defasagem evita que todos os leitos mudem ao mesmo tempo.
            occupied_at = now - timedelta(days=14) + timedelta(minutes=bed.id % 180)
            release_at = occupied_at + timedelta(days=6, hours=bed.id % 18)
            bucket = bed.id % 10

            add_event(bed, EventType.OCUPADO, occupied_at)
            add_event(bed, EventType.ALTA, release_at)
            if bucket == 9:
                continue

            unoccupied_at = release_at + timedelta(minutes=20 + bed.id % 40)
            add_event(bed, EventType.DESOCUPADO, unoccupied_at)
            if bucket == 8:
                continue

            ready_at = unoccupied_at + timedelta(minutes=60 + bed.id % 120)
            add_event(bed, EventType.APTO, ready_at)
            if bucket == 7:
                continue

            add_event(
                bed,
                EventType.OCUPADO,
                ready_at + timedelta(minutes=30 + bed.id % 90),
            )

        db.add_all(events)
        db.commit()
        print(
            f"Homologação preparada: {len(beds)} leitos e {len(events)} eventos "
            "determinísticos."
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
