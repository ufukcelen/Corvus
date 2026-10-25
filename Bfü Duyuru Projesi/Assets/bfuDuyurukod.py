import os
import re
import io
import json
import sys
import shutil
import subprocess
from datetime import datetime, timedelta, timezone

import requests

# =====================================================================
# AYARLAR
# =====================================================================
AERENDER_YOLU = "/Applications/Adobe After Effects 2026/aerender"
KOMPOZISYON_ADI = "mainsahne"
CIKTI_SABLONU = "H264_40M"

PNG_IMZA = b"\x89PNG\r\n\x1a\n"

# Takım logosu indirilemezse kullanılacak jenerik görsel (Assets klasöründe)
JENERIK_LOGO = "boş.png"

# Scriptin bulunduğu klasör "Assets"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJE_ANA_KLASOR = os.path.dirname(BASE_DIR)
AE_PROJE_YOLU = os.path.join(PROJE_ANA_KLASOR, "bfuDuyuru2027.aep")
MASAUSTU = os.path.expanduser("~/Desktop")

API_URL = "https://v3.football.api-sports.io/fixtures"
API_TIMEOUT = 10
TR_TZ = timezone(timedelta(hours=3))

# Turnuva menüsü: secim -> (API lig ID, görünen ad)
TURNUVALAR = {
    "1": (2, "Şampiyonlar Ligi"),
    "2": (3, "Europa Ligi"),
    "3": (848, "Konferans Ligi"),
    "4": (203, "Süper Lig"),
    "5": (5, "Uluslar Ligi"),
}
HEPSI = "6"

# "Önümüzdeki N gün" seçeneği (tarih sorusunda bu kodu yazınca devreye girer)
HAFTA_KODU = "7"
HAFTA_GUN_SAYISI = 7  # bugün dahil
GUNLER = ("Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz")

# Lig ID -> görsel dosyaları
BORDER_MAP = {2: "cl.png", 3: "europa.png", 848: "conferance.png", 203: "superlig.png", 5: "uluslarLigi.png"}
BG_MAP = {2: "clback.png", 3: "europaback.png", 848: "confBack.png", 203: "superligback.png", 5: "ulusArka.png"}


# =====================================================================
# API ANAHTARI (kodda tutulmaz)
# Önce ortam değişkeni, yoksa Assets klasöründeki api_key.txt okunur.
#   Terminal:  export API_SPORTS_KEY="anahtarin"
# =====================================================================
def api_anahtari_al():
    anahtar = os.environ.get("API_SPORTS_KEY", "").strip()
    if not anahtar:
        yol = os.path.join(BASE_DIR, "api_key.txt")
        if os.path.exists(yol):
            with open(yol, "r", encoding="utf-8") as f:
                anahtar = f.read().strip()
    return anahtar


API_KEY = api_anahtari_al()
if not API_KEY:
    print("[HATA] API anahtarı bulunamadı.")
    print(f"Ya 'API_SPORTS_KEY' ortam değişkenini ayarla ya da anahtarı şu dosyaya tek satır olarak yaz:")
    print(f"  {os.path.join(BASE_DIR, 'api_key.txt')}")
    sys.exit(1)

HEADERS = {"x-apisports-key": API_KEY}


# =====================================================================
# GİRİŞ YARDIMCILARI  (her prompt'ta 0 = geri / ana menü)
# =====================================================================
class Geri(Exception):
    """Kullanıcı 0 yazdı, ana menüye dön."""


def girdi_al(metin):
    s = input(metin).strip()
    if s == "0":
        raise Geri()
    return s


def saat_gecerli_mi(s):
    return re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", s) is not None


def saat_sor(metin, varsayilan=None):
    while True:
        if varsayilan:
            s = girdi_al(f"{metin} [{varsayilan}] (Enter = onayla): ")
            if not s:
                return varsayilan
        else:
            s = girdi_al(f"{metin} (Örn: 21:00): ")
        if saat_gecerli_mi(s):
            return s
        print("[UYARI] Geçersiz saat. Biçim: SS:DD  (Örn: 21:30)")


