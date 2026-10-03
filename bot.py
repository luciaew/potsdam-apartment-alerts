Pasted text(2).txt
Document
no funcuona lo de la locacion
de que linea a que linea
Pasted text(3).txt
Document
agregale que diga desde cuando esta disponible

proximo paso que sea integrar todas las paginas que te mande ddesd el principio
Pasted text(4).txt
Document
dame el nuevo de bot.py


ya lo hice ckmo sigo
Pasted text(5).txt
Document
dame el nuevo de bot.py , ahora esta asi 


asi?
Pasted text(6).txt
Document
dame el nuev 


Pasted text(7).txt
Document
asi esta ahora dame el nuevo 


Pasted text(8).txt
Document
asi esta bot py dame el nuevo 


Pasted text(9).txt
Document
wohnung_jetzt.py


pegue ese archivo pero no actualiza

Sí, ahora la captura aclara una cosa importante.

En tu bot.yml aparece:

on: workflow_dispatch

Eso significa que GitHub solo ejecuta el bot cuando vos apretás “Run workflow”. No está programado cada 5 minutos.

Además, el verde “Success” no significa que haya encontrado y enviado departamentos; solo significa que python bot.py terminó sin error.

Para que se actualice automáticamente

Tu bot.yml debería tener:

name: Potsdam Apartment Bot

on:
  workflow_dispatch:
  schedule:
    - cron: "*/5 * * * *"

permissions:
  contents: write

jobs:
  run-bot:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run apartment bot
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: python bot.py

      - name: Save seen listings
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add seen.json
          git diff --cached --quiet || git commit -m "Update seen apartment listings"
          git push

Pero hay otra cosa: esto arregla la actualización automática, no el hecho de que ahora Wohnung-jetzt no esté mandando anuncios. En los logs que me pasaste, los 126 anuncios estaban siendo descartados por la disponibilidad o por seen.

Así que tenemos dos problemas separados:

🔄 Actualización automática: falta schedule en bot.yml.
🏠 Wohnung-jetzt: el filtro todavía está descartando los anuncios antes de Telegram.

No quiero hacerte cambiar cinco archivos otra vez. Primero arreglemos el bot.yml para que vuelva a funcionar cada 5 minutos.

dame los nuevos codigos y donde ponerlos

Sí. Vamos a dejarlo simple: reemplazá 3 archivos en tu GitHub. No toques kleinanzeigen.py, requirements.txt ni seen.json.

1. bot.py

En GitHub:

Code → bot.py → Edit → reemplazá todo → Commit changes

Descargar bot.py

Este usa una nueva clave para Wohnung-jetzt, así que los anuncios antiguos pueden ser evaluados nuevamente con el filtro actualizado.

2. wohnung_jetzt.py

En GitHub:

Code → wohnung_jetzt.py → Edit → reemplazá todo → Commit changes

Descargar wohnung_jetzt.py

Este es el que controla:

Potsdam solamente
1–2 Zimmer
WG fuera
Tauschangebot fuera
Warmmiete > €900 fuera
Kaltmiete alta no cuenta como Warmmiete
Warmmiete desconocida → se mantiene
disponibilidad desde noviembre 2026
intenta detectar ab November, verfügbar ab, Einzug ab, 01.11.2026, etc.
reduce los 429 de Wohnung-jetzt.
3. bot.yml

Este es el importante para que se ejecute automáticamente.

En GitHub:

Code → .github → workflows → bot.yml → Edit → reemplazá todo

Descargar bot.yml

Ahora contiene:

on:
  workflow_dispatch:
  schedule:
    - cron: "*/5 * * * *"

Es decir: cada 5 minutos, además de poder ejecutarlo manualmente.

Después

Una vez reemplazados los 3:

Andá a Actions
Potsdam Apartment Bot
Run workflow
Esperá a que termine.
Si está verde, dejalo funcionando.

Los avisos automáticos pueden aparecer con cierto retraso porque GitHub Actions no garantiza que el cron de 5 minutos se ejecute exactamente al segundo.

No toques ningún otro archivo. 

bot.py
Code
wohnung_jetzt.py
Code
bot.yml
Code

Sí, ya encontré el error exacto. No es Telegram ni Wohnung-jetzt. Es un error de sintaxis en bot.py.

GitHub está ejecutando esto en la línea 8:

sacar esto 🏠 NUEVO DEPARTAMENTO EN POTSDAM

Eso quedó pegado dentro del código Python, por eso aparece:

SyntaxError: invalid character '🏠'
Solución

No borres ni edites una línea a mano. Reemplazá completamente tu bot.py por este archivo limpio:

DESCARGAR bot.py CORREGIDO

El comienzo correcto tiene que ser:

import json
import os
import requests

from kleinanzeigen import get_search_listings as get_kleinanzeigen_listings
from kleinanzeigen import filter_listing as filter_kleinanzeigen

from immoscout import get_search_listings as get_immoscout_listings

from wohnung_jetzt import (
    get_search_listings as get_wohnung_jetzt_listings,
    filter_listing as filter_wohnung_jetzt
)

No tiene que aparecer ningún texto como sacar esto, 🏠 NUEVO... ni instrucciones fuera de las funciones.

En GitHub
Code
bot.py
✏️ Edit
Ctrl/Cmd + A
Pegá el contenido del archivo descargado.
Commit changes
Andá a Actions
Run workflow

Después debería volver a arrancar el bot normalmente.

No cambies wohnung_jetzt.py ni bot.yml ahora. El error de esta ejecución está exclusivamente en bot.py. 

bot.py
Code

bot.py
999
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
32
33
34
35
36
37
38
39
40
41
42
43
44
45
46
47
48
49
50
51
52
53
54
55
56
57
58
59
60
61
62
63
64
65
66
67
68
69
70
71
72
73
74
75
76
77
78
import json
import os
import requests


from kleinanzeigen import get_search_listings as get_kleinanzeigen_listings
from kleinanzeigen import filter_listing as filter_kleinanzeigen


from immoscout import get_search_listings as get_immoscout_listings


from wohnung_jetzt import (
    get_search_listings as get_wohnung_jetzt_listings,
    filter_listing as filter_wohnung_jetzt
)




SEEN_FILE = "seen.json"


TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]




def load_seen():
    try:
        with open(
            SEEN_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            return set(json.load(file))


    except Exception:
        return set()




def save_seen(seen):
    with open(
        SEEN_FILE,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            sorted(seen),
            file,
            ensure_ascii=False,
            indent=2
        )




def send_telegram(message):


    url = (
        f"https://api.telegram.org/bot"
        f"{TELEGRAM_BOT_TOKEN}/sendMessage"
    )


    response = requests.post(
        url,
        data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "disable_web_page_preview": False,
        },
        timeout=30,
    )


    print(
        "Telegram status:",
        response.status_code
    )


    if response.status_code != 200:
        print(response.text)
        return False


    return True




def format_distance(value):
