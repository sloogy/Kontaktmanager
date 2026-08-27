# FreizeitManager 0.2.3 – Manual

FreizeitManager helps you keep up with the people who matter, without
turning that into a list of chores. It remembers who is important to you and
how often you would like to be in touch, and suggests at most a handful of
people each day.

This manual is generated from the help inside the application. The same texts
are always available there with **F1**.

## Contents

- [Getting started](#getting-started)
- [Importing a list](#importing-a-list)
- [The cockpit](#the-cockpit)
- [Contacts and rhythm](#contacts-and-rhythm)
- [Recording contact](#recording-contact)
- [Freshness and rotation](#freshness-and-rotation)
- [Birthdays](#birthdays)
- [Planning dates](#planning-dates)
- [Simple mode and expert mode](#simple-mode-and-expert-mode)
- [Settings, language and backup](#settings-language-and-backup)

## Getting started

The FreizeitManager answers a single question: **Who would I like to be in touch with again right now?** It is not an address book and not a to-do list. Nothing here creates debt.

The quickest start: create contacts or import an existing list. For each person you set how important they are to you and how often you would like to be in touch. Everything else follows from what you actually record.

After that the cockpit is enough. It shows at most three suggestions – experience shows that more creates pressure instead of clarity.

## Importing a list

Under **Contacts → Import** you take over an existing list of people from a CSV or Excel file (.xlsx). The columns need no fixed order: the import recognises headers such as name, first name, last name, birthday, group, notes, email and phone by itself, in German as well as in English.

Before anything is written you see a **preview**. There you decide row by row what should happen. Names that already exist are set to “skip” – for them “create” is not even offered. If you choose “fill empty fields”, only what is still missing on the existing contact is entered. Existing entries are never overwritten.

Birthdays are taken over even when the file holds no year: day and month are kept, the age is then simply not shown. Two-digit years never land in the future – “65” becomes 1965.

Rows without a name are skipped and counted in the summary. An unreadable cell never brings down the whole import.

## The cockpit

**Today** is the start screen. It does not answer “how does everything stand?” but “what would be due now?”.

The four tiles show how many contacts would fit right now, would be due this week, are already arranged and are resting. Below them your next steps appear as cards with quick actions: record, plan, postpone or mark as a wish.

**Other suggestions** exchanges the cards without showing the same people again straight away.

At the top you choose your energy state for today: low energy, normal or up for people. It shifts the suggestions towards short or more extensive contact and applies to this day only.

If nothing is pressing, the cockpit says so – instead of showing an empty table.

## Contacts and rhythm

Every contact has two separate settings that are often confused:

**Importance** (A to E) says how close the person is to you. **Contact every … days** says how often you would like to be in touch. The two are related but do not determine each other: someone close whom you see twice a year is still someone close.

The **tolerance** is the leeway around that rhythm. Only beyond it is a contact treated as overdue.

The **relationship level** is a template: choose one and new contacts inherit its importance and rhythm.

The **status** governs the rotation: active and “less contact right now” take part, “not in the rotation” stays on record but is never suggested, “paused” suspends until a date, “archived” disappears from everyday use.

Under **How is contact welcome?** and **When does it usually fit?** you record what suits the person – suggestions follow that.

## Recording contact

A contact is recorded with one click: on the card in the cockpit or via **Record** in the contact list. You are only asked back if you want to add more.

The **kind** ranges from a long meeting to a brief reaction. It determines how long the contact resonates: a long evening carries further than a thumbs-up under a picture.

The **quality** (short, normal, intense) strengthens or dampens that effect, the **duration** is optional.

Every recorded contact ends a postponement. There is deliberately no “last meeting” field: the history grows from what you record, and only from it can freshness be derived.

## Freshness and rotation

From the recorded contacts a **freshness** follows for every person: all good, soon again, a good moment now, quiet for a long time. This grading – not a score – drives the suggestions.

Suggestions are held back when something speaks against them: contact just happened (cooldown after contact), a date is already planned, the contact is paused or postponed, or your social capacity for this week is reached. The cockpit names these reasons in plain words.

The **social capacity** in the settings limits how many social days per week are suggested. It is a protection against overload, not a target.

The **rotation** area shows the full evaluation of all contacts including the reasoning. Everyday use does not need it – it makes clear why something is suggested. You find it in expert mode.

## Birthdays

Contacts can have a birthday. The cockpit shows the birthdays coming up in the next 30 days; today's is highlighted.

If the **year is unknown**, tick the corresponding box in the contact form. Day and month are then kept, but no age is shown and no year is invented.

A birthday on 29 February is shown on 28 February in ordinary years so that it stays in February.

Archived contacts do not appear here.

## Planning dates

Via **Plan** on a suggestion card you arrange a date and take the suggested person along right away. Several participants are possible.

Planned dates of the next two weeks appear in the cockpit under **Planned**. As long as a date stands, the person is not suggested again.

Once the date has taken place it becomes a real contact entry for all participants – you do not have to record it twice.

## Simple mode and expert mode

The FreizeitManager starts in **simple mode**: cockpit, contacts and settings. That is enough for everyday use.

**Expert mode** additionally shows the rotation and reveals the numbers behind the gradings in cards and lists. You switch at the bottom of the sidebar or with **Ctrl+E**.

Further shortcuts: **Ctrl+N** creates a contact, **F1** opens this help.

## Settings, language and backup

Under **Settings** you set how many suggestions the cockpit shows, how long things rest after a contact and how many social days per week suit you.

**Language** applies immediately, without a restart – German, English and French.

Under **Appearance** you choose a design profile and the font size. If the FreizeitManager runs inside the LifePlanner, it can adopt the profile set centrally there.

**Create backup** stores a copy of the database. The data folder is named on the same page.

If the FreizeitManager is connected to the LifePlanner, on request it passes on counts and next steps only – never notes.

The next steps then also appear on LifePlanner's overview page, next to the notices from the other programs – at most three, as in the cockpit. Only the finished line is transferred: who is due and what would suit. A friendship that has gone quiet is deliberately never marked as urgent there; no pile of debts should build up in LifePlanner either. Anyone you contacted today disappears from the list on its own.

---

Generated from the application's help with `tools/build_handbook.py`. Edits belong in `freizeitmanager/i18n/en.json` under `help.topics`.
