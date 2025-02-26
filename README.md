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

4. **CSV exportieren**:
   - Gehe zum Tab "CSV download".
   - Wähle einen gespeicherten Mechanismus aus der Dropdown-Liste und klicke auf "Laden".
   - Wähle, ob die CSV-Datei nur für die ausgewählte Trajektorie exportiert werden soll.
   - Klicke auf "CSV exportieren", um die Daten als CSV-Datei herunterzuladen.

5. **Mechanismus exportiern/importieren** 
   - Gehe zum Tab "Mechanik-Export/Import".
   - Wähle einen gespeicherten Mechanismus aus der Dropdown-Liste und klicke auf "JSON herunterladen", um den  Mechanismus als JSON-Datei zu exportieren.
   - Lade eine JSON-Datei hoch, um einen Mechanismus zu importieren.

6. **Mechanismusanimation (GIF) downloaden**
   - Gehe zum Tab "Animation".
   - Wähle einen gespeicherten Mechanismus aus der Dropdown-Liste und klicke auf "Laden".
   - Wähle die gewünschten Anzeigeoptionen (Längenfehler, Stablängen, Stabwinkel).
   - Klicke auf "Download als GIF", um die Animation als GIF-Datei herunterzuladen.

7. **Stückliste erstellen**
   - Gehe zum Tab "Stückliste".
   - Wähle die Gelenke, Stäbe und Antriebe aus, die in der Stückliste enthalten sein sollen.
   - Klicke auf "Stückliste als CSV herunterladen", um die Stückliste als CSV-Datei herunterzuladen.

## Projektstruktur
- [README.md]: Hauptdatei für die Streamlit-Anwendung.
- [database.py]: Funktionen zum Speichern und Laden von Mechanismen in der Datenbank.
- [mechanism.py]: Enthält die Klassen und Funktionen zur Definition und Simulation von Mechanismen.
- [animation.py]: Funktionen zur Animation der Mechanismen.
- [mechanism_db.json]: Datenbankdatei, die die gespeicherten Mechanismen enthält.
- [requirements.txt]: Liste der benötigten Python-Pakete.
- [README.md]: Diese Dokumentation.

## Abhängigkeiten

Die benötigten Pakete sind in der Datei `requirements.txt` aufgeführt. Hier ist eine Liste der wichtigsten Pakete:
- streamlit
- numpy
- pandas
- matplotlib
- tinydb
- scipy

## UML-Diagramm der Softwarestruktur

