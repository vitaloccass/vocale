@echo off
:loop
echo Serveur lancé à %date% %time%
python manage.py runserver 192.168.88.251:8000
echo Serveur arrêté, relance dans 3 secondes...
timeout /t 3
goto loop