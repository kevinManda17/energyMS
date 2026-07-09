# Lance le backend EMS accessible sur le reseau local (partage iPhone).
# 0.0.0.0 = ecoute sur TOUTES les interfaces : joignable quelle que soit
# l'IP de la machine (172.20.10.2 ou .14). A lancer depuis ems-backend/.
#
#   powershell -ExecutionPolicy Bypass -File .\run-server.ps1
#
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
& "$here\venv312\Scripts\python.exe" "$here\manage.py" runserver 0.0.0.0:8000
