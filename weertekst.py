import requests
import copy
from bs4 import BeautifulSoup
from textBlock import toTeletextBlock
from page import exportTTI, loadTTI
from legaliser import pageLegaliser

# Functie om windrichting in graden om te zetten naar kompasrichting
def windrichting_naar_kompas(graden):
    try:
        graden = float(graden)
        richtingen = ['N', 'NNO', 'NO', 'ONO', 'O', 'OZO', 'ZO', 'ZZO',
                      'Z', 'ZZW', 'ZW', 'WZW', 'W', 'WNW', 'NW', 'NNW']
        index = round(graden / 22.5) % 16
        return richtingen[index]
    except (ValueError, TypeError, ZeroDivisionError):
        return "Onbekend"

# JSON-feed ophalen voor weerinformatie
url = "https://data.buienradar.nl/2.0/feed/json"
response = requests.get(url)
data = response.json()

# Zoek naar "Meetstation Schiphol"
stations = data['actual']['stationmeasurements']
schiphol = next(
    (s for s in stations if s['stationname'].strip().lower() == 'meetstation schiphol'),
    None
)

# Verkrijg de weergegevens
if schiphol:
    temperature = schiphol.get('temperature')
    cloudcover = schiphol.get('cloudcoverpercentage', 0)
    humidity = schiphol.get('humidity')
    windspeed_ms = schiphol.get('windspeed')  # in m/s
    windspeed_kmh = round(windspeed_ms * 3.6, 1) if windspeed_ms is not None else None
    wind_direction = schiphol.get('winddirection')  # Kompasrichting (bijv. ZO)
    wind_direction_degrees = schiphol.get('winddirectiondegrees')  # Graden (bijv. 128°)

    # Gebruik windrichting in kompasvorm als beschikbaar, anders gebruik de graden
    if wind_direction:
        wind_direction_str = wind_direction
    elif wind_direction_degrees:
        wind_direction_str = windrichting_naar_kompas(wind_direction_degrees)
    else:
        wind_direction_str = "Onbekend"

    # Neerslagkans uit de forecast sectie
    forecast = data.get('forecast', {})
    weatherreport = forecast.get('weatherreport', {})
    rain_chance = "Niet beschikbaar"

    if weatherreport:
        summary = weatherreport.get('summary', '').lower()
        if 'regen' in summary or 'buien' in summary:
            rain_chance = "Kans op neerslag"
        else:
            rain_chance = "0%"

    # Creëer de teletext-pagina voor het weer
    weatherPageTemplate = loadTTI("weather_page.tti")
    teletextPage = {"number": 300, "subpages": [{"packets": copy.deepcopy(weatherPageTemplate["subpages"][0]["packets"])}]}
    line = 7

    # Voeg weerinformatie toe aan de teletext-pagina
    paraBlock = toTeletextBlock(
        input={"content": [{"align": "left", "content": [{"colour": "yellow", "text": f"Temperatuur: {temperature} °C"}]}]},
        line=line
    )
    line += len(paraBlock) + 1
    teletextPage["subpages"][0]["packets"] += paraBlock

    paraBlock = toTeletextBlock(
        input={"content": [{"align": "left", "content": [{"colour": "white", "text": f"Bewolking: {cloudcover}%"}]}]},
        line=line
    )
    line += len(paraBlock) + 1
    teletextPage["subpages"][0]["packets"] += paraBlock

    paraBlock = toTeletextBlock(
        input={"content": [{"align": "left", "content": [{"colour": "white", "text": f"Luchtvochtigheid: {humidity}%"}]}]},
        line=line
    )
    line += len(paraBlock) + 1
    teletextPage["subpages"][0]["packets"] += paraBlock

    if windspeed_kmh is not None:
        paraBlock = toTeletextBlock(
            input={"content": [{"align": "left", "content": [{"colour": "white", "text": f"Windsnelheid: {windspeed_kmh} km/u ({wind_direction_str})"}]}]},
            line=line
        )
        line += len(paraBlock) + 1
        teletextPage["subpages"][0]["packets"] += paraBlock
    else:
        paraBlock = toTeletextBlock(
            input={"content": [{"align": "left", "content": [{"colour": "white", "text": "Windsnelheid: Niet beschikbaar"}]}]},
            line=line
        )
        line += len(paraBlock) + 1
        teletextPage["subpages"][0]["packets"] += paraBlock

    paraBlock = toTeletextBlock(
        input={"content": [{"align": "left", "content": [{"colour": "white", "text": f"Neerslagkans: {rain_chance}"}]}]},
        line=line
    )
    line += len(paraBlock) + 1
    teletextPage["subpages"][0]["packets"] += paraBlock

    # Exporteer de teletext-pagina
    exportTTI(pageLegaliser(teletextPage))
