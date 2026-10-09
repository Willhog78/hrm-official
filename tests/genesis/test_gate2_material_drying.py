from copy import deepcopy
from hrm_genesis.human.interactions import weather_objects


def _case(wind, rain):
    obj = {"id": "f1", "x": 0, "y": 0, "holder": None,
           "material": "fiber", "elements_kg": {"C": 1.0},
           "integrity": 1.0, "wetness": 0.8}
    people = {"objects": [obj]}
    producer = {(0, 0): {"fire_intensity": 0.0, "detritus_elements_kg": {"C": 0.0}}}
    world = {(0, 0): {"wind_speed_m_s": wind, "solar": 1.0, "precipitation": rain}}
    weather_objects(people, producer, world, 1)
    return people["objects"][0]["wetness"]


def test_wind_drives_drying_and_rain_rewets():
    calm = _case(0, 0)
    windy = _case(12, 0)
    wet = _case(12, 3)
    assert 0 < windy < calm < 0.8
    assert wet == 1.0
    assert windy == _case(12, 0)


def test_legacy_weather_does_not_add_moisture_state():
    obj = {"id": "f1", "x": 0, "y": 0, "holder": None,
           "material": "fiber", "elements_kg": {"C": 1.0},
           "integrity": 1.0}
    people = {"objects": [deepcopy(obj)]}
    producer = {(0, 0): {"fire_intensity": 0.0, "detritus_elements_kg": {"C": 0.0}}}
    weather_objects(people, producer, {(0, 0): {"solar": 1.0, "precipitation": 0.0}}, 1)
    assert "wetness" not in people["objects"][0]