def tarih_sor():
    """Bir tarih (YYYY-MM-DD) döner. 'önümüzdeki N gün' seçilirse HAFTA_KODU döner."""
    bugun = datetime.now(TR_TZ).strftime("%Y-%m-%d")
    while True:
        s = girdi_al(
            f"Tarih (YYYY-MM-DD) [{bugun}] "
            f"(Enter = bugün, {HAFTA_KODU} = önümüzdeki {HAFTA_GUN_SAYISI} gün): "
        )
        if not s:
            return bugun
        if s == HAFTA_KODU:
            return HAFTA_KODU
        try:
            datetime.strptime(s, "%Y-%m-%d")
            return s
        except ValueError:
            print("[UYARI] Geçersiz tarih. Örnek: 2026-10-23")


def evet_mi(metin):
    """Enter = Evet."""
    s = girdi_al(f"{metin} (Enter = Evet, H = Hayır): ").upper()
    return s not in ("H", "N")


def turnuva_sor():
    print("\n1: Şampiyonlar Ligi | 2: Europa Ligi | 3: Konferans Ligi | 4: Süper Lig | 5: Uluslar Ligi | 6: Hepsi")
    while True:
        s = girdi_al("Turnuva seçin (1-6, 0 = geri): ")
        if s in TURNUVALAR or s == HEPSI:
            return s
        print("[UYARI] Geçersiz seçim, 1-6 arası bir sayı gir.")


# =====================================================================
# DOSYA İŞLEMLERİ
# =====================================================================
def yol(*parca):
    return os.path.join(BASE_DIR, *parca)


def csv_yaz(saat):
    icerik = f'baslik\n"Bu Aksam {saat}"'.encode("utf-8")
    with open(yol("yayin_saati.csv"), "wb") as f:
        f.write(icerik)


def json_yaz(saat):
    """AE'nin okuması için yayin_saati.json yazar (CSV'ye ek olarak)."""
    with open(yol("yayin_saati.json"), "w", encoding="utf-8") as f:
        json.dump({"baslik": f"Bu Aksam {saat}"}, f, ensure_ascii=False)


def logo_indir(url, hedef):
    """
    Logoyu indirir. İçerik gerçek bir PNG değilse (WebP, JPEG, SVG, HTML hata sayfası...)
    Pillow ile PNG'ye çevirmeyi dener; çevrilemezse hata fırlatır.
    Geçersiz içerik ASLA hedef dosyaya yazılmaz (AE "not a PNG" hatası vermesin diye).
    """
    r = requests.get(url, timeout=API_TIMEOUT)
    r.raise_for_status()
    veri = r.content
    if not veri:
        raise ValueError("boş yanıt geldi")

    if not veri.startswith(PNG_IMZA):
        tip = r.headers.get("Content-Type", "bilinmiyor")
        try:
            from PIL import Image
        except ImportError:
            raise ValueError(f"PNG değil ({tip}) ve Pillow yüklü değil (pip3 install pillow)")
        try:
            img = Image.open(io.BytesIO(veri)).convert("RGBA")
            tampon = io.BytesIO()
            img.save(tampon, format="PNG")
            veri = tampon.getvalue()
            print(f"[BİLGİ] Logo PNG değildi ({tip}), PNG'ye çevrildi: {os.path.basename(hedef)}")
        except Exception:
            raise ValueError(f"PNG değil ({tip}) ve PNG'ye çevrilemedi")

    with open(hedef, "wb") as f:
        f.write(veri)


def logo_hazirla(url, hedef, etiket):
    """
    Logoyu indirmeyi dener. Başarısız olursa süreci kesmez,
    JENERIK_LOGO'yu hedef dosyanın üzerine kopyalar ve uyarı basar.
    True = gerçek logo, False = jenerik logo kullanıldı.
    """
    try:
        if not url:
            raise ValueError("logo adresi yok")
        logo_indir(url, hedef)
        return True
    except Exception as e:
        print(f"[UYARI] {etiket} logosu indirilemedi ({e}). Jenerik logo kullanılıyor.")
        shutil.copyfile(yol(JENERIK_LOGO), hedef)
        return False


def png_mi(dosya):
    try:
        with open(dosya, "rb") as f:
            return f.read(8) == PNG_IMZA
    except OSError:
        return False


