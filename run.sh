#!/usr/bin/env bash
# edu-recon-lab launcher for Kali Linux
# Usage:
#   ./run.sh              # localhost only (http://127.0.0.1:5000)
#   LAB_HOST=0.0.0.0 ./run.sh   # expose on your isolated lab LAN (owned VMs only)
set -e

cd "$(dirname "$0")"

# Kali ships python3; ensure venv module is available:
#   sudo apt update && sudo apt install -y python3-venv
if [ ! -d ".venv" ]; then
  echo "[*] Creating virtualenv…"
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

echo "[*] Starting edu-recon-lab…"
echo "[*] Open http://127.0.0.1:${LAB_PORT:-5000}  (dashboard at /dashboard)"
exec python app.py
