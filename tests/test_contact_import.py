"""Import einer Personenliste aus CSV/Excel."""
from datetime import date

import pytest

from freizeitmanager.logic.contact_import import (
    ERROR_EMPTY,
    ERROR_UNSUPPORTED,
    PROBLEM_BAD_DATE,
    YEAR_UNKNOWN,
    ImportError_,
    RowAction,
    apply_preview,
    build_preview,
    detect_columns,
    parse_birthday,
    read_table,
)


def test_columns_are_detected_regardless_of_order_and_wording():
    found = detect_columns(["Geburtsdatum", "Nachname", "Vorname", "Bemerkung"])
    assert found["birthday"] == 0
    assert found["last_name"] == 1
    assert found["first_name"] == 2
    assert found["notes"] == 3
    # Englische Exporte und Umlaute/Zusaetze in der Ueberschrift.
    english = detect_columns(["Display Name", "Date of Birth", "E-Mail"])
    assert english["name"] == 0 and english["birthday"] == 1 and english["email"] == 2
    assert detect_columns(["Geburtstag (TT.MM.)"])["birthday"] == 0


def test_german_dates_are_read_day_first():
    # 03.04. ist der 3. April - nicht der 4. Maerz.
    assert parse_birthday("03.04.1985")[0] == date(1985, 4, 3)
    assert parse_birthday("1985-04-03")[0] == date(1985, 4, 3)
    assert parse_birthday(date(1985, 4, 3))[0] == date(1985, 4, 3)


def test_birthday_without_year_keeps_day_and_month():
    parsed, has_year, problem = parse_birthday("03.04.")
    assert parsed == date(YEAR_UNKNOWN, 4, 3)
    assert has_year is False and problem == ""


def test_two_digit_years_never_land_in_the_future():
    parsed, _, _ = parse_birthday("03.04.65")
    assert parsed == date(1965, 4, 3)


def test_unreadable_date_is_reported_not_guessed():
    parsed, _, problem = parse_birthday("irgendwann")
    assert parsed is None and problem == PROBLEM_BAD_DATE
    assert parse_birthday("")[0] is None
    assert parse_birthday(None)[0] is None


def test_preview_separates_new_conflicting_and_unusable_rows():
    headers = ["Name", "Geburtstag"]
    rows = [["Anna Weber", "01.02.1990"], ["Bekannter", "05.06."], ["", "01.01.1980"]]
    preview = build_preview(headers, rows, existing={"bekannter": 7})

    assert [r.name for r in preview.new_rows] == ["Anna Weber"]
    assert [r.name for r in preview.conflicts] == ["Bekannter"]
    assert len(preview.unusable) == 1
    assert preview.with_birthday == 2
    # Ein bestehender Name wird nicht ungefragt angefasst.
    assert preview.conflicts[0].action is RowAction.SKIP


def test_name_is_assembled_from_first_and_last_name():
    preview = build_preview(["Vorname", "Nachname"], [["Anna", "Weber"]])
    assert preview.rows[0].name == "Anna Weber"


def test_csv_is_read_with_semicolon_and_bom(tmp_path):
    path = tmp_path / "k.csv"
    path.write_bytes("Name;Geburtstag\nAnna Weber;01.02.1990\n".encode("utf-8-sig"))
    headers, rows = read_table(path)
    assert headers[0] == "Name"
    assert rows[0][1] == "01.02.1990"


def test_unsupported_and_empty_files_are_rejected(tmp_path):
    bad = tmp_path / "k.pdf"
    bad.write_text("x", encoding="utf-8")
    with pytest.raises(ImportError_, match=ERROR_UNSUPPORTED):
        read_table(bad)
    empty = tmp_path / "leer.csv"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(ImportError_, match=ERROR_EMPTY):
        read_table(empty)


def test_apply_writes_only_released_rows(session):
    preview = build_preview(["Name", "Geburtstag"],
                            [["Anna Weber", "01.02.1990"], ["Bert Klein", "03.04."]])
    preview.rows[1].action = RowAction.SKIP

    result = apply_preview(session, preview)

    assert result.created == 1 and result.skipped == 1
    assert result.failed == []
    from sqlalchemy import select

    from freizeitmanager.database.models import Contact
    stored = session.scalars(select(Contact)).all()
    assert [c.name for c in stored] == ["Anna Weber"]
    assert stored[0].birthday == date(1990, 2, 1)
    assert stored[0].birthday_has_year is True


def test_fill_never_overwrites_an_existing_value(session):
    from freizeitmanager.logic.contact_service import create_contact
    contact = create_contact(session, "Anna Weber", birthday=date(1990, 2, 1), notes="alt")
    session.flush()

    preview = build_preview(["Name", "Geburtstag", "Notiz"],
                            [["Anna Weber", "09.09.1999", "neu"]],
                            existing={"anna weber": contact.id})
    preview.rows[0].action = RowAction.FILL
    apply_preview(session, preview)

    assert contact.birthday == date(1990, 2, 1)
    assert contact.notes == "alt"
