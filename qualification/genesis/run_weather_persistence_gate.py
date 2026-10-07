from __future__ import annotations

from hrm_genesis.world.climate import persistent_weather_anomaly


def lag_one_correlation(values: list[float]) -> float:
    mean = sum(values) / len(values)
    numerator = sum(
        (values[i] - mean) * (values[i + 1] - mean)
        for i in range(len(values) - 1)
    )
    denominator = sum((value - mean) ** 2 for value in values)
    return numerator / denominator if denominator else 0.0


def longest_extreme_streak(values: list[float], threshold: float) -> int:
    longest = 0
    current = 0
    sign = 0
    for value in values:
        current_sign = 1 if value > threshold else (-1 if value < -threshold else 0)
        if current_sign and current_sign == sign:
            current += 1
        elif current_sign:
            sign = current_sign
            current = 1
        else:
            sign = 0
            current = 0
        longest = max(longest, current)
    return longest


def main() -> int:
    args = {
        "seed": "weather-persistence",
        "ticks_per_year": 365,
        "x": 8,
        "y": 8,
        "channel": "temperature",
    }
    values = [
        persistent_weather_anomaly(epoch=epoch, **args)
        for epoch in range(365)
    ]
    replay = [
        persistent_weather_anomaly(epoch=epoch, **args)
        for epoch in range(365)
    ]
    correlation = lag_one_correlation(values)
    streak = longest_extreme_streak(values, 0.30)

    checks = {
        "weather_is_deterministic": values == replay,
        "neighboring_days_are_correlated": correlation >= 0.75,
        "multi_day_extreme_anomaly_occurs": streak >= 4,
        "weather_varies_both_directions": min(values) < -0.30 and max(values) > 0.30,
    }

    for name, passed in checks.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")
    print(
        "WEATHER_PERSISTENCE_RESULTS:",
        {
            "lag_one_correlation": round(correlation, 6),
            "longest_extreme_streak_days": streak,
            "min_anomaly": round(min(values), 6),
            "max_anomaly": round(max(values), 6),
        },
    )

    if not all(checks.values()):
        print("WEATHER_PERSISTENCE_FAIL")
        return 1

    print("WEATHER_PERSISTENCE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
