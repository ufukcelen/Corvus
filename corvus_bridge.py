#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Corvus Bridge CLI
Connects the Corvus Mac SwiftUI application with the corvus.py automation engine.
All features and operations from corvus.py are preserved 100% faithfully.
"""

import sys
import os
import argparse
import json
import io
import random
import unicodedata
import contextlib
from datetime import datetime, timezone, timedelta

# Auto-detect project directory
BRIDGE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(BRIDGE_DIR)
CANDIDATE_DIRS = [
    os.path.join(REPO_ROOT, "CorvusEngine"),
    os.path.join(BRIDGE_DIR, "CorvusEngine"),
    "/Users/ufukcelen/Desktop/The Projeler/Duyurular/Youtube Duyuru Otomasyon",
]
DEFAULT_PROJECT_DIR = next((d for d in CANDIDATE_DIRS if os.path.isdir(d)), BRIDGE_DIR)


def setup_environment(project_dir):
    p_dir = os.path.abspath(project_dir or DEFAULT_PROJECT_DIR)
    if not os.path.isdir(p_dir):
        p_dir = next((d for d in CANDIDATE_DIRS if os.path.isdir(d)), BRIDGE_DIR)
    if p_dir not in sys.path:
        sys.path.insert(0, p_dir)
    os.chdir(p_dir)
    try:
        import corvus
        # Patch interactive prompts so child subprocess from SwiftUI never blocks/hangs
        if hasattr(corvus, "Prompt"):
            corvus.Prompt.ask = lambda *args, **kwargs: kwargs.get("default", "")
        if hasattr(corvus, "Confirm"):
            corvus.Confirm.ask = lambda *args, **kwargs: kwargs.get("default", True)
        return corvus, p_dir
    except ImportError as e:
        sys.stderr.write(f"HATA: corvus modülü '{p_dir}' dizininden yüklenemedi: {e}\n")
        sys.exit(1)


def cmd_get_matches(args, corvus, p_dir):
    tarih = args.tarih or datetime.now(timezone(timedelta(hours=3))).strftime("%Y-%m-%d")
    sezon_yili = corvus.sezon_hesapla(tarih)
    
    if args.league:
        lig_id = int(args.league)
        params = {"date": tarih, "league": lig_id, "season": sezon_yili, "timezone": "Europe/Istanbul"}
    else:
        params = {"date": tarih, "timezone": "Europe/Istanbul"}
        
    # Redirect console prints during API call so stdout is strictly clean JSON
    with contextlib.redirect_stdout(sys.stderr):
        tum = corvus.api_maclar(params)
        
    if not args.league:
        maclar = [m for m in tum if m.get("league", {}).get("id") in corvus.HEPSI_LIG_IDLERI]
    else:
        maclar = tum

    sonuc = []
    for m in maclar:
        try:
            utc_time = datetime.strptime(m['fixture']['date'], "%Y-%m-%dT%H:%M:%S%z")
            tr_time = utc_time.astimezone(timezone(timedelta(hours=3)))
            mac_saati_str = tr_time.strftime("%H:%M")
        except Exception:
            mac_saati_str = "20:00"

        sonuc.append({
            "id": m['fixture']['id'],
            "date": m['fixture']['date'],
            "time_str": mac_saati_str,
            "home": m['teams']['home']['name'],
            "home_id": m['teams']['home']['id'],
            "home_logo": m['teams']['home'].get('logo'),
            "away": m['teams']['away']['name'],
            "away_id": m['teams']['away']['id'],
            "away_logo": m['teams']['away'].get('logo'),
            "league_id": m['league']['id'],
            "league_name": m['league']['name']
        })
    print(json.dumps(sonuc, ensure_ascii=False, indent=2))


def cmd_haftalik_program(args, corvus, p_dir):
    saat = args.saat or "21:00"
    print(f"[Corvus Mac] Haftalık Program hazırlanıyor... Saat: {saat}")
    corvus.yayin_saati_kaydet(saat)

    import shutil
    shutil.copyfile(os.path.join(corvus.BASE_DIR, "Borders", "superlig.png"), os.path.join(corvus.BASE_DIR, "cerceve.png"))
    shutil.copyfile(os.path.join(corvus.BASE_DIR, "arkaPlanlar", "superligback.png"), os.path.join(corvus.BASE_DIR, "arkaPlan.png"))
    shutil.copyfile(os.path.join(corvus.BASE_DIR, "alt", "haftalık futbol programı.png"), os.path.join(corvus.BASE_DIR, "konu.png"))
    shutil.copyfile(os.path.join(corvus.BASE_DIR, "kafalar", "haftalık.png"), os.path.join(corvus.BASE_DIR, "kafa.png"))
    shutil.copyfile(os.path.join(corvus.BASE_DIR, "boş.png"), os.path.join(corvus.BASE_DIR, "evTakım.png"))
    shutil.copyfile(os.path.join(corvus.BASE_DIR, "boş.png"), os.path.join(corvus.BASE_DIR, "depTakım.png"))
    shutil.copyfile(os.path.join(corvus.BASE_DIR, "logo.png"), os.path.join(corvus.BASE_DIR, "VS.png"))

    klasor = corvus.cikti_klasoru_al("Haftalık Program")
    if args.render:
        video_adi = "Haftalik_Program_Duyurusu.mp4"
        print(f"[Corvus Mac] Render başlatılıyor: {video_adi} -> {klasor}")
        corvus.ae_render_baslat(video_adi, hedef_klasor=klasor)
        corvus.seo_haftalik_yaz(saat, video_adi, hedef_klasor=klasor)
    else:
        print("[Corvus Mac] Render atlandı.")

    if args.thumbnail:
        print("[Corvus Mac] Photoshop ile Haftalık Program Thumbnail üretiliyor...")
        corvus.haftalik_thumbnail_olustur()


def cmd_canli_mac(args, corvus, p_dir):
    tarih = args.tarih or datetime.now(timezone(timedelta(hours=3))).strftime("%Y-%m-%d")
    mac_id = str(args.mac_id)
    mac_sonu = bool(args.mac_sonu)
    
    print(f"[Corvus Mac] Maç aranıyor: ID {mac_id} (Tarih: {tarih})...")
    with contextlib.redirect_stdout(sys.stderr):
        tum = corvus.api_maclar({"date": tarih, "timezone": "Europe/Istanbul"})
        
    mac_verisi = next((m for m in tum if str(m.get('fixture', {}).get('id')) == mac_id), None)
    if not mac_verisi:
        sys.stderr.write(f"HATA: {mac_id} ID'li maç {tarih} tarihinde bulunamadı!\n")
        sys.exit(1)

    ev_adi = mac_verisi['teams']['home']['name']
    dep_adi = mac_verisi['teams']['away']['name']
    print(f"[Corvus Mac] Seçilen Maç: {ev_adi} vs {dep_adi}")

    try:
        utc_time = datetime.strptime(mac_verisi['fixture']['date'], "%Y-%m-%dT%H:%M:%S%z")
        tr_time = utc_time.astimezone(timezone(timedelta(hours=3)))
        varsayilan_saat = tr_time.strftime("%H:%M")
    except Exception:
        varsayilan_saat = "20:00"

    saat = args.saat or varsayilan_saat
    corvus.yayin_saati_kaydet(saat)

    lig_id = mac_verisi['league']['id']
    b_map = {2: "cl.png", 3: "europa.png", 848: "conferance.png", 203: "superlig.png", 5: "uluslarLigi.png"}
    bg_map = {2: "clback.png", 3: "europaback.png", 848: "confBack.png", 203: "superligback.png", 5: "ulusArka.png"}

    import shutil
    shutil.copyfile(os.path.join(corvus.BASE_DIR, "Borders", b_map.get(lig_id, "superlig.png")), os.path.join(corvus.BASE_DIR, "cerceve.png"))
    shutil.copyfile(os.path.join(corvus.BASE_DIR, "arkaPlanlar", bg_map.get(lig_id, "superligback.png")), os.path.join(corvus.BASE_DIR, "arkaPlan.png"))
    shutil.copyfile(os.path.join(corvus.BASE_DIR, "alt", "maç sonu.png" if mac_sonu else "canlı maç sohbetlerİ.png"), os.path.join(corvus.BASE_DIR, "konu.png"))
    shutil.copyfile(os.path.join(corvus.BASE_DIR, "kafalar", "millitakım.png" if lig_id == 5 else "haftalık.png"), os.path.join(corvus.BASE_DIR, "kafa.png"))
    shutil.copyfile(os.path.join(corvus.BASE_DIR, "dosyalar", "VS.png"), os.path.join(corvus.BASE_DIR, "VS.png"))

    corvus.logo_hazirla(mac_verisi['teams']['home'].get('logo'), os.path.join(corvus.BASE_DIR, "evTakım.png"), ev_adi)
    corvus.logo_hazirla(mac_verisi['teams']['away'].get('logo'), os.path.join(corvus.BASE_DIR, "depTakım.png"), dep_adi)
    corvus.png_dogrula(["cerceve.png", "arkaPlan.png", "konu.png", "kafa.png", "VS.png", "evTakım.png", "depTakım.png"])

    prog_adi = "Maç Sonu" if mac_sonu else "Canlı Maç Sohbetleri"
    klasor = corvus.cikti_klasoru_al(prog_adi, tarih=tarih)
    
    if args.render:
        video_adi = f"{'Mac_Sonu' if mac_sonu else 'Mac_Sohbeti'}_{saat.replace(':', '')}.mp4"
        print(f"[Corvus Mac] Render başlatılıyor: {video_adi} -> {klasor}")
        corvus.ae_render_baslat(video_adi, hedef_klasor=klasor)
        corvus.seo_canli_yaz(mac_verisi, saat, video_adi, mac_sonu=mac_sonu, hedef_klasor=klasor)

    if args.thumbnail:
        print("[Corvus Mac] Photoshop ile Canlı Maç Thumbnail üretiliyor...")
        corvus.canli_mac_thumbnail_olustur(mac_verisi)


def cmd_memleket_duyuru(args, corvus, p_dir):
    saat = args.saat or corvus.MEM_VARSAYILAN_SAAT
    print(f"[Corvus Mac] Filtresiz Memleket Havası hazırlanıyor... Saat: {saat}")
    
    mevcut = [g for g in corvus.MEM_GORSELLER if os.path.exists(os.path.join(corvus.MEM_ASSETS_DIR, g))]
    if not mevcut:
        sys.stderr.write(f"HATA: {corvus.MEM_ASSETS_DIR} içinde cemBurhan1-4.png bulunamadı!\n")
        sys.exit(1)
        
    secilen = random.choice(mevcut)
    import shutil
    shutil.copyfile(os.path.join(corvus.MEM_ASSETS_DIR, secilen), corvus.MEM_SUB_YOLU)
    print(f"[Corvus Mac] Seçilen görsel: {secilen} -> yayınSub.png")

    with open(corvus.MEM_JSON_YOLU, "w", encoding="utf-8") as f:
        json.dump({"baslik": corvus.MEM_BASLIK, "saat": saat}, f, ensure_ascii=False)

    klasor = corvus.cikti_klasoru_al("Memleket Havası")
    if args.render:
        video_adi = f"Memleket_Havasi_{saat.replace(':', '')}.mp4"
        proje_yolu = next((os.path.join(corvus.MEMLEKET_DIR, a) for a in corvus.MEM_PROJE_ADAYLARI if os.path.exists(os.path.join(corvus.MEMLEKET_DIR, a))), None)
        if not proje_yolu:
            sys.stderr.write("HATA: Memleket After Effects projesi bulunamadı!\n")
            sys.exit(1)
        print(f"[Corvus Mac] Render başlatılıyor: {video_adi} -> {klasor}")
        corvus.ae_render_baslat(video_adi, proje_yolu=proje_yolu, kompozisyon=corvus.MEM_KOMPOZISYON, hedef_klasor=klasor)
        corvus.seo_memleket_yaz(saat, video_adi, hedef_klasor=klasor)


def cmd_memleket_thumbnail(args, corvus, p_dir):
    bolum_giris = args.bolum
    if not bolum_giris:
        sys.stderr.write("HATA: Bölüm numarası girilmedi!\n")
        sys.exit(1)

    temiz_no = bolum_giris.lstrip("#").strip()
    etiket_no = f"#{temiz_no}"
    jpg_cikis_yolu = os.path.join(corvus.MASAUSTU, f"memleket{temiz_no}.jpg")

    hue1 = random.randint(-180, 180)
    hue2 = random.randint(-180, 180)

    ps_app = corvus.photoshop_app_adi_al()
    if not ps_app:
        sys.stderr.write("HATA: Photoshop uygulaması bulunamadı!\n")
        sys.exit(1)

    psd_yolu = corvus.psd_sablonu_temin_et("memleketYatay.psd")
    if not psd_yolu:
        sys.stderr.write("HATA: memleketYatay.psd şablonu temin edilemedi!\n")
        sys.exit(1)

    jsx_script = f"""#target photoshop
