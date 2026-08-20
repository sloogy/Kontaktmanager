"""Datenmodell des FreizeitManagers.

Kernentscheidungen gegenueber dem alten Kontaktmanager:

* Gruppen, Tags und Beziehungsgrad sind drei getrennte Konzepte und werden
  ueber echte Fremdschluessel referenziert, nicht als Freitext dupliziert.
* ``letztes_treffen`` wird durch eine vollstaendige Interaktionshistorie
  ersetzt. Nur daraus laesst sich Beziehungsfrische berechnen.
* Wichtigkeit und gewuenschter Kontaktrhythmus sind bewusst zwei Felder.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (Boolean, Column, Date, DateTime, ForeignKey, Integer,
                        String, Table, Text, UniqueConstraint)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# ── Kontaktstatus ─────────────────────────────────────────────────────────────
STATUS_ACTIVE = "active"        # normal in der Rotation
STATUS_LOW = "low"              # bewusst gerade weniger Kontakt
STATUS_NO_ROTATION = "no_rotation"  # bleibt erfasst, wird nie vorgeschlagen
STATUS_PAUSED = "paused"        # bis Datum ausgesetzt
STATUS_ARCHIVED = "archived"

ROTATING_STATUSES = {STATUS_ACTIVE, STATUS_LOW}


# ── Interaktionsarten ─────────────────────────────────────────────────────────
# Die Grundwirkung steht bewusst NICHT hier, sondern in logic.freshness -
# sie ist konfigurierbar und darf sich aendern, ohne das Schema zu beruehren.
KIND_MEET_LONG = "meet_long"
KIND_MEET = "meet"
KIND_CALL_LONG = "call_long"
KIND_CALL = "call"
KIND_CHAT = "chat"
KIND_MESSAGE = "message"
KIND_REACTION = "reaction"

INTERACTION_KINDS = (
    KIND_MEET_LONG, KIND_MEET, KIND_CALL_LONG,
    KIND_CALL, KIND_CHAT, KIND_MESSAGE, KIND_REACTION,
)

QUALITY_SHORT = "short"
QUALITY_NORMAL = "normal"
QUALITY_INTENSE = "intense"


contact_groups = Table(
    "contact_groups", Base.metadata,
    Column("contact_id", ForeignKey("contacts.id", ondelete="CASCADE"), primary_key=True),
    Column("group_id", ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True),
)

contact_tags = Table(
    "contact_tags", Base.metadata,
    Column("contact_id", ForeignKey("contacts.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)

activity_participants = Table(
    "activity_participants", Base.metadata,
    Column("activity_id", ForeignKey("planned_activities.id", ondelete="CASCADE"), primary_key=True),
    Column("contact_id", ForeignKey("contacts.id", ondelete="CASCADE"), primary_key=True),
)


class Group(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False, unique=True)
    sort_order = Column(Integer, default=0, nullable=False)
    contacts = relationship("Contact", secondary=contact_groups, back_populates="groups")


class Tag(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True)
    name = Column(String(60), nullable=False, unique=True)
    kind = Column(String(20), default="free", nullable=False)  # free | activity | context
    contacts = relationship("Contact", secondary=contact_tags, back_populates="tags")


class RelationshipLevel(Base):
    __tablename__ = "relationship_levels"
    id = Column(Integer, primary_key=True)
    name = Column(String(60), nullable=False, unique=True)
    sort_order = Column(Integer, default=0, nullable=False)
    default_interval_days = Column(Integer, nullable=True)
    default_importance = Column(Integer, nullable=True)


class Contact(Base):
    __tablename__ = "contacts"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    relationship_level_id = Column(ForeignKey("relationship_levels.id", ondelete="SET NULL"), nullable=True)

    # Wichtigkeit 1 (lose Bekanntschaft) bis 5 (engster Mensch).
    importance = Column(Integer, default=3, nullable=False)
    # Gewuenschter Kontaktrhythmus in Tagen - bewusst unabhaengig von importance.
    target_interval_days = Column(Integer, default=30, nullable=False)
    # Toleranz, bevor ueberhaupt etwas vorgeschlagen wird.
    interval_flex_days = Column(Integer, default=7, nullable=False)

    status = Column(String(20), default=STATUS_ACTIVE, nullable=False)
    paused_until = Column(Date, nullable=True)

    # Bevorzugte Kanaele - steuert, WAS vorgeschlagen wird, nicht OB.
    wants_meeting = Column(Boolean, default=True, nullable=False)
    wants_call = Column(Boolean, default=True, nullable=False)
    wants_message = Column(Boolean, default=True, nullable=False)

    prefers_weekday = Column(Boolean, default=True, nullable=False)
    prefers_weekend = Column(Boolean, default=True, nullable=False)

    # Wie viel soziale Energie ein Treffen mit dieser Person typischerweise
    # kostet: 1 = leicht, 2 = normal, 3 = anstrengend.
    energy_cost = Column(Integer, default=2, nullable=False)

    # Manueller "will ich bald sehen"-Wunsch, optional befristet.
    wish_boost = Column(Integer, default=0, nullable=False)
    wish_until = Column(Date, nullable=True)

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    level = relationship("RelationshipLevel", lazy="joined")
    groups = relationship("Group", secondary=contact_groups, back_populates="contacts")
    tags = relationship("Tag", secondary=contact_tags, back_populates="contacts")
    interactions = relationship("Interaction", back_populates="contact",
                                cascade="all, delete-orphan",
                                order_by="Interaction.occurred_on.desc()")
    snoozes = relationship("RotationSnooze", back_populates="contact",
                           cascade="all, delete-orphan")
    activities = relationship("PlannedActivity", secondary=activity_participants,
                              back_populates="participants")


class Interaction(Base):
    __tablename__ = "interactions"
    id = Column(Integer, primary_key=True)
    contact_id = Column(ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True)
    occurred_on = Column(Date, default=date.today, nullable=False, index=True)
    kind = Column(String(20), default=KIND_MEET, nullable=False)
    quality = Column(String(20), default=QUALITY_NORMAL, nullable=False)
    duration_min = Column(Integer, nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    contact = relationship("Contact", back_populates="interactions")


class PlannedActivity(Base):
    __tablename__ = "planned_activities"
    id = Column(Integer, primary_key=True)
    title = Column(String(160), nullable=False)
    planned_date = Column(Date, nullable=False, index=True)
    start_time = Column(String(5), nullable=True)   # "18:30"
    end_time = Column(String(5), nullable=True)
    kind = Column(String(20), default=KIND_MEET, nullable=False)
    status = Column(String(20), default="planned", nullable=False)  # planned|done|cancelled
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    participants = relationship("Contact", secondary=activity_participants,
                                back_populates="activities")


class RotationSnooze(Base):
    """Bewusstes Zurueckstellen - erzeugt keinen sichtbaren Schuldenberg."""
    __tablename__ = "rotation_snoozes"
    id = Column(Integer, primary_key=True)
    contact_id = Column(ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True)
    snoozed_until = Column(Date, nullable=False)
    reason = Column(String(30), default="later", nullable=False)  # later|week|manual
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    contact = relationship("Contact", back_populates="snoozes")


class RotationState(Base):
    """Rotationsgedaechtnis: verhindert, dass immer dieselben gewinnen."""
    __tablename__ = "rotation_state"
    contact_id = Column(ForeignKey("contacts.id", ondelete="CASCADE"), primary_key=True)
    last_suggested_on = Column(Date, nullable=True)
    suggest_count = Column(Integer, default=0, nullable=False)
    last_score = Column(Integer, default=0, nullable=False)


class AppSetting(Base):
    __tablename__ = "settings"
    key = Column(String(80), primary_key=True)
    value = Column(Text, nullable=True)


class SchemaMigration(Base):
    __tablename__ = "schema_migrations"
    version = Column(Integer, primary_key=True)
    applied_at = Column(DateTime, default=datetime.now, nullable=False)
    __table_args__ = (UniqueConstraint("version"),)
