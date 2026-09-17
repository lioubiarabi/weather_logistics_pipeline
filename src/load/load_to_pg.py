import os
import glob
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.dialects.postgresql import insert

# 1. ORM Setup & Schema Definition
Base = declarative_base()


class City(Base):
    __tablename__ = 'cities'

    name = Column(String, primary_key=True)
    lat = Column(Float)
    lng = Column(Float)
    admin_name = Column(String)
    population = Column(Float)


class WeatherForecast(Base):
    __tablename__ = 'weather_forecasts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    city_name = Column(String, ForeignKey('cities.name'))
    date = Column(Date)

    # Raw Weather Variables
    temp_max = Column(Float)
    temp_min = Column(Float)
    precip_sum = Column(Float)
    wind_gusts = Column(Float)

    # Engineered Features (Gold Layer)
    risk_score = Column(Integer)
    risk_level = Column(String)
    temp_category = Column(String)
    precip_category = Column(String)
    wind_category = Column(String)

    # Audit tracking
    updated_at = Column(DateTime, default=datetime.utcnow)

    # Prevent duplicate forecasts for the same city on the same day
    __table_args__ = (UniqueConstraint('city_name', 'date', name='uq_city_date'),)


def load_data_to_postgres():
    gold_dir = "../../data/gold"

    # FIX: Using pg8000 to completely bypass the Windows French character bug
    DATABASE_URI = "postgresql://postgres:admin@localhost:5433/postgres"

    engine = create_engine(DATABASE_URI)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    list_of_files = glob.glob(f"{gold_dir}/*.csv")
    if not list_of_files:
        print("❌ No Gold data found to load.")
        return
    latest_file = max(list_of_files, key=os.path.getctime)

    print(f"🔄 Loading data from: {latest_file}")
    df = pd.read_csv(latest_file)

    # Upsert Cities
    print("🏙️ Upserting City records...")
    df_cities = df[['city', 'lat', 'lng', 'admin_name', 'population']].drop_duplicates()

    cities_data = []
    for _, row in df_cities.iterrows():
        cities_data.append({
            'name': row['city'],
            'lat': row['lat'],
            'lng': row['lng'],
            'admin_name': row['admin_name'],
            'population': row['population'] if pd.notnull(row['population']) else None
        })

    stmt_cities = insert(City).values(cities_data)
    stmt_cities = stmt_cities.on_conflict_do_nothing(index_elements=['name'])
    session.execute(stmt_cities)
    session.commit()

    # Upsert Weather Forecasts
    print("🌤️ Upserting Weather Forecasts and Risk Scores...")
    forecasts_data = []
    for _, row in df.iterrows():
        forecasts_data.append({
            'city_name': row['city'],
            'date': row['date'],
            'temp_max': row['temperature_2m_max'],
            'temp_min': row['temperature_2m_min'],
            'precip_sum': row['precipitation_sum'],
            'wind_gusts': row['wind_gusts_10m_max'],
            'risk_score': row['risk_score'],
            'risk_level': row['risk_level'],
            'temp_category': row['temp_category'],
            'precip_category': row['precip_category'],
            'wind_category': row['wind_category'],
            'updated_at': datetime.utcnow()
        })

    stmt_forecasts = insert(WeatherForecast).values(forecasts_data)
    update_dict = {
        'temp_max': stmt_forecasts.excluded.temp_max,
        'temp_min': stmt_forecasts.excluded.temp_min,
        'precip_sum': stmt_forecasts.excluded.precip_sum,
        'wind_gusts': stmt_forecasts.excluded.wind_gusts,
        'risk_score': stmt_forecasts.excluded.risk_score,
        'risk_level': stmt_forecasts.excluded.risk_level,
        'temp_category': stmt_forecasts.excluded.temp_category,
        'precip_category': stmt_forecasts.excluded.precip_category,
        'wind_category': stmt_forecasts.excluded.wind_category,
        'updated_at': stmt_forecasts.excluded.updated_at
    }

    stmt_forecasts = stmt_forecasts.on_conflict_do_update(
        index_elements=['city_name', 'date'],
        set_=update_dict
    )

    session.execute(stmt_forecasts)
    session.commit()

    print("✅ Successfully loaded all data into PostgreSQL!")
    session.close()


if __name__ == "__main__":
    load_data_to_postgres()
