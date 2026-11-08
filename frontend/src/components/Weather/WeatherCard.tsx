import type { WeatherSummary } from "../../services/locationApi";

// WMO weather interpretation codes, see https://open-meteo.com/en/docs
function describeWeather(code: number | null, isDay = true) {
  if (code === null) return { icon: "❔", label: "Unknown" };
  if (code === 0) return { icon: isDay ? "☀️" : "🌙", label: "Clear sky" };
  if (code === 1) return { icon: isDay ? "🌤️" : "🌙", label: "Mainly clear" };
  if (code === 2) return { icon: "⛅", label: "Partly cloudy" };
  if (code === 3) return { icon: "☁️", label: "Overcast" };
  if (code <= 48) return { icon: "🌫️", label: "Fog" };
  if (code === 56 || code === 57) return { icon: "🌧️", label: "Freezing drizzle" };
  if (code <= 55) return { icon: "🌦️", label: "Drizzle" };
  if (code === 66 || code === 67) return { icon: "🌧️", label: "Freezing rain" };
  if (code <= 65) return { icon: "🌧️", label: "Rain" };
  if (code <= 77) return { icon: "🌨️", label: "Snow" };
  if (code <= 82) return { icon: "🌦️", label: "Rain showers" };
  if (code <= 86) return { icon: "🌨️", label: "Snow showers" };
  return { icon: "⛈️", label: "Thunderstorm" };
}

function formatNumber(value: number | null, unit: string) {
  return value === null ? "–" : `${Math.round(value)}${unit}`;
}

function weekday(date: string, index: number) {
  if (index === 0) return "Today";
  return new Date(`${date}T12:00:00`).toLocaleDateString("en", { weekday: "short" });
}

export default function WeatherCard({ weather }: { weather: WeatherSummary }) {
  const { current, days, source } = weather;
  const { icon, label } = describeWeather(current.weather_code, current.is_day);

  return (
    <div className="weather">
      <div className="weather-now">
        <span className="weather-icon" aria-hidden="true">
          {icon}
        </span>
        <span className="weather-temperature">
          {formatNumber(current.temperature, "°C")}
        </span>
        <div className="weather-summary">
          <strong>{label}</strong>
          <span>
            Wind {formatNumber(current.wind_speed, " km/h")} · Rain{" "}
            {formatNumber(current.precipitation_probability, "%")}
          </span>
        </div>
      </div>

      <ol className="weather-days">
        {days.map((day, index) => {
          const forecast = describeWeather(day.weather_code);
          return (
            <li key={day.date}>
              <span>{weekday(day.date, index)}</span>
              <span role="img" aria-label={forecast.label} title={forecast.label}>
                {forecast.icon}
              </span>
              <strong>{formatNumber(day.temperature_max, "°")}</strong>
              <span className="weather-low">
                {formatNumber(day.temperature_min, "°")}
              </span>
            </li>
          );
        })}
      </ol>

      <p className="weather-credit">
        Weather:{" "}
        <a href={source.url} target="_blank" rel="noreferrer">
          {source.name}
        </a>
        {" · "}
        <a href={source.licenceUrl} target="_blank" rel="noreferrer">
          {source.licence}
        </a>
      </p>
    </div>
  );
}
