# Alter Kontaktmanager (stillgelegt)

Dieser Stand ist der Ausgangspunkt des FreizeitManagers und wird von keinem
neuen Code mehr benutzt. Er bleibt als Referenz erhalten.

Bekannte Probleme, die im Neubau behoben sind:

* `db.py` legte `termine.db` im **Arbeitsverzeichnis** an – je nach Startort
  landete die Datenbank in `Downloads/`, `Desktop/` oder sonstwo.
* Gruppen und Beziehungsgrade wurden als Freitext in `kontakte` kopiert.
  Umbenennen oder Löschen erzeugte verwaiste Werte.
* Die Registerkarte „TAGs“ verwaltete in Wahrheit Beziehungsgrade.
* Die Kapazitätseinstellungen wurden gespeichert, aber nie ausgewertet.
* Die gesamte Programmlogik lag in einer 582-Zeilen-`main.py`.

Start (nur zu Ansichtszwecken): `python3 legacy/main.py`
