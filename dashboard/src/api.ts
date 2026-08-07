import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
});

export interface State {
  icao24: string;
  callsign: string;
  origin_country: string;
  latitude: number;
  longitude: number;
  baro_altitude: number | null;
  velocity: number | null;
  heading: number | null;
  vertical_rate: number | null;
  on_ground: boolean;
  last_contact: number;
  category_label: string;
}

export interface TrailPoint {
  lat: number;
  lon: number;
  ts: number;
}

export interface AircraftInfo {
  icao24: string;
  type: string | null;
  icao_type: string | null;
  manufacturer: string | null;
  registration: string | null;
  owner: string | null;
}

export interface AirlineInfo {
  name: string | null;
  icao: string | null;
  iata: string | null;
}

export interface FlightInfo {
  aircraft: AircraftInfo | null;
  airline: AirlineInfo | null;
}

// Set MOCK = true to use synthetic data (no backend needed)
const MOCK = import.meta.env.VITE_MOCK === "true" || false;

const AIRLINES = ["AAL", "DAL", "UAL", "SWA", "JBU", "FDX", "UPS", "SKW", "ENY", "ASA", "FFT", "JIA"];
const COUNTRIES = ["United States", "Canada", "Mexico", "United Kingdom", "Germany", "Japan"];

function randomBetween(min: number, max: number) {
  return min + Math.random() * (max - min);
}

function pick<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

function generateMockStates(): State[] {
  const count = 60 + Math.floor(Math.random() * 30);
  const now = Math.floor(Date.now() / 1000);
  const states: State[] = [];
  for (let i = 0; i < count; i++) {
    const lat = randomBetween(24, 50);
    const lng = randomBetween(-130, -65);
    const alt = randomBetween(0, 12500);
    const spd = randomBetween(0, 280);
    const hdg = randomBetween(0, 360);
    const vr = randomBetween(-15, 15);
    const airline = pick(AIRLINES);
    const num = 1000 + Math.floor(Math.random() * 9000);
    states.push({
      icao24: `a${i.toString(16).padStart(5, "0")}`,
      callsign: `${airline}${num}`,
      origin_country: pick(COUNTRIES),
      latitude: Math.round(lat * 10000) / 10000,
      longitude: Math.round(lng * 10000) / 10000,
      baro_altitude: Math.round(alt),
      velocity: Math.round(spd * 10) / 10,
      heading: Math.round(hdg * 10) / 10,
      vertical_rate: Math.round(vr * 100) / 100,
      on_ground: alt < 100,
      last_contact: now - Math.floor(Math.random() * 60),
      category_label: pick(["Light", "Commercial", "Cargo", "Business Jet", "Unknown"]),
    });
  }
  return states;
}

function generateMockTrails(icao24: string): TrailPoint[] {
  const points: TrailPoint[] = [];
  const now = Date.now() / 1000;
  const baseLat = randomBetween(24, 50);
  const baseLng = randomBetween(-130, -65);
  for (let i = 14; i >= 0; i--) {
    points.push({
      lat: baseLat + randomBetween(-0.5, 0.5),
      lon: baseLng + randomBetween(-0.5, 0.5),
      ts: now - i * 60,
    });
  }
  return points;
}

export async function fetchStates(): Promise<State[]> {
  if (MOCK) {
    await new Promise((r) => setTimeout(r, 300));
    return generateMockStates();
  }
  const { data } = await api.get<State[]>("/api/states", {
    params: { limit: 100000 },
  });
  return data;
}

export async function fetchTrails(minutes = 15): Promise<Record<string, TrailPoint[]>> {
  if (MOCK) {
    await new Promise((r) => setTimeout(r, 200));
    const result: Record<string, TrailPoint[]> = {};
    for (let i = 0; i < 5; i++) {
      result[`mock_${i}`] = generateMockTrails(`mock_${i}`);
    }
    return result;
  }
  const { data } = await api.get<Record<string, TrailPoint[]>>("/api/trails", {
    params: { minutes },
  });
  return data;
}

export async function fetchFlightInfo(params: {
  icao24: string;
  callsign: string;
  latitude?: number;
  longitude?: number;
  heading?: number;
  vertical_rate?: number;
}): Promise<FlightInfo> {
  if (MOCK) {
    await new Promise((r) => setTimeout(r, 150));
    return {
      aircraft: {
        icao24: params.icao24,
        type: "737-800",
        icao_type: "B738",
        manufacturer: "Boeing",
        registration: "N12345",
        owner: "Mock Operator",
      },
      airline: { name: "Mock Airlines", icao: "ABC", iata: "AB" },
    };
  }
  const { data } = await api.get<FlightInfo>("/api/flight-info", { params });
  return data;
}
