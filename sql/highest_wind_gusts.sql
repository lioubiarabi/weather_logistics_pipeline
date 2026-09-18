select city_name, sum(wind_gusts) / count(*) as avg_wind_gusts
from weather_forecasts
where date > now()
group by city_name
order by avg_wind_gusts desc