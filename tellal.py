
import importlib.util
import sys

_eksik = [ad for ad in ("requests", "rich", "PIL") if importlib.util.find_spec(ad) is None]
if _eksik:
    print(f"Eksik kütüphane: {', '.join(_eksik)}\nŞu komutu çalıştırıp programı tekrar aç:  pip3 install requests rich pillow")
    raise SystemExit(1)

import requests
import os
import shutil
import subprocess
import json
import re
import io
import random
import unicodedata
import glob
import hashlib
import platform
from urllib.parse import quote
from datetime import datetime, timedelta, timezone
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.markup import escape

console = Console()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

SURUM = "1.1.0"
SURUM_NOTLARI = {
    "1.1.0": [
        "Masaüstünde tek tıkla çalışan 'Tellal.app' başlatıcısı ve özel uygulama logosu eklendi.",
        "Tüm render ve SEO çıktıları masaüstünde gün/ay adıyla otomatik klasörlenir hale getirildi ({gün} {ay}_{program_adi}).",
        "GitHub güncelleme denetimi interaktif yapıldı: Güncelleme varsa sorulur, reddedilirse eski sürüm uyarısıyla devam edilir.",
        "Açılışa retro Tellal ASCII logosu ve kanal etiketleri (/uykusuztosba /radiomocas) eklendi.",
        "Radio Mocas menüsüne 'Albert ve Cem' canlı yayın otomasyonu (albert.json, albertSahne render ve albertSeo.txt) eklendi.",
        "Tarih (YYYY-MM-DD) ve saat (SS:DD) formatı doğrulaması eklenerek hatalı girişlerin programı çökertmesi önlendi.",
        "Hashtag çakışması ve çift diyez (##) hatası düzeltildi.",
        "saat_al() fonksiyonundaki varsayılan değer parametre hatası giderildi.",
        "Render bitiş sesi asenkron yapılarak terminal donması engellendi.",
        "Dosya kilitleme ve Pillow görsel bellek sızıntıları temizlendi.",
    ],
    "1.0.6": [
        "Radio Mocas menüsüne 2. seçenek olarak 'Albert ve Cem' canlı yayın otomasyonu eklendi.",
        "albert.json ve albertSeo.txt otomatik üretim ve planlama desteği tamamlandı.",
    ],
    "1.0.5": [
        "Hashtag çakışması ve çift diyez (##) hatası giderildi.",
        "Canlı Maç ve Maç Sonu menülerinde tarih formatı doğrulaması (YYYY-MM-DD) eklendi.",
        "Tüm duyuru türleri için saat girişleri güvenli ve zorunlu formata (SS:DD) bağlandı.",
        "saat_al() fonksiyonundaki varsayılan parametre (default) hatası düzeltildi.",
        "Render bitiş sesi asenkron yapılarak terminal donması engellendi.",
        "SEO metinleri render gecikse dahi masaüstüne kaydedilecek şekilde güvenceye alındı.",
        "Masaüstünde eski video açıksa silinememe durumunda bilgilendirme uyarısı eklendi.",
        "Takım arama (FC/AC/AS takımları) ve görsel dönüştürme fonksiyonları güçlendirildi.",
    ]
}


def yenilikleri_goster():
    """Yeni bir sürüme geçildiğinde sürüm notlarını kullanıcıya bir kerelik gösterir."""
    surum_dosyasi = os.path.join(SCRIPT_DIR, ".son_surum")
    son_surum = None
    if os.path.exists(surum_dosyasi):
        try:
            with open(surum_dosyasi, "r", encoding="utf-8") as f:
                son_surum = f.read().strip()
        except Exception:
            pass

    if son_surum != SURUM:
        notlar = SURUM_NOTLARI.get(SURUM, [])
        if notlar:
            maddeler = "\n".join(f"  [bold green]✓[/bold green] {madde}" for madde in notlar)
            icerik = f"[bold cyan]Tellal v{SURUM} Yenilikleri:[/bold cyan]\n\n{maddeler}"
            console.print(Panel(icerik, title="[bold yellow]🎉 Sürüm Güncellendi!", expand=False))
        try:
            with open(surum_dosyasi, "w", encoding="utf-8") as f:
                f.write(SURUM)
        except Exception:
            pass


# =====================================================================
# OTOMATİK GÜNCELLEME (GitHub)
# =====================================================================
GITHUB_REPO = "ufukcelen/tellal"
GITHUB_BRANCH = "main"
SCRIPT_GITHUB_ADI = "tellal.py"  

SEED_YOLLARI = {
    "Albert/albert.json",
    "FC Kariyer Duyuru/Assets/takımlogo.png",
    "FC Kariyer Duyuru/kariyer_takim.json",
    "Memleket Duyuru/yayınSub.png",
    "Memleket Duyuru/mem_yayin_saati.json",
    "Tekmaç/Assets/tmyGorsel.png",
    "Tekmaç/Assets/tmy.json",
}
SEED_KLASORLERI = ("Bfü Duyuru Projesi/Assets/",)  


def _nfc(metin):
    return unicodedata.normalize("NFC", metin)


def _git_blob_sha(veri):
    return hashlib.sha1(b"blob %d\0" % len(veri) + veri).hexdigest()


def _seed_mi(yol):
    y = _nfc(yol)
    if y in SEED_YOLLARI:
        return True
    return any(y.startswith(k) and "/" not in y[len(k):] for k in SEED_KLASORLERI)


def _github_indir(yol, beklenen_sha):
    url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/{quote(yol)}"
    r = requests.get(url, timeout=(5, 60))
    r.raise_for_status()
    if _git_blob_sha(r.content) != beklenen_sha:
        raise ValueError("indirilen dosya GitHub'daki güncel sürümle eşleşmedi (birkaç dakika sonra tekrar dene)")
    return r.content


def _guvenli_yaz(hedef, veri):
    os.makedirs(os.path.dirname(hedef), exist_ok=True)
    gecici = hedef + ".tellal_indir"
    with open(gecici, "wb") as f:
        f.write(veri)
    os.replace(gecici, hedef)


