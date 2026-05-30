#!/bin/bash

echo "[*] Updating packages..."
pkg update -y && pkg upgrade -y

echo "[*] Installing Python..."
pkg install python -y

echo "[*] Installing requirements..."
pip install -r requirements.txt

echo "[✓] Setup complete! Run: python bluebird_sms.py"
