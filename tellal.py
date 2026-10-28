#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Corvus (Eski adıyla Tellal) — Geriye Dönük Uyumluluk Köprüsü
Bu dosya geriye dönük uyumluluk amacıyla tutulmaktadır.
Doğrudan corvus.py dosyasını çalıştırır.
"""
import os
import sys
import runpy

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    corvus_script = os.path.join(script_dir, "corvus.py")
    if os.path.exists(corvus_script):
        runpy.run_path(corvus_script, run_name="__main__")
    else:
        print("[HATA] corvus.py dosyası bulunamadı!")
        sys.exit(1)
