#!/bin/bash
cd "$(dirname "$0")"
if [ -f "corvus.py" ]; then
    exec python3 corvus.py
else
    exec python3 tellal.py
fi
