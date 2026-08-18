"""Verifica se a base está pronta para o roteiro de homologação."""
from collections import Counter
from datetime import datetime, timedelta, timezone

from app import crud
from app.database import SessionLocal
from app.models import Bed, BedEvent, EventType
from app.routers.reports import bed_times_report


def run() -> None:
    db = SessionLocal()
    try:
        active_beds = db.query(Bed).filter(Bed.blocked.is_(False)).count()
        event_count = db.query(BedEvent).count()
        future_events = (
            db.query(BedEvent)
            .filter(BedEvent.occurred_at > datetime.now(timezone.utc))
            .count()
        )
        pairs = crud.get_beds_with_last_event(db, unit_groups=None)
        current_statuses = Counter(
            event.event_type.value if event else "sem_status"
            for bed, event in pairs
            if not bed.blocked
        )
        available_beds = len(crud.get_available_beds(db))

        end = datetime.now(timezone.utc)
        report = bed_times_report(
            start=end - timedelta(days=14),
            end=end,
            ward_id=None,
            credential=None,
            db=db,
        )
        tracked_seconds = sum(report.totals_seconds.values())

        errors: list[str] = []
        if active_beds == 0:
            errors.append("nenhum leito ativo")
        if event_count < active_beds * 2:
            errors.append("histórico insuficiente")
        if future_events:
            errors.append(f"{future_events} eventos no futuro")
        if len([value for value in EventType if current_statuses[value.value]]) < 4:
            errors.append("os quatro status não aparecem na situação atual")
        if available_beds == 0:
            errors.append("nenhum leito apto para validar o painel público")
        if tracked_seconds == 0:
            errors.append("relatório sem tempo monitorado")

        print(f"Leitos ativos: {active_beds}")
        print(f"Eventos: {event_count}")
        print(f"Situação atual: {dict(current_statuses)}")
        print(f"Leitos no painel: {available_beds}")
        print(f"Horas monitoradas em 14 dias: {tracked_seconds / 3600:.1f}")

        if errors:
            raise RuntimeError("Base de homologação inválida: " + "; ".join(errors))
        print("Base de homologação aprovada.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
