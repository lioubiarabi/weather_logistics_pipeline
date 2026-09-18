import os
import json
import glob
import pandas as pd

from tabulate import tabulate

bronze_dir = "../../data/bronze"
silver_dir = "../../data/silver"
cities_csv = os.path.join(bronze_dir, "moroccan_cites.csv")

os.makedirs(silver_dir, exist_ok=True)

list_of_files = glob.glob(f"{bronze_dir}/*.json")
latest_file = max(list_of_files, key=os.path.getctime)

with open(latest_file, "r", encoding="utf-8", errors="ignore") as f:
    raw_data = json.load(f)

all_weather_rows = []
for city_record in raw_data:
    city_name = city_record['city']
    daily_data = city_record.get('daily', {})

    if not daily_data:
        continue

    df_temp = pd.DataFrame(daily_data)
    df_temp['city'] = city_name
    all_weather_rows.append(df_temp)

df_weather = pd.concat(all_weather_rows, ignore_index=True)
df_weather.rename(columns={'time': 'date'}, inplace=True)

df_weather['date'] = pd.to_datetime(df_weather['date']).dt.date
df_weather['weather_code'] = df_weather['weather_code'].fillna(-1).astype(int)

float_columns = [
    'temperature_2m_max', 'temperature_2m_min',
    'precipitation_sum', 'precipitation_probability_max',
    'wind_speed_10m_max', 'wind_gusts_10m_max'
]
for col in float_columns:
    df_weather[col] = df_weather[col].astype(float)

df_weather.dropna(subset=float_columns, how='all', inplace=True)
df_weather.drop_duplicates(subset=['city', 'date'], keep='last', inplace=True)

df_cities = pd.read_csv(cities_csv)
df_cities = df_cities[['city', 'lat', 'lng', 'admin_name', 'population']]

df_silver = pd.merge(df_weather, df_cities, on='city', how='left')


execution_date = pd.Timestamp.now().strftime("%Y%m%d")
output_file = os.path.join(silver_dir, f"weather_cleaned_{execution_date}.csv")

df_silver.to_csv(output_file, index=False, encoding='utf-8')
print(f"Silver part completed: cleaning and processing data all saved in {output_file}")