def png_dogrula(dosyalar):
    """
    AE'nin okuduğu görsellerin gerçekten PNG olup olmadığını render öncesi kontrol eder.
    PNG olmayanı Pillow ile aynı dosya adıyla PNG'ye çevirir. Sonucu her zaman ekrana yazar.
    """
    sorunlu = 0
    for ad in dosyalar:
        hedef = yol(ad)
        if not os.path.exists(hedef):
            print(f"[UYARI] {ad} bulunamadı.")
            sorunlu += 1
            continue
        if png_mi(hedef):
            continue
        try:
            from PIL import Image
            img = Image.open(hedef).convert("RGBA")
            img.save(hedef, format="PNG")
            print(f"[BİLGİ] {ad} PNG değildi, PNG'ye çevrildi.")
        except ImportError:
            print(f"[UYARI] {ad} PNG değil ve Pillow yüklü değil (pip3 install pillow). Render hata verebilir.")
            sorunlu += 1
        except Exception as e:
            print(f"[UYARI] {ad} PNG değil ve çevrilemedi ({e}). Render hata verebilir.")
            sorunlu += 1

    if sorunlu == 0:
        print(f"[KONTROL] {len(dosyalar)} görselin hepsi geçerli PNG.")


def gorselleri_hazirla(border, arkaplan, konu, kafa, vs, ev=None, dep=None):
    """
    Tüm duyuru görsellerini AE'nin okuduğu sabit isimlere kopyalar.
    ev / dep: takım logosu URL'si. None ise boş.png kullanılır.
    Diğer parametreler Assets klasörüne göre göreli yol (liste) olarak verilir.
    """
    shutil.copyfile(yol("Borders", border), yol("cerceve.png"))
    shutil.copyfile(yol("arkaPlanlar", arkaplan), yol("arkaPlan.png"))
    shutil.copyfile(yol("alt", konu), yol("konu.png"))
    shutil.copyfile(yol("kafalar", kafa), yol("kafa.png"))
    shutil.copyfile(yol(*vs), yol("VS.png"))

    if ev is None and dep is None:
        # Haftalık program: takım logosu yok
        shutil.copyfile(yol("boş.png"), yol("evTakım.png"))
        shutil.copyfile(yol("boş.png"), yol("depTakım.png"))
    else:
        # Canlı maç: her logo ayrı denenir, biri başarısız olsa da süreç devam eder
        logo_hazirla(ev, yol("evTakım.png"), "Ev sahibi")
        logo_hazirla(dep, yol("depTakım.png"), "Deplasman")

    png_dogrula(["cerceve.png", "arkaPlan.png", "konu.png", "kafa.png", "VS.png", "evTakım.png", "depTakım.png"])


