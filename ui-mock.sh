#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

GREEN='\033[0;32m'
NC='\033[0m'

cd "$ROOT/dashboard"
echo -e "${GREEN}Starting dashboard with mock data (no backend required)...${NC}"
echo -e "${GREEN}Open http://localhost:5173${NC}"
VITE_MOCK=true npx vite --host
