select city_name, sum(temp_min) / count(*) as avg_temp
from weather_forecasts
where date > now()
group by city_name
order by avg_temp desc