def guncelleme_kontrol():
    if os.environ.get("TELLAL_GUNCELLEME") == "0" or os.path.isdir(os.path.join(SCRIPT_DIR, ".git")):
        return
    try:
        with console.status("[dim]Güncellemeler kontrol ediliyor...[/dim]"):
            r = requests.get(
                f"https://api.github.com/repos/{GITHUB_REPO}/git/trees/{GITHUB_BRANCH}?recursive=1",
                headers={"Accept": "application/vnd.github+json"}, timeout=8,
            )
        if r.status_code == 403:
            raise RuntimeError("GitHub istek sınırı doldu, biraz sonra tekrar denenecek")
        if r.status_code == 404:
            raise RuntimeError("repo bulunamadı (adı/dalı yanlış ya da repo private)")
        r.raise_for_status()
        agac = r.json()
    except Exception as e:
        console.print(f"[dim]Güncelleme kontrolü yapılamadı ({escape(str(e))}); mevcut sürümle devam ediliyor.[/dim]")
        return
    if agac.get("truncated"):
        console.print("[bold yellow][UYARI][/bold yellow] GitHub dosya listesi kesildi, bazı dosyalar güncellenmeyebilir.")

    kendi_yolu = os.path.abspath(__file__)
    yapilacak, script_girdisi = [], None
    for t in agac.get("tree", []):
        yol = t.get("path", "")
        if t.get("type") != "blob" or ".." in yol.split("/") or any(p.startswith(".") for p in yol.split("/")) or yol == "README.md":
            continue
        if yol == SCRIPT_GITHUB_ADI:
            hedef = kendi_yolu
        else:
            hedef = os.path.join(SCRIPT_DIR, *yol.split("/"))
        if os.path.isfile(hedef):
            if yol != SCRIPT_GITHUB_ADI and _seed_mi(yol):
                continue
            if os.path.getsize(hedef) == t.get("size"):
                with open(hedef, "rb") as f:
                    if _git_blob_sha(f.read()) == t.get("sha"):
                        continue
        girdi = (yol, hedef, t.get("sha"))
        if yol == SCRIPT_GITHUB_ADI:
            script_girdisi = girdi
        else:
            yapilacak.append(girdi)

    if not yapilacak and not script_girdisi:
        return
    toplam = len(yapilacak) + (1 if script_girdisi else 0)
    console.print(f"\n[bold cyan][GÜNCELLEME][/bold cyan] GitHub üzerinde yeni bir güncelleme mevcut! ([bold yellow]{toplam}[/bold yellow] dosya)")
    try:
        onay = Confirm.ask("[bold green]Yeni sürüme güncellemek istiyor musunuz?[/bold green]", default=True)
    except Exception:
        onay = True

    if not onay:
        console.print("[bold yellow][UYARI] Güncelleme atlandı. Eski sürümdesiniz, en kısa sürede güncellesen iyi olur![/bold yellow]\n")
        return

    console.print(f"[bold cyan][GÜNCELLEME][/bold cyan] {toplam} dosya indirilecek/güncellenecek...")
    basarili = 0
    for i, (yol, hedef, sha) in enumerate(yapilacak, 1):
        console.print(f"[dim]({i}/{toplam}) {escape(yol)}[/dim]")
        try:
            _guvenli_yaz(hedef, _github_indir(yol, sha))
            basarili += 1
        except Exception as e:
            console.print(f"[bold yellow][UYARI][/bold yellow] {escape(yol)} güncellenemedi: {escape(str(e))}")
    if script_girdisi:
        yol, hedef, sha = script_girdisi
        console.print(f"[dim]({toplam}/{toplam}) {escape(yol)} (programın kendisi)[/dim]")
        try:
            _guvenli_yaz(hedef, _github_indir(yol, sha))
            console.print("[bold green][GÜNCELLEME][/bold green] Program başarıyla güncellendi! Yeniden başlatılıyor...\n")
            os.execv(sys.executable, [sys.executable, hedef] + sys.argv[1:])
        except Exception as e:
            console.print(f"[bold yellow][UYARI][/bold yellow] Program dosyası güncellenemedi: {escape(str(e))}")
    if basarili:
        console.print(f"[bold green][GÜNCELLEME][/bold green] {basarili} dosya güncellendi. Program açılıyor...\n")


guncelleme_kontrol()


def api_anahtari_oku():
    yol = os.path.join(SCRIPT_DIR, "api.txt")
    try:
        with open(yol, encoding="utf-8-sig") as f:
            for satir in f:
                satir = satir.strip().strip("\"'")
                if satir:
                    return satir
    except FileNotFoundError:
        pass
    anahtar = os.environ.get("API_SPORTS_KEY", "").strip()
    if not anahtar:
        console.print(f"[bold yellow][UYARI][/bold yellow] api.txt bulunamadı ya da boş. Maç ve takım aramaları çalışmaz. API anahtarını şu dosyaya yaz: {yol}")
    return anahtar


def aerender_bul():
    varsayilan = "/Applications/Adobe After Effects 2026/aerender"
    if os.path.exists(varsayilan):
        return varsayilan
    adaylar = sorted(glob.glob("/Applications/Adobe After Effects*/aerender"), reverse=True)
    adaylar += sorted(glob.glob(r"C:\Program Files\Adobe\Adobe After Effects*\Support Files\aerender.exe"), reverse=True)
    return adaylar[0] if adaylar else varsayilan


