from dataclasses import dataclass

from pydantic import BaseModel

CATEGORY_LABELS: dict[int, str] = {
    0: "No category information",
    1: "Light",
    2: "Small",
    3: "Large",
    4: "High Vortex Large",
    5: "Heavy",
    6: "High Performance",
    7: "Rotorcraft",
    8: "Glider",
    9: "Lighter-than-air",
    10: "Parachutist",
    11: "Ultralight",
    12: "Reserved",
    13: "UAV",
    14: "Space",
    15: "Emergency Vehicle",
    16: "Service Vehicle",
    17: "Point Obstacle",
    18: "Cluster Obstacle",
    19: "Line Obstacle",
}


@dataclass
class FlightStateDTO:
    icao24: str
    callsign: str | None
    origin_country: str | None
    longitude: float | None
    latitude: float | None
    baro_altitude: float | None
    velocity: float | None
    heading: float | None
    on_ground: bool | None
    last_contact: int
    vertical_rate: float | None = None
    category: int | None = None


class FlightStateResponse(BaseModel):
    icao24: str
    callsign: str
    origin_country: str
    latitude: float
    longitude: float
    baro_altitude: float | None = None
    velocity: float | None = None
    heading: float | None = None
    vertical_rate: float | None = None
    on_ground: bool = False
    last_contact: int
    category_label: str


class AirlineInfo(BaseModel):
    name: str | None = None
    icao: str | None = None
    iata: str | None = None


class AircraftInfo(BaseModel):
    icao24: str
    type: str | None = None
    icao_type: str | None = None
    manufacturer: str | None = None
    registration: str | None = None
    owner: str | None = None


class FlightInfoResponse(BaseModel):
    aircraft: AircraftInfo | None = None
    airline: AirlineInfo | None = None
