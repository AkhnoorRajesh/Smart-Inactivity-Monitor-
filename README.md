Smart-Inactivity-Monitor-
========================
Smart Inactivity Monitor is a lightweight app that tracks user inactivity and performs actions like screen lock, alerts, or logout. Designed for workplaces and labs, it features customizable idle timeouts, activity logging, and a user-friendly interface to boost security and productivity.


A free, open-source tool to monitor user inactivity and alert/lock the system.

Features:
- Inactivity detection
- Customizable alerts and sounds
- Dark mode and user profiles
- Works offline, no installation required

How to Use:
1. Double-click the .exe to start.
2. Use the dashboard to set timers, alerts, and profiles.
3. The app will warn and lock the system after inactivity.

How to Build (for developers):
1. Install Python 3.8+ and pip.
2. Install dependencies: pip install -r requirements.txt
3. Use PyInstaller to build: 
   pyinstaller --onefile --windowed --icon=src/resources/icon.ico --add-data "src/resources;resources" --add-data "src/settings.json;." src/SmartInactivityMonitor.py

Download the exe file:

🔗 [Download EXE](https://drive.google.com/file/d/1iD7D7GGwohgFvgL14bxjSObJ7O3iZpAE/view?usp=drive_link)

