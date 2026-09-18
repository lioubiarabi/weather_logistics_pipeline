select date, sum(risk_score)/count(*) as avg_risk_score
from weather_forecasts
group by date
order by avg_risk_score desc
