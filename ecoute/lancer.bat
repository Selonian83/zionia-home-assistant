@echo off
rem Lance ZIONIA Ecoute. Un raccourci vers ce fichier dans le dossier
rem shell:startup le demarre avec Windows.
cd /d "%~dp0"
".venv\Scripts\python.exe" zionia_ecoute.py
pause
