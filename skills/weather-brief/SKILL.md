---
name: weather-brief
description: Today's weather for a city, with commute and safety flags.
version: 1.0.0
author: CSCI 599 A3 student project
license: MIT
metadata:
  hermes:
    tags: [weather, briefing, forecast, open-meteo, productivity]
    category: productivity
---

# Weather Brief

Gives a short, practical weather briefing for one city for today: a single
summary line (conditions, high/low, chance of rain) followed by flags that
change what the user should do (take an umbrella for the commute, dress for
cold, expect wind).

## When to Use

- The user asks about today's weather, whether to take an umbrella or a
  jacket, or what the commute will be like.
- A morning briefing or daily summary needs a weather line.
- Use the user's home city from memory when they don't name one. Ask if you
  don't know it.

## Procedure

1. **If a weather tool is available, use it.** If your tool list has a tool
   whose name ends in `get_weather_brief` (for example
   `mcp__weather__get_weather_brief`), call it with `city` and skip step 2.
   It runs this same code as a read-only service.
2. **Otherwise run the bundled script** (needs the terminal tool and
   `python3`; standard library only, no install step):

       python3 ${HERMES_SKILL_DIR}/scripts/weather_brief.py "CITY"

   - Add a region or country to disambiguate: `"Portland, OR"`,
     `"Paris, France"`.
   - Units are automatic (°F for the US, °C elsewhere). Override with
     `--units imperial` or `--units metric`.
   - `--json` returns structured output: `line`, `flags`, `place`, `units`.
3. Reply with the summary line, then the flags as short bullets. Keep it to
   two to four lines. If there are no flags, say so in a few words.

## Pitfalls

- Exit code 2 means the city was not found. Ask the user to spell it
  differently or add the country. Never guess a forecast.
- Exit code 3 means Open-Meteo could not be reached. Say the forecast is
  unavailable right now. Don't make one up.
- City names are ambiguous ("Springfield"). If the matched place in the
  output isn't the one the user meant, retry with a region or country.
- The script reports only today's local date in the city's own timezone.
  Don't use it for multi-day forecasts.

## Verification

The output's first line names the matched place and date, for example
`Los Angeles, California (2026-11-11): clear, high 87°F / low 58°F, 0% max chance of rain.`
Check that the place and date are the ones the user meant.
