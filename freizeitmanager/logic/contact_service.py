"""Fachliche Operationen auf Kontakten und Interaktionen.

Quick Actions sind hier bewusst einzeilig aufrufbar. Lehre aus FPM 0.2.77:
Eine zentrale Aktion darf weder still fehlschlagen noch eine unnoetige
Vorauswahl verlangen. "Marko angerufen" muss ein Aufruf sein, kein Dialog.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from freizeitmanager.database.models import (
    INTERACTION_KINDS,
    KIND_MEET,
    QUALITY_NORMAL,
    STATUS_ACTIVE,
    STATUS_PAUSED,
    Contact,
    Group,
    Interaction,
    PlannedActivity,
    RelationshipLevel,
    RotationSnooze,
    Tag,
)


def _get_or_create(session: Session, model, name: str, **extra):
    name = str(name or "").strip()
    if not name:
        return None
    row = session.scalar(select(model).where(model.name == name))
    if row is None:
        row = model(name=name, **extra)
        session.add(row)
        session.flush()
    return row


def create_contact(session: Session, name: str, *, level: str | None = None,
                   importance: int | None = None,
                   target_interval_days: int | None = None,
                   groups: list[str] | None = None,
                   tags: list[str] | None = None,
                   notes: str | None = None,
                   **fields) -> Contact:
    """Legt einen Kontakt an. Rhythmus und Wichtigkeit erben vom Beziehungsgrad."""
    name = str(name or "").strip()
    if not name:
        raise ValueError("Ein Kontakt braucht einen Namen.")

    level_row = _get_or_create(session, RelationshipLevel, level) if level else None
    if importance is None:
        importance = (level_row.default_importance if level_row else None) or 3
    if target_interval_days is None:
        target_interval_days = (level_row.default_interval_days if level_row else None) or 30

    contact = Contact(name=name,
                      relationship_level_id=level_row.id if level_row else None,
                      importance=max(1, min(5, int(importance))),
                      target_interval_days=max(1, int(target_interval_days)),
                      notes=notes,
                      status=fields.pop("status", STATUS_ACTIVE),
                      **fields)
    # Erst persistieren, dann verknuepfen: sonst verwirft SQLAlchemy beim
    # Autoflush waehrend _get_or_create die Zuordnung stillschweigend.
    session.add(contact)
    session.flush()
    for group_name in groups or []:
        group = _get_or_create(session, Group, group_name)
        if group is not None:
            contact.groups.append(group)
    for tag_name in tags or []:
        tag = _get_or_create(session, Tag, tag_name)
        if tag is not None:
            contact.tags.append(tag)
    session.flush()
    return contact


def log_interaction(session: Session, contact_id: int, kind: str = KIND_MEET,
                    *, occurred_on: date | None = None,
                    quality: str = QUALITY_NORMAL,
                    duration_min: int | None = None,
                    note: str | None = None) -> Interaction:
    """Quick Action: Kontakt eintragen. Alles ausser der Art ist optional."""
    if kind not in INTERACTION_KINDS:
        raise ValueError(f"Unbekannte Kontaktart: {kind!r}")
    if session.get(Contact, contact_id) is None:
        raise ValueError(f"Kontakt {contact_id} existiert nicht.")

    row = Interaction(contact_id=contact_id, kind=kind,
                      occurred_on=occurred_on or date.today(),
                      quality=quality, duration_min=duration_min, note=note)
    session.add(row)
    # Ein erfasster Kontakt beendet jedes Zurueckstellen.
    for snooze in session.scalars(select(RotationSnooze).where(RotationSnooze.contact_id == contact_id)):
        session.delete(snooze)
    session.flush()
    return row


def plan_activity(session: Session, title: str, planned_date: date,
                  contact_ids: list[int], *, kind: str = KIND_MEET,
                  start_time: str | None = None, end_time: str | None = None,
                  note: str | None = None) -> PlannedActivity:
    activity = PlannedActivity(title=str(title or "Treffen").strip(),
                               planned_date=planned_date, kind=kind,
                               start_time=start_time, end_time=end_time, note=note)
    for cid in contact_ids:
        contact = session.get(Contact, cid)
        if contact is not None:
            activity.participants.append(contact)
    session.add(activity)
    session.flush()
    return activity


def complete_activity(session: Session, activity_id: int,
                      quality: str = QUALITY_NORMAL) -> list[Interaction]:
    """Aus einem stattgefundenen Termin werden echte Interaktionen."""
    activity = session.get(PlannedActivity, activity_id)
    if activity is None:
        raise ValueError(f"Aktivitaet {activity_id} existiert nicht.")
    activity.status = "done"
    created = [log_interaction(session, c.id, activity.kind,
                               occurred_on=activity.planned_date,
                               quality=quality, note=activity.title)
               for c in activity.participants]
    return created


def set_wish(session: Session, contact_id: int, boost: int = 15,
             until: date | None = None) -> None:
    """'Die Person moechte ich bald wieder sehen.'"""
    contact = session.get(Contact, contact_id)
    if contact is None:
        raise ValueError(f"Kontakt {contact_id} existiert nicht.")
    contact.wish_boost = max(0, min(20, int(boost)))
    contact.wish_until = until


def pause_contact(session: Session, contact_id: int, until: date | None = None) -> None:
    contact = session.get(Contact, contact_id)
    if contact is None:
        raise ValueError(f"Kontakt {contact_id} existiert nicht.")
    contact.status = STATUS_PAUSED
    contact.paused_until = until
