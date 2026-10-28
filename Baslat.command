#!/bin/bash
cd "$(dirname "$0")"
if [ -f "corvus.py" ]; then
    python3 corvus.py
else
    python3 tellal.py
fi