def ses_cal():
    """İşlem bittiğinde script ile aynı klasördeki aeDone.mp3 dosyasını çalar."""
    ses_dosyasi = os.path.join(SCRIPT_DIR, "aeDone.mp3")
    if os.path.exists(ses_dosyasi):
        try:
            if platform.system() == "Darwin":
                subprocess.Popen(["afplay", ses_dosyasi], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif platform.system() == "Windows":
                os.startfile(ses_dosyasi)
        except Exception:
            pass


API_KEY = api_anahtari_oku()
HEADERS = {"x-apisports-key": API_KEY}
AERENDER_YOLU = aerender_bul()
KOMPOZISYON_ADI = "mainsahne"
CIKTI_SABLONU = "ygiido"

PROJE_ANA_KLASOR = os.path.join(SCRIPT_DIR, "Bfü Duyuru Projesi")
BASE_DIR = os.path.join(PROJE_ANA_KLASOR, "Assets")
AE_PROJE_YOLU = os.path.join(PROJE_ANA_KLASOR, "bfuDuyuru2027.aep")

if not os.path.isdir(BASE_DIR):
    console.print(f"[bold red][CRITICAL HATA][/bold red] Assets klasörü bulunamadı: {BASE_DIR}")
    console.print("[dim]İlk açılışta dosyalar GitHub'dan indirilir; internet bağlantını kontrol edip programı tekrar aç.[/dim]")
    raise SystemExit(1)
if not os.path.exists(AE_PROJE_YOLU):
    console.print(f"[bold yellow][UYARI][/bold yellow] After Effects projesi bulunamadı: {AE_PROJE_YOLU} (render çalışmaz)")

MEMLEKET_DIR = os.path.join(SCRIPT_DIR, "Memleket Duyuru")
MEM_ASSETS_DIR = os.path.join(MEMLEKET_DIR, "assets")
MEM_SUB_YOLU = os.path.join(MEMLEKET_DIR, "yayınSub.png")
MEM_JSON_YOLU = os.path.join(MEMLEKET_DIR, "mem_yayin_saati.json")
MEM_GORSELLER = ["cemBurhan1.png", "cemBurhan2.png", "cemBurhan3.png", "cemBurhan4.png"]
MEM_PROJE_ADAYLARI = ["memlketDuyAe.aep", "memleketDuyAe.aep"] 
MEM_KOMPOZISYON = "memSahne"
MEM_VARSAYILAN_SAAT = "22:00"
MEM_BASLIK = "BU AKŞAM" 

ALBERT_DIR = os.path.join(SCRIPT_DIR, "Albert")
ALBERT_PROJE_YOLU = os.path.join(ALBERT_DIR, "albert.aep")
ALBERT_JSON_YOLU = os.path.join(ALBERT_DIR, "albert.json")
ALBERT_KOMPOZISYON = "albertSahne"
ALBERT_VARSAYILAN_SAAT = "23:00" 

TMY_DIR = os.path.join(SCRIPT_DIR, "Tekmaç")
TMY_ASSETS_DIR = os.path.join(TMY_DIR, "Assets")
TMY_JSON_YOLU = os.path.join(TMY_ASSETS_DIR, "tmy.json")
TMY_GORSEL_YOLU = os.path.join(TMY_ASSETS_DIR, "tmyGorsel.png")
TMY_KOMPOZISYON = "tmySahne"
TMY_VARSAYILAN_SAAT = "21:00"
TMY_VIDEO_ADI = "tmyDuyuru.mp4"

FC_DIR = os.path.join(SCRIPT_DIR, "FC Kariyer Duyuru")
FC_ASSETS_DIR = os.path.join(FC_DIR, "Assets")
FC_PROJE_YOLU = os.path.join(FC_DIR, "fc27kariyerDuy.aep")
FC_KOMPOZISYON = "fc27sahne"
FC_LOGO_YOLU = os.path.join(FC_ASSETS_DIR, "takımlogo.png")
FC_TAKIM_DOSYASI = os.path.join(FC_DIR, "kariyer_takim.json") 
FC_VARSAYILAN_TAKIM = "Feyenoord"
FC_LOGO_BOYUT = (203, 195) 
FC_VIDEO_ADI = "fc27Duyuru.mp4"
MASAUSTU = os.path.expanduser("~/Desktop")

TURKCE_AYLAR = {
    1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
    7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"
}


def cikti_klasoru_al(program_adi, tarih=None):
    """Masaüstünde '26 Ekim_Program Adı' formatında klasör oluşturup yolunu döndürür."""
    if tarih:
        try:
            dt = datetime.strptime(tarih[:10], "%Y-%m-%d")
        except Exception:
            dt = datetime.now()
    else:
        dt = datetime.now()

    gun = dt.strftime("%d")
    ay = TURKCE_AYLAR.get(dt.month, dt.strftime("%B"))
    klasor_adi = f"{gun} {ay}_{program_adi}"
    hedef_klasor = os.path.join(MASAUSTU, klasor_adi)
    os.makedirs(hedef_klasor, exist_ok=True)
    return hedef_klasor


def masaustu_app_olustur():
    """macOS ortamında Masaüstüne çift tıklanabilir Tellal.app uygulamasını oluşturur ve özel ikonunu atar."""
    if platform.system() != "Darwin":
        return
    app_yolu = os.path.join(MASAUSTU, "Tellal.app")
    icns_kaynak = os.path.join(SCRIPT_DIR, "tellal.icns")
    png_kaynak = os.path.join(SCRIPT_DIR, "tellalicon.png")

    yeni_olusturuldu = False
    if not os.path.exists(app_yolu):
        try:
            script = f'tell application "Terminal" to do script "cd \\"{SCRIPT_DIR}\\" && python3 tellal.py"'
            subprocess.run(["osacompile", "-o", app_yolu, "-e", script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            yeni_olusturuldu = True
        except Exception:
            return

    # İkon dosyasını ve özel Finder rozetini güncelle
    try:
        icns_hedef = os.path.join(app_yolu, "Contents", "Resources", "applet.icns")
        assets_car = os.path.join(app_yolu, "Contents", "Resources", "Assets.car")
        if os.path.exists(assets_car):
            try:
                os.remove(assets_car)
            except Exception:
                pass
        if os.path.exists(icns_kaynak):
            shutil.copy2(icns_kaynak, icns_hedef)
            subprocess.run(["touch", app_yolu], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if os.path.exists(png_kaynak):
            swift_cmd = f'import Cocoa; if let img = NSImage(contentsOfFile: "{png_kaynak}") {{ NSWorkspace.shared.setIcon(img, forFile: "{app_yolu}", options: []) }}'
            subprocess.run(["swift", "-e", swift_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def ae_render_baslat(cikis_adi, proje_yolu=None, kompozisyon=None, hedef_klasor=None):
    proje_yolu = proje_yolu or AE_PROJE_YOLU
    kompozisyon = kompozisyon or KOMPOZISYON_ADI
    if not os.path.exists(AERENDER_YOLU):
        console.print(f"\n[bold red][CRITICAL HATA][/bold red] aerender motoru bulunamadı! Yol: {AERENDER_YOLU}")
        return

    hedef_dizin = hedef_klasor or MASAUSTU
    os.makedirs(hedef_dizin, exist_ok=True)
    cikis_yolu = os.path.join(hedef_dizin, cikis_adi)
    if os.path.exists(cikis_yolu):
        try:
            os.remove(cikis_yolu)
        except Exception as e:
            console.print(f"[bold yellow][UYARI][/bold yellow] Eski video silinemedi ({e}). Oynatıcıda açıksa kapatın.")

    console.print(Panel(f"[cyan]Proje:[/cyan] {os.path.basename(proje_yolu)}\n[cyan]Comp:[/cyan] {kompozisyon}\n[cyan]Hedef:[/cyan] {cikis_yolu}", title="[bold yellow]Render Başlatılıyor", expand=False))
    
    komut = [AERENDER_YOLU, "-project", proje_yolu, "-comp", kompozisyon, "-OMtemplate", CIKTI_SABLONU, "-output", cikis_yolu]
    
    try:
        process = subprocess.Popen(komut, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
        
        console.print("[dim]Render Motoru Logları (Sadece İlerleme):[/dim]")
        for satir in iter(process.stdout.readline, ''):
            if "PROGRESS:" in satir:
                console.print(f"[bold blue]{satir.strip()}[/bold blue]")
            elif any(k in satir.lower() for k in ("warning", "error")):
                console.print(f"[bold yellow]{escape(satir.strip())}[/bold yellow]")
                
        process.stdout.close()
        return_code = process.wait()
        
        if os.path.exists(cikis_yolu):
            console.print(f"\n[bold green][BAŞARILI][/bold green] Video kaydedildi: {cikis_yolu}")
            ses_cal()
        else:
            console.print(f"\n[bold red][HATA][/bold red] İşlem bitti ama dosya oluşmadı. Şablon veya Comp adı yanlış olabilir.")
            
    except Exception as e:
        console.print(f"\n[bold red][HATA][/bold red] Çökme yaşandı: {e}")


HAFTALIK_SEO_SABLON = """-Bermuda Futbol Uçgeni Canlı Yayın -

Bu Akşam Saat {saat}'{ek} Tosba Youtube, Twitch ve Kick Kanalında.

www.youtube.com/uykusuztosba
www.kick.com/uykusuztosba
www.twitch.com/uykusuztosba

#futbol #gündem #canlıyayın #süperlig #futbolgündemi
"""

CANLI_SEO_SABLON = """CANLI YAYINDAYIZ! {ev} - {dep} maçı esnasında sohbet edip pozisyonları tartışıyoruz. Yayın saati: {saat}
çayını kahveni hazırla chate gel! 👇

#{ev_tag} #{dep_tag} #CanlıYayın #MaçSohbeti #{lig_tag}
"""

MAC_SONU_SEO_SABLON = CANLI_SEO_SABLON.replace("maçı esnasında", "maçı sonrasında")
assert MAC_SONU_SEO_SABLON != CANLI_SEO_SABLON 


def saat_eki(saat):
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", saat.strip())
    if not m:
        return "de"
    saat_degeri, dakika = int(m.group(1)), int(m.group(2))
    n = saat_degeri if dakika == 0 else dakika
    birler = {1: "bir", 2: "iki", 3: "üç", 4: "dört", 5: "beş", 6: "altı", 7: "yedi", 8: "sekiz", 9: "dokuz"}
    onlar = {0: "sıfır", 10: "on", 20: "yirmi", 30: "otuz", 40: "kırk", 50: "elli"}
    kelime = birler[n % 10] if n % 10 else onlar[n]
    son_unlu = next(c for c in reversed(kelime) if c in "aıoueöüi")
    sert = kelime[-1] in "çfhkpsşt"
    return ("t" if sert else "d") + ("e" if son_unlu in "eiöü" else "a")


def hashtag_temizle(metin):
    """Metni hashtag uyumlu temizler (diyez olmadan)."""
    return re.sub(r"[\W_]+", "", metin)


def hashtag_yap(metin):
    """Metni başına # ekleyerek hashtag yapar."""
    temiz = hashtag_temizle(metin)
    return f"#{temiz}" if temiz else ""


def dosya_adi_temizle(ad):
    return re.sub(r'[\\/:*?"<>|]', "-", ad)


def seo_yaz(dosya_adi, icerik, video_adi=None, hedef_klasor=None):
    hedef_dizin = hedef_klasor or MASAUSTU
    os.makedirs(hedef_dizin, exist_ok=True)
    if video_adi and not os.path.exists(os.path.join(hedef_dizin, video_adi)):
        console.print(f"[bold yellow][UYARI][/bold yellow] {video_adi} bulunamadı ancak SEO metni yine de kaydediliyor.")
    try:
        yol = os.path.join(hedef_dizin, dosya_adi)
        with open(yol, "w", encoding="utf-8") as f:
            f.write(icerik)
        console.print(f"[bold green][BAŞARILI][/bold green] SEO metni kaydedildi: {yol}")
    except Exception as e:
        console.print(f"[bold red][HATA][/bold red] SEO metni yazılamadı: {e}")


ETIKET_NOTU = "-Cem'i Kadir'i Yağız'ı ve Yiğit'i etiketle."
LIG_MUZIK_ADLARI = {2: "Şampiyonlar Ligi", 3: "Europa Ligi", 848: "Konferans Ligi", 203: "Süper Lig", 5: "Uluslar Ligi"}


def planlama_saati(saat):
    try:
        t = datetime.strptime(saat.strip(), "%H:%M")
    except ValueError:
        return None, False
    onceki = t - timedelta(hours=4)
    return onceki.strftime("%H:%M"), onceki.day != t.day


def ekstra_not(saat, muzik_notu):
    plan, onceki_gun = planlama_saati(saat)
    if plan:
        gun = ", bir önceki gün" if onceki_gun else ""
        planla = f"-Yayın saatinden 4 saat önceye ({plan}{gun}) yayınla/planla"
    else:
        planla = "-Yayın saatinden 4 saat önceye yayınla/planla"
    return f"\n\n\n{planla}\n\n{ETIKET_NOTU}\n\n-Videoya {muzik_notu}\n"


def seo_haftalik_yaz(saat, video_adi, hedef_klasor=None):
    icerik = HAFTALIK_SEO_SABLON.format(saat=saat, ek=saat_eki(saat))
    icerik += ekstra_not(saat, "jenerik bir futbol veya trend bir müziği koy")
    seo_yaz("seoHaftalıkProgram.txt", icerik, video_adi, hedef_klasor=hedef_klasor)


def seo_canli_yaz(mac_verisi, saat, video_adi, mac_sonu=False, hedef_klasor=None):
    ev = mac_verisi['teams']['home']['name']
    dep = mac_verisi['teams']['away']['name']
    lig = mac_verisi['league']['name']
    sablon = MAC_SONU_SEO_SABLON if mac_sonu else CANLI_SEO_SABLON
    icerik = sablon.format(
        ev=ev, dep=dep, saat=saat,
        ev_tag=hashtag_temizle(ev), dep_tag=hashtag_temizle(dep), lig_tag=hashtag_temizle(lig),
    )
    lig_adi = LIG_MUZIK_ADLARI.get(mac_verisi['league']['id'], lig)
    icerik += ekstra_not(saat, f"{lig_adi} müziği koy")
    onek = "seoMaçSonu" if mac_sonu else "seoCanlısohbet"
    dosya = dosya_adi_temizle(f"{onek} {ev}_{dep}.txt")
    seo_yaz(dosya, icerik, video_adi, hedef_klasor=hedef_klasor)


PNG_IMZA = b"\x89PNG\r\n\x1a\n"
JENERIK_LOGO = "boş.png"  
BUGUN_YAZISI = "Bugün ise Enter a bas."


def logo_indir(url, hedef):
    r = requests.get(url, timeout=10)
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
            console.print(f"[bold cyan][BİLGİ][/bold cyan] Logo PNG değildi ({escape(tip)}), PNG'ye çevrildi: {os.path.basename(hedef)}")
        except Exception:
            raise ValueError(f"PNG değil ({tip}) ve PNG'ye çevrilemedi")

    with open(hedef, "wb") as f:
        f.write(veri)


def logo_hazirla(url, hedef, etiket):
    try:
        if not url:
            raise ValueError("logo adresi yok")
        logo_indir(url, hedef)
        return True
    except Exception as e:
        console.print(f"[bold yellow][UYARI][/bold yellow] {etiket} logosu indirilemedi ({escape(str(e))}). Jenerik logo kullanılıyor.")
        shutil.copyfile(os.path.join(BASE_DIR, JENERIK_LOGO), hedef)
        return False


def png_mi(dosya):
    try:
        with open(dosya, "rb") as f:
            return f.read(8) == PNG_IMZA
    except OSError:
        return False


def png_dogrula(dosyalar):
    sorunlu = 0
    for ad in dosyalar:
        hedef = os.path.join(BASE_DIR, ad)
        if not os.path.exists(hedef):
            console.print(f"[bold yellow][UYARI][/bold yellow] {ad} bulunamadı.")
            sorunlu += 1
            continue
        if png_mi(hedef):
            continue
        try:
            from PIL import Image
            with Image.open(hedef) as img:
                donusmus = img.convert("RGBA")
            donusmus.save(hedef, format="PNG")
            console.print(f"[bold cyan][BİLGİ][/bold cyan] {ad} PNG değildi, PNG'ye çevrildi.")
        except ImportError:
            console.print(f"[bold yellow][UYARI][/bold yellow] {ad} PNG değil ve Pillow yüklü değil (pip3 install pillow). Render hata verebilir.")
            sorunlu += 1
        except Exception as e:
            console.print(f"[bold yellow][UYARI][/bold yellow] {ad} PNG değil ve çevrilemedi ({escape(str(e))}). Render hata verebilir.")
            sorunlu += 1

    if sorunlu == 0:
        console.print(f"[bold green][KONTROL][/bold green] {len(dosyalar)} görselin hepsi geçerli PNG.")


UCRETSIZ_SEZONLAR = range(2022, 2025)
HEPSI_LIG_IDLERI = [2, 3, 848, 203, 5]


def sezon_hesapla(tarih):
    yil, ay = int(tarih[:4]), int(tarih[5:7])
    return str(yil if ay >= 7 else yil - 1)


def api_maclar(params):
    r = requests.get("https://v3.football.api-sports.io/fixtures", headers=HEADERS, params=params, timeout=15)
    j = r.json()
    if j.get("errors"):
        console.print(f"[bold red][API HATASI][/bold red] {escape(str(j['errors']))}")
    kalan = r.headers.get("x-ratelimit-requests-remaining")
    if kalan is not None:
        console.print(f"[dim]Kalan günlük istek: {kalan}[/dim]")
    return j.get("response", [])


def uykusuz_tosba_menu():
    while True:
        console.print("\n")
        menu = """[bold cyan]1.[/bold cyan] Haftalık Program
[bold cyan]2.[/bold cyan] Canlı Maç Sohbeti
[bold cyan]3.[/bold cyan] Maç Sonu
[bold cyan]4.[/bold cyan] Tek Maçtan Yatanlar
[bold cyan]5.[/bold cyan] FC27 Kariyer
[bold cyan]6.[/bold cyan] Geri"""
        console.print(Panel(menu, title=f"[bold yellow]🐢 Uykusuz Tosba Duyuru Sistemi [cyan]v{SURUM}[/cyan]", expand=False))
    
        secim = Prompt.ask("[bold green]İşlem seçin[/bold green]", choices=["1", "2", "3", "4", "5", "6"])

        if secim == "6":
            break

        try:
            if secim == "1":
                saat = saat_al("Yayın Saat kaçta? (Örn: 21:00)")
            
                json_yolu = os.path.join(BASE_DIR, "yayin_saati.json")
                with open(json_yolu, "w", encoding="utf-8") as f:
                    json.dump({"baslik": f"Bu Aksam {saat}"}, f, ensure_ascii=False)
                
                csv_yolu = os.path.join(BASE_DIR, "yayin_saati.csv")
                with open(csv_yolu, "wb") as f:
                    f.write(f'baslik\n"Bu Aksam {saat}"'.encode("utf-8"))
                
                shutil.copyfile(os.path.join(BASE_DIR, "Borders", "superlig.png"), os.path.join(BASE_DIR, "cerceve.png"))
                shutil.copyfile(os.path.join(BASE_DIR, "arkaPlanlar", "superligback.png"), os.path.join(BASE_DIR, "arkaPlan.png"))
                shutil.copyfile(os.path.join(BASE_DIR, "alt", "haftalık futbol programı.png"), os.path.join(BASE_DIR, "konu.png"))
                shutil.copyfile(os.path.join(BASE_DIR, "kafalar", "haftalık.png"), os.path.join(BASE_DIR, "kafa.png"))
                shutil.copyfile(os.path.join(BASE_DIR, "boş.png"), os.path.join(BASE_DIR, "evTakım.png"))
                shutil.copyfile(os.path.join(BASE_DIR, "boş.png"), os.path.join(BASE_DIR, "depTakım.png"))
                shutil.copyfile(os.path.join(BASE_DIR, "logo.png"), os.path.join(BASE_DIR, "VS.png"))
            
                klasor = cikti_klasoru_al("Haftalık Program")
                if Confirm.ask("[bold yellow]Dosyalar güncellendi. Render başlatılsın mı?[/bold yellow]"):
                    ae_render_baslat("Haftalik_Program_Duyurusu.mp4", hedef_klasor=klasor)
                    seo_haftalik_yaz(saat, "Haftalik_Program_Duyurusu.mp4", hedef_klasor=klasor)
                else:
                    console.print("[dim]Render atlandı.[/dim]")

            elif secim in ("2", "3"):
                mac_sonu = secim == "3" 
                while True:
                    tarih_girdisi = Prompt.ask("[bold cyan]Tarih (YYYY-MM-DD)[/bold cyan]", default=BUGUN_YAZISI)
                    girdi_temiz = tarih_girdisi.strip().lower()
                    if girdi_temiz in ("", BUGUN_YAZISI.lower(), "bugün", "bugun"):
                        tarih = datetime.now(timezone(timedelta(hours=3))).strftime("%Y-%m-%d")
                        break
                    elif re.fullmatch(r"\d{4}-\d{2}-\d{2}", tarih_girdisi.strip()):
                        tarih = tarih_girdisi.strip()
                        break
                    else:
                        console.print("[bold yellow][UYARI][/bold yellow] Tarihi YYYY-MM-DD biçiminde gir (Örn: 2026-10-25) veya Enter'a bas.")
                
                sezon_yili = sezon_hesapla(tarih)
                sadece_hepsi = int(sezon_yili) not in UCRETSIZ_SEZONLAR

                if sadece_hepsi:
                    lig_menu = "[6] Hepsi (Bu 5 Lig)"
                    secenekler, varsayilan = ["6"], "6"
                else:
                    lig_menu = """[1] Şampiyonlar Ligi  [2] Europa Ligi  [3] Konferans Ligi
[4] Süper Lig        [5] Uluslar Ligi [6] Hepsi (Bu 5 Lig)"""
                    secenekler, varsayilan = ["1", "2", "3", "4", "5", "6"], None

                console.print(Panel(lig_menu, title="Turnuva Seçimi", expand=False))
                turnuva_secim = Prompt.ask("[bold green]Turnuva seçin[/bold green]", choices=secenekler, default=varsayilan) if varsayilan else Prompt.ask("[bold green]Turnuva seçin[/bold green]", choices=secenekler)

                maclar = []
                with console.status("[bold cyan]API'den maçlar çekiliyor...[/bold cyan]"):
                    if turnuva_secim == "6":
                        tum = api_maclar({"date": tarih, "timezone": "Europe/Istanbul"})
                        maclar = [m for m in tum if m['league']['id'] in HEPSI_LIG_IDLERI]
                    else:
                        lig_map = {"1": 2, "2": 3, "3": 848, "4": 203, "5": 5}
                        maclar = api_maclar({"date": tarih, "league": lig_map[turnuva_secim], "season": sezon_yili, "timezone": "Europe/Istanbul"})

                if not maclar:
                    console.print(f"[bold red][UYARI][/bold red] {tarih} tarihinde maç bulunamadı.")
                    continue
                
                table = Table(title=f"[bold magenta]--- {tarih} Tarihli Maçlar ---[/bold magenta]")
                table.add_column("Sıra", justify="right", style="cyan", no_wrap=True)
                table.add_column("ID", style="magenta")
                table.add_column("Ev Sahibi", style="green")
                table.add_column("Deplasman", style="red")
                table.add_column("Saat", style="yellow")
                table.add_column("Lig", style="blue")

                sira_to_id = {}
                id_list = []
            
                for idx, m in enumerate(maclar, start=1):
                    f_id = str(m['fixture']['id'])
                    sira_to_id[str(idx)] = f_id
                    id_list.append(f_id)
                
                    utc_time = datetime.strptime(m['fixture']['date'], "%Y-%m-%dT%H:%M:%S%z")
                    tr_time = utc_time.astimezone(timezone(timedelta(hours=3)))
                    mac_saati_str = tr_time.strftime("%H:%M")
                
                    table.add_row(str(idx), f_id, m['teams']['home']['name'], m['teams']['away']['name'], mac_saati_str, m['league']['name'])
                
                console.print(table)
            
                girdi = Prompt.ask("[bold cyan]Sıra No veya Maç ID'si girin[/bold cyan]").strip()
            
                if girdi in sira_to_id and girdi in id_list:
                    girdi = Prompt.ask("[bold red][DİKKAT][/bold red] Girdiğiniz sayı hem Sıra No hem ID ile eşleşiyor. Tam Maç ID'sini tekrar girin").strip()
                    secilen_id = girdi
                else:
                    secilen_id = sira_to_id.get(girdi, girdi)
            
                mac_verisi = next((m for m in maclar if str(m['fixture']['id']) == secilen_id), None)
            
                if not mac_verisi:
                    console.print("[bold red][UYARI][/bold red] Maç bulunamadı.")
                    continue
                    
                tr_time = datetime.strptime(mac_verisi['fixture']['date'], "%Y-%m-%dT%H:%M:%S%z").astimezone(timezone(timedelta(hours=3)))

                if mac_sonu:
                    nihai_saat = saat_al("Yayın Saati kaçta? (Örn: 23:45)")
                else:
                    yayin_saati_oto = (tr_time - timedelta(minutes=15)).strftime("%H:%M")
                    nihai_saat = saat_al(f"Yayın Saati ({yayin_saati_oto} olarak hesaplandı). Farklı bir saat girmek ister misiniz?", default=yayin_saati_oto)
            
                json_yolu = os.path.join(BASE_DIR, "yayin_saati.json")
                with open(json_yolu, "w", encoding="utf-8") as f:
                    json.dump({"baslik": f"Bu Aksam {nihai_saat}"}, f, ensure_ascii=False)
                
                csv_yolu = os.path.join(BASE_DIR, "yayin_saati.csv")
                with open(csv_yolu, "wb") as f:
                    f.write(f'baslik\n"Bu Aksam {nihai_saat}"'.encode("utf-8"))
                
                lig_id = mac_verisi['league']['id']
                b_map = {2: "cl.png", 3: "europa.png", 848: "conferance.png", 203: "superlig.png", 5: "uluslarLigi.png"}
                bg_map = {2: "clback.png", 3: "europaback.png", 848: "confBack.png", 203: "superligback.png", 5: "ulusArka.png"}
            
                shutil.copyfile(os.path.join(BASE_DIR, "Borders", b_map.get(lig_id, "superlig.png")), os.path.join(BASE_DIR, "cerceve.png"))
                shutil.copyfile(os.path.join(BASE_DIR, "arkaPlanlar", bg_map.get(lig_id, "superligback.png")), os.path.join(BASE_DIR, "arkaPlan.png"))
                shutil.copyfile(os.path.join(BASE_DIR, "alt", "maç sonu.png" if mac_sonu else "canlı maç sohbetlerİ.png"), os.path.join(BASE_DIR, "konu.png"))
                shutil.copyfile(os.path.join(BASE_DIR, "kafalar", "millitakım.png" if lig_id == 5 else "haftalık.png"), os.path.join(BASE_DIR, "kafa.png"))
                shutil.copyfile(os.path.join(BASE_DIR, "dosyalar", "VS.png"), os.path.join(BASE_DIR, "VS.png"))
            
                logo_hazirla(mac_verisi['teams']['home'].get('logo'), os.path.join(BASE_DIR, "evTakım.png"), "Ev sahibi")
                logo_hazirla(mac_verisi['teams']['away'].get('logo'), os.path.join(BASE_DIR, "depTakım.png"), "Deplasman")
                png_dogrula(["cerceve.png", "arkaPlan.png", "konu.png", "kafa.png", "VS.png", "evTakım.png", "depTakım.png"])

                prog_adi = "Maç Sonu" if mac_sonu else "Canlı Maç Sohbeti"
                klasor = cikti_klasoru_al(prog_adi, tarih=tarih)
                if Confirm.ask("[bold yellow]Dosyalar güncellendi. Render başlatılsın mı?[/bold yellow]"):
                    video_adi = f"{'Mac_Sonu' if mac_sonu else 'Mac_Sohbeti'}_{nihai_saat.replace(':', '')}.mp4"
                    ae_render_baslat(video_adi, hedef_klasor=klasor)
                    seo_canli_yaz(mac_verisi, nihai_saat, video_adi, mac_sonu=mac_sonu, hedef_klasor=klasor)
                else:
                    console.print("[dim]Render atlandı.[/dim]")

            elif secim == "4":
                tek_mac_yatanlar_yap()
            elif secim == "5":
                fc27_kariyer_yap()

        except Exception as e:
            console.print(f"\n[bold red][HATA][/bold red] İşlem sırasında sorun oluştu: {e}")


def saat_al(mesaj="Yayın Saati kaçta? (Örn: 21:00)", varsayilan=None, default=None):
    varsayilan = default if default is not None else varsayilan
    while True:
        if varsayilan:
            saat = Prompt.ask(
                f"[bold cyan]{mesaj}[/bold cyan] (Boş bırakırsanız {varsayilan} kullanılır)",
                default=varsayilan,
            ).strip()
        else:
            saat = Prompt.ask(f"[bold cyan]{mesaj}[/bold cyan]").strip()
        if re.fullmatch(r"\d{1,2}:\d{2}", saat):
            return saat
        console.print("[bold yellow][UYARI][/bold yellow] Saati SS:DD biçiminde gir (Örn: 21:00).")


def saat_oner_al(varsayilan):
    return saat_al(f"Yayın Saati ({varsayilan} olarak önerildi). Farklı bir saat girmek ister misiniz?", default=varsayilan)


def mem_saat_al():
    return saat_oner_al(MEM_VARSAYILAN_SAAT)


MEM_SEO_SABLON = """“Yok artık!” dedirten anları, sokağın filtresiz gerçekleri... Cem ve Burhan’la kaos, kahkaha ve dram başlıyor! 🇹🇷🎬

“Bu olsa olsa ancak bizim memlekette olur” dediğimiz ne varsa, bu akşam {saat} YouTube, Kick ve Twitch ortak yayınında masada!

youtube.com/radiomocas
kick.com/uykusuztosba
twitch.com/radiomocas

#FiltresizMemleketHavası #kaos #sohbet #mizah #CanlıYayın
"""


def seo_memleket_yaz(saat, video_adi):
    icerik = MEM_SEO_SABLON.format(saat=saat)
    plan, onceki_gun = planlama_saati(saat)
    if plan:
        gun = " (bir önceki gün)" if onceki_gun else ""
        planla = f"-Bu videoyu {plan} saatine planla{gun}"
    else:
        planla = "-Bu videoyu yayın saatinden 4 saat önceye planla"
    icerik += f"\n\n\n-Cem ve Burhan'ı etiketle\n\n-Videoya cyberpunk türü veya Cem'in şarkılarından birini koy\n\n{planla}\n"
    seo_yaz("seo_Filtresiz_memleket_Duyuru.txt", icerik, video_adi)


def memleket_duyuru_yap():
    saat = mem_saat_al()

    mevcut = [g for g in MEM_GORSELLER if os.path.exists(os.path.join(MEM_ASSETS_DIR, g))]
    if not mevcut:
        console.print(f"[bold red][HATA][/bold red] {MEM_ASSETS_DIR} içinde cemBurhan1-4.png bulunamadı.")
        return
    secilen = random.choice(mevcut)
    shutil.copyfile(os.path.join(MEM_ASSETS_DIR, secilen), MEM_SUB_YOLU)
    with open(MEM_SUB_YOLU, "rb") as f:
        if not f.read(8).startswith(PNG_IMZA):
            console.print(f"[bold yellow][UYARI][/bold yellow] {secilen} gerçek bir PNG değil, render hata verebilir.")
    console.print(f"[bold cyan][BİLGİ][/bold cyan] Seçilen görsel: {secilen} -> yayınSub.png")

    with open(MEM_JSON_YOLU, "w", encoding="utf-8") as f:
        json.dump({"baslik": MEM_BASLIK, "saat": saat}, f, ensure_ascii=False)

    proje = next((os.path.join(MEMLEKET_DIR, a) for a in MEM_PROJE_ADAYLARI if os.path.exists(os.path.join(MEMLEKET_DIR, a))), None)
    if not proje:
        console.print(f"[bold red][HATA][/bold red] After Effects projesi bulunamadı: {os.path.join(MEMLEKET_DIR, MEM_PROJE_ADAYLARI[0])}")
        return

    klasor = cikti_klasoru_al("Memleket Havası")
    if Confirm.ask("[bold yellow]Dosyalar güncellendi. Render başlatılsın mı?[/bold yellow]"):
        video_adi = f"Memleket_Havasi_{saat.replace(':', '')}.mp4"
        ae_render_baslat(video_adi, proje_yolu=proje, kompozisyon=MEM_KOMPOZISYON, hedef_klasor=klasor)
        seo_memleket_yaz(saat, video_adi, hedef_klasor=klasor)
    else:
        console.print("[dim]Render atlandı.[/dim]")


ALBERT_SEO_SABLON = """-Albert ve Cem- Canlı Yayın -

Dikkat edin içerisi ağır dram içerir.Yayın tekrarı yoktur.Kaçıracak olanlar şimdiden üzülebilir.(+18)

#albertvecem #canlıyayın #sohbet #efkar #dram

cemi etiketle

{planla}saatine planla

video müzikli ama istersen müziği iptal edip cemin müziklerinden birini koyabilirsin.
-
"""


def seo_albert_yaz(saat, video_adi, hedef_klasor=None):
    plan, onceki_gun = planlama_saati(saat)
    if plan:
        gun = " (bir önceki gün) " if onceki_gun else " "
        plan_metni = f"{plan}{gun}"
    else:
        plan_metni = "yayın saatinden 4 saat önce "
    icerik = ALBERT_SEO_SABLON.format(planla=plan_metni)
    seo_yaz("albertSeo.txt", icerik, video_adi, hedef_klasor=hedef_klasor)


def albert_ve_cem_yap():
    if not os.path.isdir(ALBERT_DIR):
        console.print(f"[bold red][HATA][/bold red] Albert klasörü bulunamadı: {ALBERT_DIR}")
        return
    if not os.path.exists(ALBERT_PROJE_YOLU):
        console.print(f"[bold red][HATA][/bold red] After Effects projesi bulunamadı: {ALBERT_PROJE_YOLU}")
        return

    saat = saat_oner_al(ALBERT_VARSAYILAN_SAAT)

    with open(ALBERT_JSON_YOLU, "w", encoding="utf-8") as f:
        json.dump({"baslik": "BU AKŞAM", "saat": saat}, f, ensure_ascii=False)

    console.print(f"[bold cyan][BİLGİ][/bold cyan] albert.json güncellendi: BU AKŞAM {saat}")

    klasor = cikti_klasoru_al("Albert ve Cem")
    if Confirm.ask("[bold yellow]Dosyalar güncellendi. Render başlatılsın mı?[/bold yellow]"):
        video_adi = f"Albert_ve_Cem_{saat.replace(':', '')}.mp4"
        ae_render_baslat(video_adi, proje_yolu=ALBERT_PROJE_YOLU, kompozisyon=ALBERT_KOMPOZISYON, hedef_klasor=klasor)
        seo_albert_yaz(saat, video_adi, hedef_klasor=klasor)
    else:
        console.print("[dim]Render atlandı.[/dim]")


TMY_SEO_SABLON = """{kimden} iddaa tahminleri ve kupon önerileri yayında! Videodaki maçlar ve oranlar.

Oranlar maç saatine kadar değişebilir.
📌 Not: Bu videoda yer alan değerlendirmeler tamamen kişisel futbol ve spor yorumlarımızdan ibarettir. Kesinlik taşımaz ve herhangi bir tavsiye niteliği bulundurmaz.

#iddaa #tahmin {etiketler}
"""





def tmy_proje_bul():
    try:
        adaylar = sorted(f for f in os.listdir(TMY_DIR) if f.lower().endswith(".aep"))
    except FileNotFoundError:
        return None
    havuz = [f for f in adaylar if "tmy" in f.lower()] or adaylar
    if not havuz:
        return None
    if len(havuz) > 1:
        console.print(f"[bold cyan][BİLGİ][/bold cyan] Tekmaç klasöründe birden fazla .aep var, {havuz[0]} kullanılıyor.")
    return os.path.join(TMY_DIR, havuz[0])


def tmy_json_guncelle(saat):
    try:
        with open(TMY_JSON_YOLU, encoding="utf-8") as f:
            veri = json.load(f)
        if not isinstance(veri, dict):
            veri = {}
    except (FileNotFoundError, json.JSONDecodeError):
        veri = {}
    eski = veri.get("baslik")
    if isinstance(eski, str) and re.search(r"\d{1,2}:\d{2}", eski):
        veri["baslik"] = re.sub(r"\d{1,2}:\d{2}", lambda m: saat, eski, count=1)
    else:
        veri["baslik"] = f"Bu Aksam {saat}"
    with open(TMY_JSON_YOLU, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False)


def takim_hashtagleri_al():
    console.print("[bold cyan]O haftanın maçlarıyla ilgili 3 takım adı gir (hashtag olacak). Bilmiyorsan önce ekibe sor.[/bold cyan]")
    etiketler = []
    while len(etiketler) < 3:
        tag = hashtag_yap(Prompt.ask(f"[bold cyan]{len(etiketler) + 1}. takım[/bold cyan]").strip())
        if not tag:
            console.print("[bold yellow][UYARI][/bold yellow] Takım adı boş olamaz.")
            continue
        etiketler.append(tag)
    return etiketler


def seo_tmy_yaz(saat, kayhan_var, etiketler, video_adi, hedef_klasor=None):
    kimden = "Cem Yıldırım ve Kayhan Alkay'dan" if kayhan_var else "Cem Yıldırım'dan"
    icerik = TMY_SEO_SABLON.format(kimden=kimden, etiketler=" ".join(etiketler))
    plan, onceki_gun = planlama_saati(saat)
    if plan:
        gun = " (bir önceki gün)" if onceki_gun else ""
        paylas = f"-{plan} saatinde paylaş{gun}"
    else:
        paylas = "-Yayın saatinden 4 saat önce paylaş"
    etiket_notu = "-Kayhan ve Cem'i etiketle" if kayhan_var else "-Cem'i etiketle"
    icerik += f"\n\n\n{etiket_notu}\n\n{paylas}\n\n-Videoya trend, enerjik bir müzik koy\n"
    seo_yaz("tmyDuyuru.txt", icerik, video_adi, hedef_klasor=hedef_klasor)


def tek_mac_yatanlar_yap():
    if not os.path.isdir(TMY_ASSETS_DIR):
        console.print(f"[bold red][HATA][/bold red] Assets klasörü bulunamadı: {TMY_ASSETS_DIR}")
        return
    proje = tmy_proje_bul()
    if not proje:
        console.print(f"[bold red][HATA][/bold red] {TMY_DIR} içinde After Effects projesi (.aep) bulunamadı.")
        return

    saat = saat_oner_al(TMY_VARSAYILAN_SAAT)

    kayhan_var = Confirm.ask("[bold cyan]Kayhan Abi var mı?[/bold cyan]")
    kaynak = "kayhan.png" if kayhan_var else "cem.png"
    kaynak_yol = os.path.join(TMY_ASSETS_DIR, kaynak)
    if not os.path.exists(kaynak_yol):
        console.print(f"[bold red][HATA][/bold red] {kaynak_yol} bulunamadı.")
        return
    shutil.copyfile(kaynak_yol, TMY_GORSEL_YOLU)
    with open(TMY_GORSEL_YOLU, "rb") as f:
        if not f.read(8).startswith(PNG_IMZA):
            console.print(f"[bold yellow][UYARI][/bold yellow] {kaynak} gerçek bir PNG değil, render hata verebilir.")
    console.print(f"[bold cyan][BİLGİ][/bold cyan] {kaynak} -> tmyGorsel.png")

    etiketler = takim_hashtagleri_al()
    tmy_json_guncelle(saat)

    klasor = cikti_klasoru_al("Tek Maçtan Yatanlar")
    if Confirm.ask("[bold yellow]Dosyalar güncellendi. Render başlatılsın mı?[/bold yellow]"):
        ae_render_baslat(TMY_VIDEO_ADI, proje_yolu=proje, kompozisyon=TMY_KOMPOZISYON, hedef_klasor=klasor)
        seo_tmy_yaz(saat, kayhan_var, etiketler, TMY_VIDEO_ADI, hedef_klasor=klasor)
    else:
        console.print("[dim]Render atlandı.[/dim]")


FC27_SEO_SABLON = """Fc27 {takim} kariyeri canlı yayın başladı!

📺 {takim} kariyerimizi SADECE YouTube'da!
👉 YouTube: Uykusuz Tosba (/uykusuztosba)

#FC27 {etiket} #KariyerModu #UykusuzTosba #EAFC27
"""


def ascii_norm(metin):
    metin = metin.replace("İ", "I").replace("ı", "i")
    metin = unicodedata.normalize("NFKD", metin)
    metin = "".join(c for c in metin if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]", "", metin.lower()).strip()


def fc_takim_oku():
    try:
        with open(FC_TAKIM_DOSYASI, encoding="utf-8") as f:
            ad = json.load(f).get("takim")
        if isinstance(ad, str) and ad.strip():
            return ad.strip()
    except (FileNotFoundError, json.JSONDecodeError, AttributeError):
        pass
    fc_takim_yaz(FC_VARSAYILAN_TAKIM)
    return FC_VARSAYILAN_TAKIM


def fc_takim_yaz(ad):
    with open(FC_TAKIM_DOSYASI, "w", encoding="utf-8") as f:
        json.dump({"takim": ad}, f, ensure_ascii=False)


def fc_takim_ara(giris):
    tam = ascii_norm(giris)
    kelimeler = tam.split()
    if len(kelimeler) > 1 and kelimeler[0] in ("fc", "ac", "as", "sk", "fk"):
        tam = " ".join(kelimeler[1:])
    onek = tam[:4].strip() if len(tam) >= 4 else tam
    if len(onek) < 3:
        return []
    r = requests.get("https://v3.football.api-sports.io/teams", headers=HEADERS, params={"search": onek}, timeout=15)
    j = r.json()
    if j.get("errors"):
        console.print(f"[bold red][API HATASI][/bold red] {escape(str(j['errors']))}")
    sonuc = []
    for item in j.get("response", []):
        t = item.get("team", {})
        ad = t.get("name") or ""
        n = ascii_norm(ad)
        if onek not in n:
            continue
        sira = 0 if n.startswith(tam) else 1 if tam in n else 2 if n.startswith(onek) else 3
        sonuc.append((sira, bool(t.get("national")), ad, {"ad": ad, "ulke": t.get("country") or "", "milli": bool(t.get("national")), "logo": t.get("logo")}))
    sonuc.sort(key=lambda x: (x[0], x[1], x[2]))
    return [x[3] for x in sonuc[:6]]


def fc_takim_sec():
    while True:
        giris = Prompt.ask("[bold cyan]Hangi takımın kariyerini yapıyor?[/bold cyan] (Boş bırakırsan vazgeçilir)", default="", show_default=False).strip()
        if not giris:
            return None
        if len(ascii_norm(giris)) < 3:
            console.print("[bold yellow][UYARI][/bold yellow] En az ilk 3 harfi doğru yazmalısın.")
            continue
        adaylar = fc_takim_ara(giris)
        if not adaylar:
            console.print("[bold yellow][UYARI][/bold yellow] Eşleşen takım bulunamadı, ilk harfleri kontrol edip tekrar dene.")
            continue
        for i, a in enumerate(adaylar, 1):
            milli = " (Milli takım)" if a["milli"] else ""
            console.print(f"  [bold cyan]{i}.[/bold cyan] {escape(a['ad'])} [dim]- {escape(a['ulke'])}{milli}[/dim]")
        sec = Prompt.ask("[bold green]Numara seç[/bold green] (0 = tekrar dene)", choices=[str(i) for i in range(len(adaylar) + 1)], default="1")
        if sec != "0":
            return adaylar[int(sec) - 1]


def fc_logo_hazirla(url):
    if not url:
        raise ValueError("API logo adresi vermedi")
    try:
        from PIL import Image
    except ImportError:
        raise ValueError("Pillow yüklü değil (pip3 install pillow)")
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    img = Image.open(io.BytesIO(r.content)).convert("RGBA")
    w, h = FC_LOGO_BOYUT
    oran = min(w / img.width, h / img.height)
    yeni = img.resize((max(1, round(img.width * oran)), max(1, round(img.height * oran))), Image.LANCZOS)
    tuval = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    tuval.paste(yeni, ((w - yeni.width) // 2, (h - yeni.height) // 2), yeni)
    tuval.save(FC_LOGO_YOLU, format="PNG")


def fc27_txt_yaz(takim, hedef_klasor=None):
    icerik = FC27_SEO_SABLON.format(takim=takim, etiket=hashtag_yap(takim))
    icerik += "\n\n\n-Cem'i etiketle\n\n-FC27 soundtracklerinden bir müzik seç\n"
    seo_yaz("fc27Duyuru.txt", icerik, hedef_klasor=hedef_klasor)


def fc27_kariyer_yap():
    if not os.path.isdir(FC_ASSETS_DIR):
        console.print(f"[bold red][HATA][/bold red] Assets klasörü bulunamadı: {FC_ASSETS_DIR}")
        return
    if not os.path.exists(FC_PROJE_YOLU):
        console.print(f"[bold red][HATA][/bold red] After Effects projesi bulunamadı: {FC_PROJE_YOLU}")
        return

    kayitli = fc_takim_oku()
    if Confirm.ask(f"[bold cyan]Halen {escape(kayitli)} kariyeri mi yapıyor?[/bold cyan]", default=True):
        takim = kayitli
        if not os.path.exists(FC_LOGO_YOLU):
            console.print(f"[bold red][HATA][/bold red] {FC_LOGO_YOLU} bulunamadı. 'Hayır' deyip takımı yeniden girersen logo indirilir.")
            return
    else:
        secilen = fc_takim_sec()
        if not secilen:
            console.print("[dim]Vazgeçildi.[/dim]")
            return
        try:
            fc_logo_hazirla(secilen["logo"])
            fc_takim_yaz(secilen["ad"])
            takim = secilen["ad"]
            console.print(f"[bold cyan][BİLGİ][/bold cyan] {escape(takim)} seçildi, logo {FC_LOGO_BOYUT[0]}x{FC_LOGO_BOYUT[1]} olarak takımlogo.png'ye kaydedildi.")
        except Exception as e:
            console.print(f"[bold red][HATA][/bold red] Logo indirilemedi/işlenemedi: {e}")
            return

    klasor = cikti_klasoru_al("FC27 Kariyer")
    console.print("[bold yellow][NOT][/bold yellow] Bu yayın duyurusu, yayın başladıktan sonra yapılır.")
    if Confirm.ask("[bold yellow]Render başlatılsın mı?[/bold yellow]"):
        fc27_txt_yaz(takim, hedef_klasor=klasor)
        ae_render_baslat(FC_VIDEO_ADI, proje_yolu=FC_PROJE_YOLU, kompozisyon=FC_KOMPOZISYON, hedef_klasor=klasor)
    else:
        console.print("[dim]Render atlandı.[/dim]")


def radio_mocas_menu():
    while True:
        console.print("\n")
        menu = """[bold cyan]1.[/bold cyan] Filtresiz Memleket Havası
[bold cyan]2.[/bold cyan] Albert ve Cem
[bold cyan]3.[/bold cyan] Mocas Bey ve Radyosu
[bold cyan]4.[/bold cyan] Aklımdaki Filmler
[bold cyan]5.[/bold cyan] Geri"""
        console.print(Panel(menu, title=f"[bold yellow]📻 Radio Mocas Duyuru Sistemi [cyan]v{SURUM}[/cyan]", expand=False))

        secim = Prompt.ask("[bold green]İşlem seçin[/bold green]", choices=["1", "2", "3", "4", "5"])
        if secim == "5":
            break
        if secim == "1":
            try:
                memleket_duyuru_yap()
            except Exception as e:
                console.print(f"\n[bold red][HATA][/bold red] İşlem sırasında sorun oluştu: {e}")
        elif secim == "2":
            try:
                albert_ve_cem_yap()
            except Exception as e:
                console.print(f"\n[bold red][HATA][/bold red] İşlem sırasında sorun oluştu: {e}")
        else:
            console.print("[bold yellow]Yapım aşamasında...[/bold yellow]")


def banner_yazdir():
    """Program başlığındaki şık ASCII art Tellal logosunu ve kanal bilgilerini yazdırır."""
    art = [
        (r" _____     _ _       _ ", r""),
        (r"|_   _|___| | | __ _| |", r"  [bold cyan]/uykusuztosba[/bold cyan]   [bold magenta]/radiomocas[/bold magenta]"),
        (r"  | |/ _ \ | |/ _` | |", f"  [dim]Duyuru Sistemi[/dim] [bold yellow]v{SURUM}[/bold yellow]"),
        (r"  | |  __/ | | (_| | |", r""),
        (r"  |_|\___|_|_|\__,_|_|", r""),
    ]
    console.print()
    for sol, sag in art:
        console.print(f"[bold green]{sol:<24}[/bold green]{sag}")
    console.print()


# =====================================================================
# ANA MENÜ
# =====================================================================
def ana_menu():
    while True:
        banner_yazdir()
        menu = """[bold cyan]1.[/bold cyan] Uykusuz Tosba Duyuru Sistemi
[bold cyan]2.[/bold cyan] Radio Mocas Duyuru Sistemi
[bold cyan]3.[/bold cyan] Çıkış"""
        console.print(Panel(menu, title=f"[bold yellow]▶️ Youtube Duyuru Sistemi [cyan]v{SURUM}[/cyan]", expand=False))

        ana_secim = Prompt.ask("[bold green]Sistem seçin[/bold green]", choices=["1", "2", "3"])

        if ana_secim == "3":
            console.print("[bold yellow]Çıkış yapılıyor...[/bold yellow]")
            break
        elif ana_secim == "1":
            uykusuz_tosba_menu()
        elif ana_secim == "2":
            radio_mocas_menu()


if __name__ == "__main__":
    masaustu_app_olustur()
    yenilikleri_goster()
    ana_menu()