# =====================================================================
# RENDER
# =====================================================================
def ae_render_baslat(cikis_adi):
    if not os.path.exists(AERENDER_YOLU):
        print(f"\n[CRITICAL HATA] aerender motoru bulunamadı! Yol: {AERENDER_YOLU}")
        return

    if not os.path.exists(AE_PROJE_YOLU):
        print(f"\n[CRITICAL HATA] After Effects projesi bulunamadı! Yol: {AE_PROJE_YOLU}")
        return

    cikis_yolu = os.path.join(MASAUSTU, cikis_adi)

    if os.path.exists(cikis_yolu):
        try:
            os.remove(cikis_yolu)
        except OSError:
            pass

    print("\n[RENDER] After Effects arka planda başlatılıyor...")
    print(f"[RENDER] Proje: {os.path.basename(AE_PROJE_YOLU)} | Comp: {KOMPOZISYON_ADI} | Şablon: {CIKTI_SABLONU}")
    print(f"[RENDER] Hedef: {cikis_yolu}")
    print("[RENDER] İlerleme:")
    print("-" * 50)

    komut = [
        AERENDER_YOLU,
        "-project", AE_PROJE_YOLU,
        "-comp", KOMPOZISYON_ADI,
        "-OMtemplate", CIKTI_SABLONU,
        "-output", cikis_yolu,
        "-v", "ERRORS_AND_PROGRESS",
    ]

    try:
        process = subprocess.Popen(komut, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        tam_log = []
        for satir in iter(process.stdout.readline, ""):
            tam_log.append(satir)
            if "PROGRESS:" in satir:
                print(satir.strip())
            elif any(k in satir.lower() for k in ("warning", "error", "font", "expression", "footage", "missing")):
                print("[AE]", satir.strip())

        process.stdout.close()
        return_code = process.wait()

        print("-" * 50)
        log_metni = "".join(tam_log)

        # Fiziksel kontrol: dosya gerçekten oluştu mu?
        cikti_var = os.path.exists(cikis_yolu)
        hata_var = ("aerender error" in log_metni.lower()) or return_code != 0

        if hata_var or not cikti_var:
            print("\n[HATA] Render başarısız veya dosya oluşmadı.")
            print("Muhtemel sebep: şablon adı / H.264 desteği / proje içi eksik dosya.")
            print("\n--- AERENDER LOGU ---")
            print(log_metni)
            return

        print(f"\n[BAŞARILI] Render tamamlandı, Masaüstüne kaydedildi: {cikis_adi}")

    except Exception as e:
        print(f"\n[HATA] Render sırasında beklenmeyen hata: {e}")


def render_sor_ve_baslat(dosya_adi):
    if evet_mi("\n[BAŞARILI] Dosyalar güncellendi. Masaüstüne render başlatılsın mı?"):
        ae_render_baslat(dosya_adi)
    else:
        print("Render atlandı. Ana menüye dönülüyor...")


# =====================================================================
# API
# =====================================================================
def tr_saati(mac):
    t = datetime.strptime(mac["fixture"]["date"], "%Y-%m-%dT%H:%M:%S%z")
    return t.astimezone(TR_TZ)


def maclari_getir(tarih, turnuva_secim):
    """
    Sadece tarih ile çeker (sezon parametresi gerekmez), lige göre filtreler.
    timezone=Europe/Istanbul: 'tarih' Türkiye gününe göre yorumlanır.
    Hata durumunda None döner.
    """
    try:
        r = requests.get(
            API_URL,
            headers=HEADERS,
            params={"date": tarih, "timezone": "Europe/Istanbul"},
            timeout=API_TIMEOUT,
        )
        r.raise_for_status()
        res = r.json()
    except requests.exceptions.RequestException as e:
        print(f"\n[BAĞLANTI HATASI] API'ye ulaşılamadı: {e}")
        return None
    except ValueError:
        print("\n[API HATASI] Geçersiz yanıt alındı.")
        return None

    if res.get("errors"):
        print(f"\n[API HATASI] {res['errors']}")
        return None

    tum = res.get("response", [])
    if turnuva_secim == HEPSI:
        hedef = {v[0] for v in TURNUVALAR.values()}
    else:
        hedef = {TURNUVALAR[turnuva_secim][0]}

    maclar = [m for m in tum if m["league"]["id"] in hedef]
    maclar.sort(key=tr_saati)
    return maclar


def maclari_getir_hafta(baslangic, turnuva_secim):
    """
    Bugünden itibaren HAFTA_GUN_SAYISI günün maçlarını çeker (gün başına 1 API isteği).
    Bir gün başarısız olursa diğerleri yine de listelenir. Hepsi başarısız olursa None döner.
    """
    bas = datetime.strptime(baslangic, "%Y-%m-%d")
    print(f"\n[BİLGİ] Önümüzdeki {HAFTA_GUN_SAYISI} günün maçları çekiliyor...")

    tum = []
    basarili = 0
    for i in range(HAFTA_GUN_SAYISI):
        gun = (bas + timedelta(days=i)).strftime("%Y-%m-%d")
        maclar = maclari_getir(gun, turnuva_secim)
        if maclar is None:
            continue
        basarili += 1
        tum.extend(maclar)

    if basarili == 0:
        return None
    if basarili < HAFTA_GUN_SAYISI:
        print(f"\n[UYARI] {HAFTA_GUN_SAYISI} günün sadece {basarili} tanesi alınabildi, liste eksik olabilir.")

    tum.sort(key=tr_saati)
    return tum


def mac_sec(maclar, tarihli=False):
    """Sıra No (<=3 hane) veya Maç ID (>=4 hane) kabul eder. Seçilen maçı döner.
    tarihli=True: listede maçın tarihi ve günü de gösterilir (çok günlük liste için)."""
    print("\n--- MAÇLAR ---")
    for i, m in enumerate(maclar, start=1):
        ev = m["teams"]["home"]["name"]
        dep = m["teams"]["away"]["name"]
        t = tr_saati(m)
        if tarihli:
            zaman = f"{t:%d.%m} {GUNLER[t.weekday()]} {t:%H:%M}"
        else:
            zaman = f"{t:%H:%M}"
        print(f"{i}) {zaman} | {ev} - {dep} [{m['league']['name']}]")

    while True:
        s = girdi_al("\nSıra No veya Maç ID girin (0 = geri): ")
        if not s.isdigit():
            print("[UYARI] Sadece sayı gir.")
            continue

        if len(s) <= 3:
            idx = int(s)
            if 1 <= idx <= len(maclar):
                return maclar[idx - 1]
            print(f"[UYARI] Sıra No 1-{len(maclar)} arasında olmalı.")
        else:
            for m in maclar:
                if str(m["fixture"]["id"]) == s:
                    return m
            print("[UYARI] Bu ID listede yok.")


# =====================================================================
# MENÜLER
# =====================================================================
def menu_haftalik():
    saat = saat_sor("Yayın saati")
    csv_yaz(saat)
    json_yaz(saat)
    gorselleri_hazirla(
        border="superlig.png",
        arkaplan="superligback.png",
        konu="haftalık futbol programı.png",
        kafa="haftalık.png",
        vs=("logo.png",),  # Not: Canlı maç menüsü dosyalar/VS.png kullanıyor
    )
    render_sor_ve_baslat("Haftalik_Program_Duyurusu.mp4")


def menu_canli_mac():
    tarih = tarih_sor()
    turnuva = turnuva_sor()

    hafta = (tarih == HAFTA_KODU)
    if hafta:
        bugun = datetime.now(TR_TZ).strftime("%Y-%m-%d")
        maclar = maclari_getir_hafta(bugun, turnuva)
    else:
        maclar = maclari_getir(tarih, turnuva)

    if maclar is None:
        return
    if not maclar:
        if hafta:
            print(f"\n[UYARI] Önümüzdeki {HAFTA_GUN_SAYISI} günde bu kriterlere uygun maç bulunamadı.")
        else:
            print(f"\n[UYARI] {tarih} tarihinde bu kriterlere uygun maç bulunamadı.")
        return

    mac = mac_sec(maclar, tarihli=hafta)
    lig_id = mac["league"]["id"]

    oto_saat = (tr_saati(mac) - timedelta(minutes=15)).strftime("%H:%M")
    print(f"\nSeçilen: {mac['teams']['home']['name']} - {mac['teams']['away']['name']} ({tr_saati(mac):%H:%M})")
    print(f"Yayın saati maçtan 15 dk öncesine ({oto_saat}) ayarlandı.")
    saat = saat_sor("Yayın saati", oto_saat)

    csv_yaz(saat)
    json_yaz(saat)
    gorselleri_hazirla(
        border=BORDER_MAP.get(lig_id, "superlig.png"),
        arkaplan=BG_MAP.get(lig_id, "superligback.png"),
        konu="canlı maç sohbetlerİ.png",
        kafa="millitakım.png" if lig_id == 5 else "haftalık.png",
        vs=("dosyalar", "VS.png"),
        ev=mac["teams"]["home"].get("logo") or "",
        dep=mac["teams"]["away"].get("logo") or "",
    )
    render_sor_ve_baslat(f"Mac_Sohbeti_{saat.replace(':', '')}.mp4")


# =====================================================================
# ANA DÖNGÜ
# =====================================================================
def main():
    print(f"\n[SİSTEM] Aktif Çalışan Dosya: {os.path.abspath(__file__)}")

    while True:
        print("\n--- Uykusuz Tosba Duyuru Sistemi ---")
        print("1. Haftalık Program")
        print("2. Canlı Maç Sohbeti")
        print("0. Çıkış")
        secim = input("Seçiminiz: ").strip()

        if secim == "0":
            print("Çıkış yapılıyor...")
            break

        try:
            if secim == "1":
                menu_haftalik()
            elif secim == "2":
                menu_canli_mac()
            else:
                print("\n[UYARI] Geçersiz seçim. 1, 2 veya 0 gir.")
        except Geri:
            print("\nAna menüye dönülüyor...")
        except Exception as e:
            print(f"\n[HATA] Bir sorun oluştu: {e}")
            print("İşlem iptal edildi, ana menüye dönülüyor...")


if __name__ == "__main__":
    main()
