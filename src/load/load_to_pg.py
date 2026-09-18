import os
import glob
import pandas as pd
import sqlalchemy as db
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime


gold_dir = "../../data/gold"

engine = db.create_engine("postgresql://postgres:admin@localhost:5433/postgres")
metadata = db.MetaData()

cities = db.Table('cities', metadata, autoload_with=engine)
forecasts = db.Table('weather_forecasts', metadata, autoload_with=engine)

list_of_files = glob.glob(os.path.join(gold_dir, "*.csv"))
latest_file = max(list_of_files, key=os.path.getctime)
print(f"Loading data from: {latest_file}")

df = pd.read_csv(latest_file)
df = df.where(pd.notnull(df), None)

df_cities = df[['city', 'lat', 'lng', 'admin_name', 'population']].drop_duplicates()
df_cities = df_cities.rename(columns={'city': 'name'})
cities_data = df_cities.to_dict('records')

df_forecasts = df[
    ['city', 'date', 'temperature_2m_max', 'temperature_2m_min', 'precipitation_sum', 'wind_gusts_10m_max',
     'risk_score', 'risk_level', 'temp_category', 'precip_category', 'wind_category']].copy()
df_forecasts = df_forecasts.rename(columns={
    'city': 'city_name',
    'temperature_2m_max': 'temp_max',
    'temperature_2m_min': 'temp_min',
    'precipitation_sum': 'precip_sum',
    'wind_gusts_10m_max': 'wind_gusts'
})
df_forecasts['updated_at'] = datetime.now()
forecasts_data = df_forecasts.to_dict('records')


with engine.connect() as conn:
    print("Upserting City records...")
    stmt_cities = insert(cities).values(cities_data)
    stmt_cities = stmt_cities.on_conflict_do_nothing(index_elements=['name'])
    conn.execute(stmt_cities)

    print("Upserting Weather Forecasts...")
    stmt_forecasts = insert(forecasts).values(forecasts_data)

    update_dict = {c.name: c for c in stmt_forecasts.excluded if c.name not in ('id', 'city_name', 'date')}

    stmt_forecasts = stmt_forecasts.on_conflict_do_update(
        index_elements=['city_name', 'date'],
        set_=update_dict
    )
    conn.execute(stmt_forecasts)

    print("Data updated successfully!")

