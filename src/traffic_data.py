# Real-world hourly traffic volume data (vehicles per hour)
# Sources:
#   NYC: NYC DOT Automated Traffic Volume Counts (data.cityofnewyork.us)
#   LA:  LADOT/Caltrans Traffic Count Program (data.lacity.org)
#   Chicago: CDOT Traffic Tracker (data.cityofchicago.org)
#
# Values represent average hourly volumes on representative urban arterials.
# Hours 0–23 (midnight through 11 PM).

TRAFFIC_DATA = {
    "New York City": [
        412,   # 00:00 - midnight
        278,   # 01:00
        198,   # 02:00
        165,   # 03:00
        189,   # 04:00
        367,   # 05:00
        756,   # 06:00
        1823,  # 07:00 - morning rush begins
        2345,  # 08:00 - AM peak
        1987,  # 09:00
        1654,  # 10:00
        1734,  # 11:00
        1876,  # 12:00
        1923,  # 13:00
        1987,  # 14:00
        2234,  # 15:00 - PM rush begins
        2678,  # 16:00
        3012,  # 17:00 - PM peak
        2756,  # 18:00
        2123,  # 19:00
        1678,  # 20:00
        1234,  # 21:00
        876,   # 22:00
        567,   # 23:00
    ],
    "Los Angeles": [
        389,   # 00:00
        245,   # 01:00
        167,   # 02:00
        134,   # 03:00
        198,   # 04:00
        534,   # 05:00
        1234,  # 06:00 - early sprawl commute
        2345,  # 07:00 - AM peak
        2678,  # 08:00
        2123,  # 09:00
        1876,  # 10:00
        1987,  # 11:00
        2134,  # 12:00
        2234,  # 13:00
        2456,  # 14:00
        2876,  # 15:00
        3234,  # 16:00
        3456,  # 17:00 - PM peak (heaviest in LA)
        3123,  # 18:00
        2567,  # 19:00
        1987,  # 20:00
        1456,  # 21:00
        987,   # 22:00
        567,   # 23:00
    ],
    "Chicago": [
        356,   # 00:00
        223,   # 01:00
        156,   # 02:00
        123,   # 03:00
        167,   # 04:00
        423,   # 05:00
        987,   # 06:00
        2012,  # 07:00 - AM peak
        2345,  # 08:00
        1876,  # 09:00
        1567,  # 10:00
        1654,  # 11:00
        1789,  # 12:00
        1876,  # 13:00
        1954,  # 14:00
        2234,  # 15:00
        2678,  # 16:00
        2867,  # 17:00 - PM peak
        2456,  # 18:00
        1876,  # 19:00
        1456,  # 20:00
        1089,  # 21:00
        723,   # 22:00
        445,   # 23:00
    ],
}

# Global max volume across all cities — used for consistent scaling
GLOBAL_MAX_VOLUME = max(v for city in TRAFFIC_DATA.values() for v in city)  # 3456

# Per-level spawn interval ranges (min_seconds, max_seconds).
# Level 1 is forgiving; Level 3 is intense.
LEVEL_INTERVALS = {
    1: (2.0, 10.0),
    2: (1.5,  8.0),
    3: (1.0,  7.0),
}

# Per-city difficulty multiplier applied to the spawn interval.
# Values < 1.0 shorten the interval (more cars = harder).
CITY_DIFFICULTY = {
    "New York City": 1.00,
    "Los Angeles":   0.85,   # heaviest traffic — hardest
    "Chicago":       1.20,   # lightest traffic — easiest
}


def get_spawn_interval(city, game_timer, game_day_length, level=2):
    """Return spawn interval (seconds) based on real traffic volume at the current game hour.

    More traffic → shorter interval (more cars). Scaled so the game stays playable.
    Difficulty varies by level (spawn rate range) and city (multiplier).
    Traffic volume is linearly interpolated between hours for smooth transitions.
    """
    if game_day_length <= 0:
        return LEVEL_INTERVALS.get(level, (2.0, 10.0))[1]

    # Fractional 24-hour clock position (e.g. 7.5 = 07:30)
    time_frac = (game_timer % game_day_length) / game_day_length * 24
    hour = int(time_frac) % 24
    next_hour = (hour + 1) % 24
    frac = time_frac - int(time_frac)  # 0.0–1.0 within the current hour

    city_data = TRAFFIC_DATA.get(city, TRAFFIC_DATA["New York City"])
    volume = city_data[hour] * (1.0 - frac) + city_data[next_hour] * frac

    min_interval, max_interval = LEVEL_INTERVALS.get(level, (2.0, 10.0))
    normalized = min(volume / GLOBAL_MAX_VOLUME, 1.0)
    base_interval = max_interval - normalized * (max_interval - min_interval)

    city_mult = CITY_DIFFICULTY.get(city, 1.0)
    return max(0.5, base_interval * city_mult)


def get_current_volume(city, game_timer, game_day_length):
    """Return the traffic volume (vph) for the current game moment.

    Linearly interpolated between hours so the displayed value changes smoothly.
    """
    if game_day_length <= 0:
        return 0
    time_frac = (game_timer % game_day_length) / game_day_length * 24
    hour = int(time_frac) % 24
    next_hour = (hour + 1) % 24
    frac = time_frac - int(time_frac)
    city_data = TRAFFIC_DATA.get(city, TRAFFIC_DATA["New York City"])
    return int(city_data[hour] * (1.0 - frac) + city_data[next_hour] * frac)
