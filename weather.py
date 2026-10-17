import requests

# --- Config: change these when you move ---
LOCATION = {"name": "West Lafayette, IN", "lat": 40.4259, "lon": -86.9081}
UNIT = "fahrenheit"  # use "celsius" for Kolkata
# For Kolkata testing: {"name": "Kolkata, IN", "lat": 22.5726, "lon": 88.3639}

# Open-Meteo describes weather as a number code; this turns it into words
WEATHER_CODES = {
    0: "Clear sky", 1: "Mostly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow",
    80: "Rain showers", 81: "Rain showers", 82: "Heavy rain showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with hail",
}


def get_weather():
    """Get today's weather for the configured location."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LOCATION["lat"],
        "longitude": LOCATION["lon"],
        "current": "temperature_2m,weather_code,wind_speed_10m",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "temperature_unit": UNIT,
        "timezone": "auto",
        "forecast_days": 1,
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()  # raises an error if the request failed
        data = response.json()
    except requests.RequestException as e:
        return {"error": f"Could not fetch weather: {e}"}

    symbol = "°F" if UNIT == "fahrenheit" else "°C"
    current = data["current"]
    daily = data["daily"]

    return {
        "location": LOCATION["name"],
        "conditions": WEATHER_CODES.get(current["weather_code"], "Unknown"),
        "temperature_now": f'{round(current["temperature_2m"])}{symbol}',
        "high": f'{round(daily["temperature_2m_max"][0])}{symbol}',
        "low": f'{round(daily["temperature_2m_min"][0])}{symbol}',
        "chance_of_rain": f'{daily["precipitation_probability_max"][0]}%',
    }


if __name__ == "__main__":
    print(get_weather())