app.displayDialogs = DialogModes.NO;

function setHue(layerName, hueValue) {{
    try {{
        var doc = app.activeDocument;
        var lyr = doc.artLayers.getByName(layerName);
        doc.activeLayer = lyr;
        var d = new ActionDescriptor();
        var dHue = new ActionDescriptor();
        dHue.putInteger(charIDToTypeID("H   "), hueValue);
        var list = new ActionList();
        list.putDescriptor(charIDToTypeID("Hst2"), dHue);
        d.putList(charIDToTypeID("Adjs"), list);
        executeAction(charIDToTypeID("setd"), d, DialogModes.NO);
    }} catch(e) {{}}
}}

try {{
    var doc = app.open(new File('{psd_yolu}'));
    try {{
        var txtLyr = doc.artLayers.getByName("bolumno");
        txtLyr.textItem.contents = "{etiket_no}";
    }} catch(e) {{}}

    setHue("renk1", {hue1});
    setHue("renk2", {hue2});

    var jpgFile = new File('{jpg_cikis_yolu}');
    var jpgOpts = new JPEGSaveOptions();
    jpgOpts.quality = 12;
    jpgOpts.embedColorProfile = true;
    doc.saveAs(jpgFile, jpgOpts, true, Extension.LOWERCASE);

    doc.close(SaveOptions.DONOTSAVECHANGES);
    'SUCCESS';
}} catch (e) {{
    'ERROR: ' + e.message;
}}
"""
    temp_jsx = "/tmp/corvus_memleket_thumb.jsx"
    with open(temp_jsx, "w", encoding="utf-8") as f:
        f.write(jsx_script)

    import subprocess
    applescript_cmd = f'''tell application "{ps_app}"
        do javascript (file "{temp_jsx}")
    end tell'''
    
    print(f"[Corvus Mac] Photoshop çalışıyor: Bölüm {etiket_no}...")
    proc = subprocess.run(["osascript", "-e", applescript_cmd], capture_output=True, text=True)
    if "ERROR" in proc.stdout or proc.returncode != 0:
        sys.stderr.write(f"Photoshop Hatası: {proc.stdout or proc.stderr}\n")
        sys.exit(1)
    else:
        corvus.ses_cal()
        print(f"[Corvus Mac] Başarılı! Thumbnail oluşturuldu: {jpg_cikis_yolu}")


def cmd_haftalik_thumbnail(args, corvus, p_dir):
    ok = corvus.haftalik_thumbnail_olustur()
    if not ok:
        sys.exit(1)


def cmd_canli_thumbnail(args, corvus, p_dir):
    mac_id = str(args.mac_id)
    tarih = args.tarih or datetime.now(timezone(timedelta(hours=3))).strftime("%Y-%m-%d")
    with contextlib.redirect_stdout(sys.stderr):
        tum = corvus.api_maclar({"date": tarih, "timezone": "Europe/Istanbul"})
    mac_verisi = next((m for m in tum if str(m.get('fixture', {}).get('id')) == mac_id), None)
    if not mac_verisi:
        sys.stderr.write(f"HATA: {mac_id} ID'li maç {tarih} tarihinde bulunamadı!\n")
        sys.exit(1)
    ok = corvus.canli_mac_thumbnail_olustur(mac_verisi)
    if not ok:
        sys.exit(1)


def cmd_albert_ve_cem(args, corvus, p_dir):
    saat = args.saat or corvus.ALBERT_VARSAYILAN_SAAT
    print(f"[Corvus Mac] Albert ve Cem hazırlanıyor... Saat: {saat}")
    with open(corvus.ALBERT_JSON_YOLU, "w", encoding="utf-8") as f:
        json.dump({"baslik": "BU AKŞAM", "saat": saat}, f, ensure_ascii=False)

    klasor = corvus.cikti_klasoru_al("Albert ve Cem")
    if args.render:
        video_adi = f"Albert_ve_Cem_{saat.replace(':', '')}.mp4"
        print(f"[Corvus Mac] Render başlatılıyor: {video_adi} -> {klasor}")
        corvus.ae_render_baslat(video_adi, proje_yolu=corvus.ALBERT_PROJE_YOLU, kompozisyon=corvus.ALBERT_KOMPOZISYON, hedef_klasor=klasor)
        corvus.seo_albert_yaz(saat, video_adi, hedef_klasor=klasor)


def cmd_tek_mac(args, corvus, p_dir):
    saat = args.saat or corvus.TMY_VARSAYILAN_SAAT
    kayhan_var = bool(args.kayhan)
    etiketler = [t.strip() for t in (args.etiketler or "").split(",") if t.strip()]

    print(f"[Corvus Mac] Tek Maçtan Yatanlar hazırlanıyor... Saat: {saat} (Kayhan: {'Var' if kayhan_var else 'Yok'})")
    corvus.tmy_json_guncelle(saat)
    
    # corvus.py logic: kayhan.png if kayhan_var else cem.png
    kaynak = "kayhan.png" if kayhan_var else "cem.png"
    kaynak_yol = os.path.join(corvus.TMY_ASSETS_DIR, kaynak)
    if not os.path.exists(kaynak_yol):
        sys.stderr.write(f"HATA: {kaynak_yol} bulunamadı!\n")
        sys.exit(1)

    import shutil
    shutil.copyfile(kaynak_yol, corvus.TMY_GORSEL_YOLU)
    print(f"[Corvus Mac] Görsel kopyalandı: {kaynak} -> tmyGorsel.png")

    klasor = corvus.cikti_klasoru_al("Tek Maçtan Yatanlar")
    if args.render:
        proje = corvus.tmy_proje_bul()
        if not proje:
            sys.stderr.write("HATA: Tek Maç After Effects projesi bulunamadı!\n")
            sys.exit(1)
        video_adi = corvus.TMY_VIDEO_ADI
        print(f"[Corvus Mac] Render başlatılıyor: {video_adi} -> {klasor}")
        corvus.ae_render_baslat(video_adi, proje_yolu=proje, kompozisyon=corvus.TMY_KOMPOZISYON, hedef_klasor=klasor)
        corvus.seo_tmy_yaz(saat, kayhan_var, etiketler, video_adi, hedef_klasor=klasor)


def cmd_fc_kariyer(args, corvus, p_dir):
    takim = args.takim or corvus.FC_VARSAYILAN_TAKIM
    print(f"[Corvus Mac] FC27 Kariyer hazırlanıyor... Takım: {takim}")
    corvus.fc_takim_yaz(takim)

    # Logo ara ve hazırla
    eslesen = corvus.fc_takim_ara(takim)
    if eslesen and "logo" in eslesen[0]:
        corvus.fc_logo_hazirla(eslesen[0]["logo"])

    klasor = corvus.cikti_klasoru_al("FC27 Kariyer")
    corvus.fc27_txt_yaz(takim, klasor)
    
    if args.render:
        video_adi = corvus.FC_VIDEO_ADI
        print(f"[Corvus Mac] Render başlatılıyor: {video_adi} -> {klasor}")
        corvus.ae_render_baslat(video_adi, proje_yolu=corvus.FC_PROJE_YOLU, kompozisyon=corvus.FC_KOMPOZISYON, hedef_klasor=klasor)


def main():
    parser = argparse.ArgumentParser(description="Corvus Bridge CLI")
    parser.add_argument("--dir", default=DEFAULT_PROJECT_DIR, help="Corvus Proje Dizini")

    subparsers = parser.add_subparsers(dest="cmd")

    # get_matches
    p_m = subparsers.add_parser("get_matches")
    p_m.add_argument("--tarih", default=None)
    p_m.add_argument("--league", default=None)

    # haftalik_program
    p_h = subparsers.add_parser("haftalik_program")
    p_h.add_argument("--saat", default="21:00")
    p_h.add_argument("--render", action="store_true")
    p_h.add_argument("--thumbnail", action="store_true")

    # canli_mac
    p_c = subparsers.add_parser("canli_mac")
    p_c.add_argument("--tarih", default=None)
    p_c.add_argument("--mac_id", required=True)
    p_c.add_argument("--saat", default=None)
    p_c.add_argument("--mac_sonu", action="store_true")
    p_c.add_argument("--render", action="store_true")
    p_c.add_argument("--thumbnail", action="store_true")

    # memleket_duyuru
    p_mem = subparsers.add_parser("memleket_duyuru")
    p_mem.add_argument("--saat", default="22:00")
    p_mem.add_argument("--render", action="store_true")

    # memleket_thumbnail
    p_mt = subparsers.add_parser("memleket_thumbnail")
    p_mt.add_argument("--bolum", required=True)

    # haftalik_thumbnail
    subparsers.add_parser("haftalik_thumbnail")

    # canli_thumbnail
    p_ct = subparsers.add_parser("canli_thumbnail")
    p_ct.add_argument("--mac_id", required=True)
    p_ct.add_argument("--tarih", default=None)

    # albert_ve_cem
    p_ac = subparsers.add_parser("albert_ve_cem")
    p_ac.add_argument("--saat", default="23:00")
    p_ac.add_argument("--render", action="store_true")

    # tek_mac
    p_tm = subparsers.add_parser("tek_mac")
    p_tm.add_argument("--saat", default="21:00")
    p_tm.add_argument("--kayhan", type=int, default=1)
    p_tm.add_argument("--etiketler", default="")
    p_tm.add_argument("--render", action="store_true")

    # fc_kariyer
    p_fc = subparsers.add_parser("fc_kariyer")
    p_fc.add_argument("--takim", default="Feyenoord")
    p_fc.add_argument("--render", action="store_true")

    args = parser.parse_args()

    if not args.cmd:
        parser.print_help()
        sys.exit(0)

    corvus, p_dir = setup_environment(args.dir)

    dispatch = {
        "get_matches": cmd_get_matches,
        "haftalik_program": cmd_haftalik_program,
        "canli_mac": cmd_canli_mac,
        "memleket_duyuru": cmd_memleket_duyuru,
        "memleket_thumbnail": cmd_memleket_thumbnail,
        "haftalik_thumbnail": cmd_haftalik_thumbnail,
        "canli_thumbnail": cmd_canli_thumbnail,
        "albert_ve_cem": cmd_albert_ve_cem,
        "tek_mac": cmd_tek_mac,
        "fc_kariyer": cmd_fc_kariyer,
    }

    if args.cmd in dispatch:
        dispatch[args.cmd](args, corvus, p_dir)
    else:
        sys.stderr.write(f"Bilinmeyen komut: {args.cmd}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
