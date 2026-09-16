import os
import glob
import pandas as pd
import numpy as np



def calculate_risk_score(row):
    score = 0

    precip = row['precipitation_sum']
    if precip > 15:
        score += 40
    elif precip > 5:
        score += 20
    elif precip > 0:
        score += 10

    gusts = row['wind_gusts_10m_max']
    if gusts > 60:
        score += 30
    elif gusts > 40:
        score += 15

    t_max = row['temperature_2m_max']
    t_min = row['temperature_2m_min']

    if t_max >= 40 or t_min <= 0:
        score += 30
    elif t_max >= 35 or t_min <= 5:
        score += 15

    return min(100, score)


silver_dir = "../../data/silver"
gold_dir = "../../data/gold"

os.makedirs(gold_dir, exist_ok=True)

list_of_files = glob.glob(f"{silver_dir}/*.csv")
latest_file = max(list_of_files, key=os.path.getctime)

df = pd.read_csv(latest_file)

conditions_temp = [
    (df['temperature_2m_max'] < 10),
    (df['temperature_2m_max'] >= 10) & (df['temperature_2m_max'] < 25),
    (df['temperature_2m_max'] >= 25) & (df['temperature_2m_max'] < 35),
    (df['temperature_2m_max'] >= 35)
]
df['temp_category'] = np.select(conditions_temp, ['Cold', 'Moderate', 'Hot', 'Extreme Heat'], default='Unknown')


conditions_precip = [
    (df['precipitation_sum'] == 0),
    (df['precipitation_sum'] > 0) & (df['precipitation_sum'] <= 5),
    (df['precipitation_sum'] > 5) & (df['precipitation_sum'] <= 15),
    (df['precipitation_sum'] > 15)
]
df['precip_category'] = np.select(conditions_precip, ['Dry', 'Light Rain', 'Moderate Rain', 'Heavy Rain'], default='Unknown')

conditions_wind = [
    (df['wind_gusts_10m_max'] < 40),
    (df['wind_gusts_10m_max'] >= 40) & (df['wind_gusts_10m_max'] < 60),
    (df['wind_gusts_10m_max'] >= 60)
]
df['wind_category'] = np.select(conditions_wind, ['Calm', 'Windy', 'Stormy'], default='Unknown')

print("Calculating the Weather Risk Score..")

df['risk_score'] = df.apply(calculate_risk_score, axis=1)

conditions_risk_level = [
    (df['risk_score'] < 45),
    (df['risk_score'] >= 45) & (df['risk_score'] < 65),
    (df['risk_score'] >= 65)
]
df['risk_level'] = np.select(conditions_risk_level, ['Low', 'Medium', 'High'], default='Unknown')


execution_date = pd.Timestamp.now().strftime("%Y%m%d")
output_file = os.path.join(gold_dir, f"weather_gold_{execution_date}.csv")

df.to_csv(output_file, index=False, encoding='utf-8')
print(f"Gold layer processing complete: data saved in : {output_file}")

