SELECT distinct on (city_name)
    city_name,
    date,
    risk_score
FROM weather_forecasts
ORDER BY city_name, risk_score DESC