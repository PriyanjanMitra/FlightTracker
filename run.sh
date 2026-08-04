#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
DATA_DIR="$ROOT/data"
DB="$DATA_DIR/flight_tracker.db"
PID_FILE="$ROOT/.run_pids"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

cleanup() {
    echo -e "\n${YELLOW}Shutting down...${NC}"
    if [ -f "$PID_FILE" ]; then
        while IFS= read -r pid; do
            kill "$pid" 2>/dev/null || true
        done < "$PID_FILE"
        rm -f "$PID_FILE"
    fi
    wait 2>/dev/null
    echo -e "${GREEN}Done.${NC}"
}
trap cleanup EXIT INT TERM

# --- Prerequisites ---
command -v python3 >/dev/null 2>&1 || { echo -e "${RED}python3 is required${NC}"; exit 1; }
command -v node >/dev/null 2>&1 || { echo -e "${RED}node is required for the dashboard${NC}"; exit 1; }

# --- Python venv ---
VENV="$ROOT/.venv"
if [ ! -x "$VENV/bin/python" ]; then
    echo -e "${GREEN}[1/5] Creating Python virtualenv...${NC}"
    python3 -m venv "$VENV"
fi

# --- Install Python deps ---
echo -e "${GREEN}[1/5] Installing Python dependencies...${NC}"
"$VENV/bin/pip" install -q -e "$ROOT" 2>/dev/null || "$VENV/bin/pip" install -e "$ROOT"

# --- Init DB ---
echo -e "${GREEN}[2/5] Initializing database...${NC}"
mkdir -p "$DATA_DIR"
"$VENV/bin/python" "$ROOT/main.py" init-db

# --- Load reference data (only once) ---
if [ ! -f "$DATA_DIR/openflights/.loaded" ]; then
    echo -e "${GREEN}[3/5] Loading reference data (airports, airlines, routes)...${NC}"
    "$VENV/bin/python" "$ROOT/main.py" load-ref-data
    mkdir -p "$DATA_DIR/openflights"
    touch "$DATA_DIR/openflights/.loaded"
else
    echo -e "${GREEN}[3/5] Reference data already loaded, skipping.${NC}"
fi

# --- Install frontend deps ---
echo -e "${GREEN}[4/5] Installing frontend dependencies...${NC}"
cd "$ROOT/dashboard"
npm install --silent 2>/dev/null || npm install
cd "$ROOT"

# --- Launch ---
echo -e "${GREEN}[5/5] Starting services...${NC}"

# Pipeline (poll OpenSky)
"$VENV/bin/python" "$ROOT/main.py" run-pipeline &
echo $! >> "$PID_FILE"

# FastAPI backend
"$VENV/bin/python" "$ROOT/main.py" serve-backend &
echo $! >> "$PID_FILE"

# Vite dev server
cd "$ROOT/dashboard"
npx vite --host &
echo $! >> "$PID_FILE"
cd "$ROOT"

sleep 2
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  FlightTracker is running!${NC}"
echo -e "${GREEN}  Dashboard : http://localhost:5173${NC}"
echo -e "${GREEN}  API       : http://localhost:8000${NC}"
echo -e "${GREEN}  Docs      : http://localhost:8000/docs${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Press Ctrl+C to stop all services."

wait
