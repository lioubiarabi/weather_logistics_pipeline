select city_name, sum(risk_score) / count(*) as avg_risk_score
from weather_forecasts
where date > now()
group by city_name
order by avg_risk_score desc