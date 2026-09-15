import os
import json
import glob
import pandas as pd


def process_silver_layer():
    # Define paths
    # Define paths (going up from src/transformation to the project root)
    bronze_dir = "../../data/bronze"
    silver_dir = "../../data/silver"
    cities_csv = os.path.join(bronze_dir, "moroccan_cites.csv")

    # Ensure the silver directory exists
    os.makedirs(silver_dir, exist_ok=True)

    # 1. Find the latest JSON file in the bronze folder
    # This allows the script to always process the most recent extraction
    list_of_files = glob.glob(f"{bronze_dir}/*.json")
    if not list_of_files:
        print("❌ No raw JSON data found in the Bronze layer.")
        return
    latest_file = max(list_of_files, key=os.path.getctime)
    print(f"🔄 Processing file: {latest_file}")

    # 2. Load the JSON data
    with open(latest_file, "r", encoding="utf-8", errors="ignore") as f:
        raw_data = json.load(f)

    # 3. Flatten the JSON (Extract daily arrays into rows)
    all_weather_rows = []
    for city_record in raw_data:
        city_name = city_record['city']
        daily_data = city_record.get('daily', {})

        if not daily_data:
            continue

        # Convert the 'daily' dictionary of lists into a DataFrame
        df_temp = pd.DataFrame(daily_data)
        df_temp['city'] = city_name
        all_weather_rows.append(df_temp)

    # Combine all cities into a single DataFrame
    df_weather = pd.concat(all_weather_rows, ignore_index=True)

    # Rename 'time' to 'date' for clarity
    df_weather.rename(columns={'time': 'date'}, inplace=True)

    # 4. Standardize Types and Dates
    print("🧹 Cleaning data and standardizing types...")
    df_weather['date'] = pd.to_datetime(df_weather['date']).dt.date
    df_weather['weather_code'] = df_weather['weather_code'].fillna(-1).astype(int)

    float_columns = [
        'temperature_2m_max', 'temperature_2m_min',
        'precipitation_sum', 'precipitation_probability_max',
        'wind_speed_10m_max', 'wind_gusts_10m_max'
    ]
    for col in float_columns:
        df_weather[col] = df_weather[col].astype(float)

    # 5. Data Quality Checks & Duplicate Handling
    # Drop completely empty rows
    df_weather.dropna(subset=float_columns, how='all', inplace=True)

    # Ensure no duplicates exist for the same city on the same date
    initial_count = len(df_weather)
    df_weather.drop_duplicates(subset=['city', 'date'], keep='last', inplace=True)
    if initial_count != len(df_weather):
        print(f"⚠️ Removed {initial_count - len(df_weather)} duplicate records.")

    # 6. Join with the Cities dataset (Enrichment)
    print("🔗 Joining weather data with city coordinates...")
    df_cities = pd.read_csv(cities_csv)

    # We select only the columns we need from the cities dataset to avoid clutter
    df_cities = df_cities[['city', 'lat', 'lng', 'admin_name', 'population']]

    # Merge on the 'city' column
    df_silver = pd.merge(df_weather, df_cities, on='city', how='left')

    # 7. Save to the Silver layer
    execution_date = pd.Timestamp.now().strftime("%Y%m%d")
    output_file = os.path.join(silver_dir, f"weather_cleaned_{execution_date}.csv")

    df_silver.to_csv(output_file, index=False, encoding='utf-8')
    print(f"✅ Silver layer processing complete! Cleaned data saved to {output_file}")

    # Preview the data
    print("\nData Preview:")
    print(df_silver[['city', 'date', 'temperature_2m_max', 'precipitation_sum']].head())


if __name__ == "__main__":
    process_silver_layer()
