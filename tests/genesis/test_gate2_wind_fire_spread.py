from hrm_genesis.ecology.plants import _wind_fire_spread_factor


def test_directional_fire_spread_and_calm_compatibility():
    source = (2, 2)
    east = (3, 2)
    west = (1, 2)
    north = (2, 3)
    calm = {}
    assert _wind_fire_spread_factor(calm, source, east) == 1.0
    wind = {"wind_speed_m_s": 10.0, "wind_east_m_s": 10.0, "wind_north_m_s": 0.0}
    assert _wind_fire_spread_factor(wind, source, east) > 1.0
    assert _wind_fire_spread_factor(wind, source, west) < 1.0
    assert _wind_fire_spread_factor(wind, source, north) == 1.0
    assert 0.2 <= _wind_fire_spread_factor(
        {"wind_speed_m_s": 1e6, "wind_east_m_s": 1e6, "wind_north_m_s": 0.0},
        source, west) <= 1.0
    assert _wind_fire_spread_factor(wind, source, east) == _wind_fire_spread_factor(wind, source, east)
