from __future__ import annotations

from copy import deepcopy
import math

from hrm_coordination.seeds import SeedBank

from .climate import lightning_activity, persistent_weather_anomaly, precipitation_amount, temperature_c, wind_vector_m_s
from .energy import solar_input
from .grid import build_grid
from .terrain import latitude_factor


def build_world_state(
    *,
    width: int,
    height: int,
    ticks_per_year: int,
    master_seed: str,
    seed_bank: SeedBank,
    wind_enabled: bool = False,
) -> dict:
    return {
        "width": width,
        "height": height,
        "ticks_per_year": ticks_per_year,
        "master_seed": master_seed,
        "epoch_applied": -1,
        **({"wind_model": "persistent-vector-v1"} if wind_enabled else {}),
        "cells": build_grid(width, height, seed_bank),
    }


def evolve_world(state: dict, epoch: int) -> dict:
    world = deepcopy(state)
    width = int(world["width"])
    height = int(world["height"])
    ticks_per_year = int(world["ticks_per_year"])
    seed = str(world["master_seed"])

    for cell in world["cells"]:
        y = int(cell["y"])
        lat = latitude_factor(y, height)
        cell["solar"] = solar_input(epoch, ticks_per_year, lat)
        x = int(cell["x"])
        cell["temperature"] = temperature_c(
            seed=seed,
            epoch=epoch,
            ticks_per_year=ticks_per_year,
            x=x,
            y=y,
            height=height,
            elevation=float(cell["elevation"]),
        )
        cell["weather_temperature_anomaly"] = persistent_weather_anomaly(
            seed=seed,
            epoch=epoch,
            ticks_per_year=ticks_per_year,
            x=x,
            y=y,
            channel="temperature",
        )
        cell["weather_moisture_anomaly"] = persistent_weather_anomaly(
            seed=seed,
            epoch=epoch,
            ticks_per_year=ticks_per_year,
            x=x,
            y=y,
            channel="moisture",
        )
        cell["lightning"] = lightning_activity(
            seed=seed,
            epoch=epoch,
            ticks_per_year=ticks_per_year,
            x=x,
            y=y,
        )
        if world.get("wind_model") == "persistent-vector-v1":
            east, north = wind_vector_m_s(seed=seed, epoch=epoch, ticks_per_year=ticks_per_year, x=x, y=y)
            cell["wind_east_m_s"] = east
            cell["wind_north_m_s"] = north
            cell["wind_speed_m_s"] = round(math.hypot(east, north), 10)
            cell["wind_from_deg"] = round(math.degrees(math.atan2(-north, -east)) % 360.0, 10) if east or north else 0.0
        cell["precipitation"] = precipitation_amount(
            seed=seed,
            epoch=epoch,
            ticks_per_year=ticks_per_year,
            x=x,
            y=y,
            height=height,
            elevation=float(cell["elevation"]),
        )

    world["epoch_applied"] = epoch
    for cell in world["cells"]:
        for field in (
            "temperature",
            "solar",
            "precipitation",
            "weather_temperature_anomaly",
            "weather_moisture_anomaly",
            "lightning",
        ):
            cell[field] = round(float(cell[field]), 10)
    return world
