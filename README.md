# hermes-weather-brief

A [Hermes Agent](https://github.com/NousResearch/hermes-agent) skill tap with one skill, **weather-brief**.

**weather-brief** gives today's weather for one city as a single summary line,
covering conditions, high and low, and the chance of rain. Below that it adds
flags that change what you should do, such as taking an umbrella for the
commute, dressing for the cold, or expecting wind. The skill calls a bundled
Python script that uses only the standard library, so there is nothing to
install and no API key. It needs Hermes's terminal tool and `python3`.

## Install (as a tap)

```bash
hermes skills tap add SuyashRoy/hermes-weather-brief
hermes skills install SuyashRoy/hermes-weather-brief/weather-brief
hermes chat -q "What's the weather in Los Angeles?"
```

Tested with Hermes Agent v0.21.5 (tag `v2026.9.24`).

## Layout

```
skills/weather-brief/SKILL.md                 # instructions Hermes loads
skills/weather-brief/scripts/weather_brief.py # python3 weather_brief.py "CITY" [--json] [--units imperial|metric]
```

## Data and attribution

Weather and geocoding data come from [Open-Meteo](https://open-meteo.com/),
which is free and needs no API key. The data is licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Each run makes two
HTTPS requests: geocoding, which turns the city into coordinates and a
timezone, then the forecast for today.

## License

MIT; see [LICENSE](LICENSE).
