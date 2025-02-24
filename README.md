# SWD_Abschlussprojekt

## Installation

1. **Python installieren**: Stelle sicher, dass Python 3.x auf deinem System installiert ist. Du kannst Python von [python.org](https://www.python.org/downloads/) herunterladen.

2. **Virtuelle Umgebung erstellen**: Es wird empfohlen, eine virtuelle Umgebung zu verwenden, um Abhängigkeiten zu isolieren. Erstelle eine virtuelle Umgebung mit dem folgenden Befehl:

   ```bash
   python -m venv venv
   ```

3. **Virtuelle Umgebung aktivieren**:

   - Auf Windows:
     ```bash
     .\venv\Scripts\activate
     ```
   - Auf macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

4. **Abhängigkeiten installieren**: Installiere die benötigten Pakete mit `pip`:
   ```bash
   pip install -r requirements.txt
   ```

## Ausführung

1. **Streamlit-Anwendung starten**: Um die interaktive Mechanismus-Simulation zu starten, führe den folgenden Befehl aus:

   ```bash
   streamlit run Streamlit_UI.py
   ```

2. **Mechanismus erstellen**:

   - Öffne die Anwendung im Browser.
   - Gehe zum Tab "Mechanismus erstellen".
   - Wähle den Rotationsradius und die Anzahl der Gelenkpunkte.
   - Bearbeite die Gelenkpunkte und Stäbe nach Bedarf.
   - Gib einen Namen für den Mechanismus ein und klicke auf "Speichern".

3. **Mechanismus laden und simulieren**:
   - Gehe zum Tab "Mechaniken laden".
   - Wähle einen gespeicherten Mechanismus aus der Dropdown-Liste und klicke auf "Laden".
   - Klicke auf "Mechanik ausführen", um die Simulation zu starten.

## Projektstruktur

- [Streamlit_UI.py](http://_vscodecontentref_/0): Hauptdatei für die Streamlit-Anwendung.
- [main.py](http://_vscodecontentref_/1): Enthält die Klassen und Funktionen zur Definition und Simulation von Mechanismen.
- `mechanism_db.json`: Datenbankdatei, die die gespeicherten Mechanismen enthält.
- `requirements.txt`: Liste der benötigten Python-Pakete.
- [README.md](http://_vscodecontentref_/2): Diese Dokumentation.

## Abhängigkeiten

Die benötigten Pakete sind in der Datei `requirements.txt` aufgeführt. Hier ist eine Liste der wichtigsten Pakete:

## UML-Diagramm der Softwarestruktur

@startuml
class Mechanism {
  - gelenk: list
  - staebe: list
  - radius: float
  - fixed_gelenk_index: int
  - rotating_gelenk_index: int
  - theta_values: np.ndarray
  - verbindungs_matrix: np.ndarray
  - start_laengen: np.ndarray
  - trajectories: dict
  - selected_trajectory: int
  + create_verbindungs_matrix()
  + berechnet_laengen()
  + fehlerfunktion()
  + update_positions()
}

class Gelenk {
  - x: float
  - y: float
  - is_static: bool
  - is_rotating: bool
  - is_tracked: bool
  + position()
}

class Stab {
  - gelenk1: Gelenk
  - gelenk2: Gelenk
}

class TinyDB {
  - db: TinyDB
  - mechanisms_table: Table
  + save_mechanism_to_db()
  + load_mechanism_from_db()
}

Mechanism --> Gelenk
Mechanism --> Stab
TinyDB --> Mechanism
@enduml