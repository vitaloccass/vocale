import schedule
import time
from datetime import datetime
import subprocess

def ma_tache():
    print("Tâche lancée à", datetime.now())
    subprocess.run(["python", "app.py"])

with open('heure.txt', 'r', encoding='utf-8') as fichier:
    heure = fichier.readline().strip()

schedule.every().day.at(heure).do(ma_tache)

while True:
    schedule.run_pending()
    time.sleep(1)
