#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Takvim ("Yayın Takvimi") Otomasyon Senkronizasyon Modülü
Tellal YouTube Duyuru Otomasyonu

Kullanıcının Google Takvim'deki "Yayın Takvimi" takvimiyle (macOS Calendar CalDAV / Google sync köprüsü üzerinden)
iki yönlü ve anlık senkronizasyon sağlar.
- Yayın eklendiğinde -> "Yayın Takvimi"ne eklenir.
- Yayın hazır (✅) veya iptal (❌) olduğunda -> Takvimde başlık ve durumu güncellenir.
- Yayın takvimden kaldırıldığında -> "Yayın Takvimi"nden anında silinir.
"""

import os
import sys
import re
import json
import time
import hashlib
import requests
import subprocess
from datetime import datetime, timedelta, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TAKVIM_DOSYASI = os.path.join(SCRIPT_DIR, "takvim.txt")
FIREBASE_DB_URL = "https://tellal-otomasyon-default-rtdb.europe-west1.firebasedatabase.app/tellal_db"
CALENDAR_NAME = "Yayın Takvimi"
GOOGLE_CALENDAR_ID = "c1765f9d421b1821978ac5fabbcd06b0df0b80f212403476b4d39ea7057138b6@group.calendar.google.com"

AY_MAP = {
    "ocak": 1, "subat": 2, "şubat": 2, "mart": 3, "nisan": 4, "mayis": 5, "mayıs": 5,
    "haziran": 6, "temmuz": 7, "agustos": 8, "ağustos": 8, "eylul": 9, "eylül": 9,
    "ekim": 10, "kasim": 11, "kasım": 11, "aralik": 12, "aralık": 12
}

GUN_MAP = {
    "pazartesi": 0, "sali": 1, "salı": 1, "carsamba": 2, "çarşamba": 2,
    "persembe": 3, "perşembe": 3, "cuma": 4, "cumartesi": 5, "pazar": 6
}


def parse_broadcast_line(satir, index=0):
    """Metin satırını ayrıştırarak sözlük nesnesi döndürür."""
    temiz_satir = satir.strip()
    is_done = "✅" in temiz_satir
    is_canceled = "❌" in temiz_satir

    bilgi = ""
    if " | Bilgi: " in temiz_satir:
        parts = temiz_satir.split(" | Bilgi: ")
        temiz_satir = parts[0].strip()
        bilgi = parts[1].strip()

    if "-)" in temiz_satir:
        temiz_satir = temiz_satir.split("-)", 1)[1].strip()

    temiz_satir = temiz_satir.replace("✅", "").replace("❌", "").strip()

    yayin_adi = temiz_satir
    gun = "Belirtilmedi"
    saat = "20:00"

    if " - " in temiz_satir:
        segmentler = temiz_satir.split(" - ")
        if len(segmentler) >= 3:
            saat = segmentler[-1].strip()
            gun = segmentler[-2].strip()
            yayin_adi = " - ".join(segmentler[:-2]).strip()
        elif len(segmentler) == 2:
            gun = segmentler[1].strip()
            yayin_adi = segmentler[0].strip()

    kanal = "Uykusuz Tosba"
    lower_adi = yayin_adi.lower()
    if any(k in lower_adi for k in ["memleket", "albert", "mocas", "film"]):
        kanal = "Radio Mocas"

    # Benzersiz sabit ID (başlık, gün ve saate göre)
    raw_key = f"{kanal}::{yayin_adi}::{gun}::{saat}".lower()
    sync_id = hashlib.md5(raw_key.encode("utf-8")).hexdigest()[:12]

    return {
        "sync_id": sync_id,
        "yayin_adi": yayin_adi,
        "kanal": kanal,
        "gun": gun,
        "saat": saat,
        "bilgi": bilgi,
        "is_done": is_done,
        "is_canceled": is_canceled
    }


def parse_broadcast_datetime(gun_str, saat_str):
    """Gün ve saat dizgilerinden kesin datetime nesnesi türetir."""
    now = datetime.now()
    saat, dakika = 20, 0
    if ":" in saat_str:
        p = saat_str.split(":")
        try:
            saat, dakika = int(p[0]), int(p[1])
        except Exception:
            pass

    gun_clean = gun_str.lower().strip()

    # 1. Sayı ve Ay Kontrolü (Örn: "30 Ekim", "30 Ekim (Cuma)")
    num_match = re.search(r"\b([1-9]|[12]\d|3[01])\b", gun_clean)
    if num_match:
        day_num = int(num_match.group(1))
        found_month = now.month
        for m_name, m_val in AY_MAP.items():
            if m_name in gun_clean:
                found_month = m_val
                break
        year = now.year
        try:
            dt = datetime(year, found_month, day_num, saat, dakika)
            if dt < now - timedelta(days=20):
                dt = datetime(year + 1, found_month, day_num, saat, dakika)
            return dt
        except Exception:
            pass

    # 2. Bugün / Yarın
    if "bugün" in gun_clean:
        return datetime(now.year, now.month, now.day, saat, dakika)
    if "yarın" in gun_clean:
        tom = now + timedelta(days=1)
        return datetime(tom.year, tom.month, tom.day, saat, dakika)

    # 3. Gün Adı Kontrolü (Örn: "Çarşamba", "Her Cuma")
    for g_name, g_dow in GUN_MAP.items():
        if g_name in gun_clean:
            cur_dow = now.weekday()
            diff = (g_dow - cur_dow) % 7
            if diff == 0:
                if now.hour > saat or (now.hour == saat and now.minute >= dakika):
                    diff = 7
            target_date = now + timedelta(days=diff)
            return datetime(target_date.year, target_date.month, target_date.day, saat, dakika)

    return datetime(now.year, now.month, now.day, saat, dakika)


def run_applescript(script):
    """AppleScript kodunu çalıştırır ve çıktısını döndürür."""
    res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    return res.returncode == 0, res.stdout.strip(), res.stderr.strip()


def check_calendar_exists():
    """macOS Calendar uygulamasında 'Yayın Takvimi' olup olmadığını doğrular."""
    sc = f'''
    tell application "Calendar"
        set calList to (every calendar whose name is "{CALENDAR_NAME}")
        return count of calList
    end tell
    '''
    ok, out, _ = run_applescript(sc)
    return ok and out.isdigit() and int(out) > 0


def format_applescript_date(dt):
    """macOS AppleScript tarih formatına uygun biçimlendirme yapar (GG.AA.YYYY SS:DD:00)."""
    return dt.strftime("%d.%m.%Y %H:%M:00")


def google_takvim_senkronize_et(satirlar=None):
    """
    Verilen yayın satırlarını veya takvim.txt / Firebase içeriğini
    'Yayın Takvimi' Google Takvimi ile tam olarak eşitler.
    """
    if not check_calendar_exists():
        print(f"[UYARI] '{CALENDAR_NAME}' takvimi macOS Takvim uygulamasında bulunamadı.")
        return False, "Takvim bulunamadı"

    if satirlar is None:
        if os.path.exists(TAKVIM_DOSYASI):
            with open(TAKVIM_DOSYASI, "r", encoding="utf-8") as f:
                satirlar = [s.strip() for s in f if s.strip()]
        else:
            satirlar = []

    # Gemini AI bot satırlarını filtrele
    satirlar = [s for s in satirlar if s and not ("Gemini AI" in s or "[Gemini AI]" in s)]

    hedef_yayinlar = [parse_broadcast_line(s, idx) for idx, s in enumerate(satirlar)]
    hedef_id_set = {y["sync_id"] for y in hedef_yayinlar}

    # 1. Mevcut Tellal etkinliklerini tara ve hedef listede olmayanları sil
    sc_get_existing = f'''
    tell application "Calendar"
        set targetCal to first calendar whose name is "{CALENDAR_NAME}"
        set resList to {{}}
        tell targetCal
            set tellalEvts to (every event whose description contains "[Tellal-ID:")
            repeat with evt in tellalEvts
                set d to description of evt
                set end of resList to (uid of evt & ":::" & d)
            end repeat
        end tell
        return resList
    end tell
    '''
    ok, out, err = run_applescript(sc_get_existing)
    
    silinen_sayisi = 0
    mevcut_id_to_uid = {}

    if ok and out:
        # AppleScript liste çıktısını ayrıştır
        parts = [p.strip() for p in out.split(", ") if p.strip()]
        for p in parts:
            if ":::" in p:
                uid, desc = p.split(":::", 1)
                m = re.search(r"\[Tellal-ID:\s*([a-f0-9]+)\]", desc)
                if m:
                    evt_sync_id = m.group(1)
                    if evt_sync_id not in hedef_id_set:
                        # Bu yayın artık listede yok, takvimden sil
                        sc_del = f'''
                        tell application "Calendar"
                            set targetCal to first calendar whose name is "{CALENDAR_NAME}"
                            tell targetCal
                                delete (first event whose uid is "{uid}")
                            end tell
                        end tell
                        '''
                        run_applescript(sc_del)
                        silinen_sayisi += 1
                    else:
                        mevcut_id_to_uid[evt_sync_id] = uid

    # 2. Her hedef yayını oluştur veya güncelle
    eklenen_sayisi = 0
    guncellenen_sayisi = 0

    for item in hedef_yayinlar:
        start_dt = parse_broadcast_datetime(item["gun"], item["saat"])
        end_dt = start_dt + timedelta(minutes=90)

        # Başlık biçimi
        if item["is_canceled"]:
            durum_metni = "İptal Edildi ❌"
            summary = f"❌ [İPTAL] {item['yayin_adi']} ({item['kanal']})"
        elif item["is_done"]:
            durum_metni = "Yapıldı / Hazır ✅"
            summary = f"✅ {item['yayin_adi']} ({item['kanal']})"
        else:
            durum_metni = "Planlanan Canlı Yayın 📅"
            summary = f"📅 {item['yayin_adi']} ({item['kanal']})"

        # Açıklama metni
        desc_lines = [
            f"Kanal: {item['kanal']}",
            f"Program: {item['yayin_adi']}",
            f"Planlanan Zaman: {item['gun']} - {item['saat']}",
            f"Durum: {durum_metni}"
        ]
        if item["bilgi"]:
            desc_lines.append(f"Ek Not / Karşılaşma: {item['bilgi']}")
        desc_lines.append("Panel: https://tellal-otomasyon.web.app")
        desc_lines.append(f"[Tellal-ID: {item['sync_id']}]")
        description = "\\n".join(desc_lines)

        start_str = format_applescript_date(start_dt)
        end_str = format_applescript_date(end_dt)

        # Kaçış karakterleri
        clean_summary = summary.replace('"', '\\"')

        sync_id = item["sync_id"]
        if sync_id in mevcut_id_to_uid:
            # Güncelle
            uid = mevcut_id_to_uid[sync_id]
            sc_update = f'''
            tell application "Calendar"
                set targetCal to first calendar whose name is "{CALENDAR_NAME}"
                tell targetCal
                    set targetEvt to (first event whose uid is "{uid}")
                    set summary of targetEvt to "{clean_summary}"
                    set description of targetEvt to "{description}"
                    set start date of targetEvt to (date "{start_str}")
                    set end date of targetEvt to (date "{end_str}")
                end tell
            end tell
            '''
            run_applescript(sc_update)
            guncellenen_sayisi += 1
        else:
            # Yeni oluştur
            sc_create = f'''
            tell application "Calendar"
                set targetCal to first calendar whose name is "{CALENDAR_NAME}"
                tell targetCal
                    set newEvt to make new event at end of events with properties {{summary:"{clean_summary}", start date:(date "{start_str}"), end date:(date "{end_str}"), description:"{description}", url:"https://tellal-otomasyon.web.app"}}
                    return uid of newEvt
                end tell
            end tell
            '''
            run_applescript(sc_create)
            eklenen_sayisi += 1

    rapor = f"Yayın Takvimi Google Senkronizasyonu: +{eklenen_sayisi} yeni, ~{guncellenen_sayisi} güncellendi, -{silinen_sayisi} silindi."
    return True, rapor


def start_daemon_listener(poll_interval=4.0):
    """
    Firebase Realtime Database takvim tablosunu ve yerel takvim.txt dosyasını
    sürekli izleyerek Google Takvim'i arka planda otomatik güncel tutar.
    """
    print(f"🚀 Tellal Google Takvim Senkronizasyon Ajanı başlatıldı...")
    print(f"📅 Hedef Takvim: '{CALENDAR_NAME}' (Google ID: {GOOGLE_CALENDAR_ID})")
    print(f"⏱️ Kontrol sıklığı: {poll_interval} saniye")

    son_hash = ""
    while True:
        try:
            # 1. Firebase RTDB kontrol
            r = requests.get(f"{FIREBASE_DB_URL}/takvim.json?t={int(time.time()*1000)}", timeout=3.0)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, dict):
                    satirlar = data.get("satirlar") or []
                    if isinstance(satirlar, dict):
                        satirlar = list(satirlar.values())
                    cur_hash = hashlib.md5("".join(satirlar).encode("utf-8")).hexdigest()
                    if cur_hash != son_hash:
                        ok, msg = google_takvim_senkronize_et(satirlar)
                        if ok:
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
                            son_hash = cur_hash
        except Exception as e:
            pass

        time.sleep(poll_interval)


if __name__ == "__main__":
    if "--daemon" in sys.argv:
        start_daemon_listener()
    else:
        ok, msg = google_takvim_senkronize_et()
        print(msg)
