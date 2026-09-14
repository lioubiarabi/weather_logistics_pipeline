import time
import requests
import json
import pandas as pd
from datetime import datetime

df_cities = pd.read_csv("../../data/bronze/moroccan_cites.csv")

weather_data = []

for index, row in df_cities.iterrows():
    city_name = row['city']
    lat = row['lat']
    lon = row['lng']

    params = {
                "latitude": lat,
                "longitude": lon,
                "daily": [
                    "weather_code",
                    "temperature_2m_max",
                    "temperature_2m_min",
                    "precipitation_sum",
                    "precipitation_probability_max",
                    "wind_speed_10m_max",
                    "wind_gusts_10m_max"
                ],
                "timezone": "Africa/Casablanca"
            }

    try:
        print(f"\r\033[2K fetching weather of : {city_name}", end="", flush=True)
        response = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=10)
        response.raise_for_status()

        city_weather = response.json()
        city_weather['city'] = city_name


        weather_data.append(city_weather)
        time.sleep(5)

    except requests.exceptions.Timeout:
        print(f"Timeout Error: The API took too long to respond for {city_name}.")
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP Error for {city_name}: {http_err}")
    except Exception as err:
        print(f"Unexpected Error for {city_name}: {err}")

if weather_data:
    output_json_file = f"weather_for_{datetime.now().strftime('%Y%m%d')}.json"
    with open("../../data/bronze/" + output_json_file, "w") as file:
        json.dump(weather_data, file, ensure_ascii=False, indent=4)
    print(f"\nDone fetching cities weather into {output_json_file} !")
else:
    print("No data was fetch!")

