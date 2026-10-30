
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
try:
    import tty
    import termios
except ImportError:
    tty = None
    termios = None
from urllib.parse import quote
from datetime import datetime, timedelta, timezone
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.markup import escape

console = Console()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

SURUM = "1.4.8"
SURUM_NOTLARI = {
    "1.4.8": [
        "Marka ve Kimlik Dönüşümü (Tellal -> Corvus): Uygulama adı, masaüstü simgesi ve web portali Corvus olarak yenilendi.",
        "Yeni Siber Karga Logosu: Yüksek çözünürlüklü macOS .icns ve web logo optimizasyonu tamamlandı.",
        "GitHub Repo Senkronizasyonu: Yeni 'ufukcelen/Corvus' ana reposu ile otomatik güncelleme bağlantısı kuruldu.",
        "Masaüstü 'Corvus.app' Başlatıcısı: macOS masaüstü kısayolu Corvus kimliği ve yeni simgesiyle güncellendi.",
        "Geriye Dönük Uyumluluk (Backward Compatibility): Eski takvim ID'leri ve veri köprüleri sıfır veri kaybı garantisiyle korundu.",
    ],
    "1.4.7": [
        "Tellal.app Masaüstü Dinamik Yol Eşitlemesi: .script_v5 marker'ı proje dizinini kontrol edecek şekilde güncellendi; farklı Mac veya taşınan klasörlerde açılmama sorunu tamamen giderildi.",
        "Tireli Maç ve Yayın Adı Koruması: 'Galatasaray - Fenerbahçe' gibi adında tire bulunan yayınların parçalanması, saat/gün kayması ve durum simgelerinin yanlış yere eklenmesi engellendi.",
        "Durum Simgesi Çakışma Önleme: İptal edilen yayına check işareti verildiğinde eski ❌ simgesi otomatik temizlenir; çift simge (❌ ✅) oluşumu engellendi.",
        "Firebase RTDB Veri Tipi Toleransı: Buluttan gelen veri yapısının (Object / Array) her iki formatta da güvenle çözümlenmesi sağlandı.",
        "Performans & Arayüz İyileştirmeleri: Terminal girdi tamponu temizliği (tcflush) tüm sihirbazlara eklendi, mükerrer bildirim ve ağ istekleri optimize edildi.",
    ],
    "1.4.6": [
        "Tellal.app macOS İzin Hatası (-1743) Giderildi: 'System Events' gereksinimi kaldırılarak Terminal doğrudan açılabilecek hale getirildi.",
        "Yayın Takvimi İzolasyonu: Gemini AI maç etkinlikleri yayın takviminden (.app ve takvim.txt) tamamen arındırıldı; yalnız web aylık takvim hücrelerinde gösterilir.",
        "Ekip Sohbeti (Chat) Temizliği: Canlı chat alanından yapay zeka bildirimleri kaldırıldı; sohbet yalnızca ekip arkadaşları arasındaki iletişime tahsis edildi.",
        "Veri Akışı & Bütünlük Koruması: .app ve Web arasındaki Firebase / Ntfy senkronizasyonu çift yönlü olarak sıfır hata prensibiyle güçlendirildi.",
    ],
    "1.4.5": [
        "Gemini AI Maç Takip Asistanı: Türkiye A Milli Takımı ve 4 Büyüklerin (GS, FB, BJK, TS) derbi ve lig maçları otomatik taranarak takvime eklendi.",
        "Normal Takvim ve Yayın Takvimi Ayrımı: Gemini AI maçları yayın takvimini ve masaüstü uygulamasını kirletmez; doğrudan web takvim gridinde gösterilir.",
        "Tellal Cloud Web Portalı: tellal-otomasyon.web.app üzerinden masaüstü (.app) ve bulut arasında anlık çift yönlü Firebase senkronizasyonu tamamlandı.",
        "Canlı Ekip Chat Entegrasyonu: Ufuk, Yiğit ve Cem Yıldırım için çoklu kullanıcı desteği ve yapay zeka bildirimli canlı sohbet kutusu eklendi.",
        "Aylık Takvim Arayüzü: Bugünün kırmızı rozeti, ay navigasyonu ve tek güne özel yayın eşleme algoritmasıyla modern edge-to-edge karanlık tema takvimi devreye alındı.",
    ],
    "1.4.2": [
        "Tellal.app çift tıklandığında fazladan boş Terminal penceresi açılma sorunu giderildi.",
        "Ana menüye 'Chat Refresh Yenile(R)' eklendi; R tuşuna basıldığında anında ekrana yazılmadan takvim ve chat yenilenir.",
    ],
    "1.4.1": [
        "Ufuk & Yiğit arasında canlı 'Chat' sohbet kutusu eklendi.",
        "Menüye 'Chat' seçeneği getirilerek anlık mesajlaşma sağlandı.",
        "Gelecek Yayınlar altına WhatsApp stili mesaj geçmişi kutusu entegre edildi.",
    ],
    "1.4.0": [
        "Ufuk & Yiğit arasında canlı 'Chat' sohbet kutusu eklendi.",
        "Menüye 'Chat' seçeneği getirilerek anlık mesajlaşma sağlandı.",
        "Gelecek Yayınlar altına WhatsApp stili mesaj geçmişi kutusu entegre edildi.",
    ],
    "1.3.0": [
        "Ana menü altına 'Gelecek Yayınlar' canlı takvim paneli eklendi.",
        "Ufuk için adım adım 'Yayın Ekle' sihirbazı ve 'Takvimi Temizle' seçenekleri eklendi.",
        "İki taraf arasında anlık takvim.txt senkronizasyonu tamamlandı.",
    ],
    "1.2.0": [
        "Ufuk & Yiğit iki taraflı anlık masaüstü bildirim sistemi eklendi.",
        "Açılışta otomatik kullanıcı tanımlama (user.txt) ve 'Hoş geldin' karşılama sistemi eklendi.",
        "Program açıldığında karşı taraftan gelen yeni bildirimlerin sesli macOS bildirimi ve görsel kutuyla gösterilmesi sağlandı.",
        "Ana menüye karşı tarafa kolay bildirim gönderme seçeneği eklendi.",
    ],
    "1.1.1": [
        "Masaüstü 'Tellal.app' başlatıcısına otomatik odaklanma (activate) eklendi; Terminal artık doğrudan öne geliyor.",
        "Uykusuz Tosba menüsüne 'Tosba Lojistik (ETS2)' bölümü (yapım aşamasında) eklendi.",
        "Ana menüden 'Çıkış' yapıldığında Terminal penceresinin otomatik kapanması sağlandı.",
        "Ana menü başlığındaki simge boşluğu düzenlendi (▶️  Youtube Duyuru Sistemi).",
    ],
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
            icerik = f"[bold cyan]Corvus v{SURUM} Yenilikleri:[/bold cyan]\n\n{maddeler}"
            console.print(Panel(icerik, title="[bold yellow]🎉 Sürüm Güncellendi!", expand=False))
        try:
            with open(surum_dosyasi, "w", encoding="utf-8") as f:
                f.write(SURUM)
        except Exception:
            pass


# =====================================================================
# OTOMATİK GÜNCELLEME (GitHub)
# =====================================================================
GITHUB_REPO = "ufukcelen/Corvus"
GITHUB_BRANCH = "main"
SCRIPT_GITHUB_ADI = "corvus.py"  

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
    gecici = hedef + ".corvus_indir"
    with open(gecici, "wb") as f:
        f.write(veri)
    os.replace(gecici, hedef)


def guncelleme_kontrol():
    if os.environ.get("CORVUS_GUNCELLEME") == "0" or os.environ.get("TELLAL_GUNCELLEME") == "0" or os.path.isdir(os.path.join(SCRIPT_DIR, ".git")):
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
    """macOS ortamında Masaüstüne çift tıklanabilir Corvus.app uygulamasını oluşturur ve özel ikonunu atar."""
    if platform.system() != "Darwin":
        return
    app_yolu = os.path.join(MASAUSTU, "Corvus.app")
    eski_app = os.path.join(MASAUSTU, "Tellal.app")
    if os.path.exists(eski_app):
        try:
            shutil.rmtree(eski_app, ignore_errors=True)
        except Exception:
            pass

    icns_kaynak = os.path.join(SCRIPT_DIR, "corvus.icns")
    if not os.path.exists(icns_kaynak):
        icns_kaynak = os.path.join(SCRIPT_DIR, "tellal.icns")
    png_kaynak = os.path.join(SCRIPT_DIR, "corvusicon.png")
    if not os.path.exists(png_kaynak):
        png_kaynak = os.path.join(SCRIPT_DIR, "tellalicon.png")
    main_scpt = os.path.join(app_yolu, "Contents", "Resources", "Scripts", "main.scpt")
    bq = "\\" + '"'
    sc_kodu = f'tell application "Terminal"\n    activate\n    do script "cd {bq}{SCRIPT_DIR}{bq} && python3 corvus.py"\nend tell\n'

    yeni_olusturuldu = False
    if not os.path.exists(app_yolu):
        try:
            subprocess.run(["osacompile", "-o", app_yolu], input=sc_kodu, text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            yeni_olusturuldu = True
        except Exception:
            return
    else:
        # Uygulama zaten var: Script içindeki çalışma dizini (SCRIPT_DIR) değişmişse veya eski sürümse otomatik yeniden derle
        try:
            marker = os.path.join(app_yolu, "Contents", "Resources", ".script_v6")
            kayitli_yol = ""
            if os.path.exists(marker):
                try:
                    with open(marker, "r", encoding="utf-8") as mf:
                        kayitli_yol = mf.read().strip()
                except Exception:
                    kayitli_yol = ""
            if kayitli_yol != SCRIPT_DIR and os.path.exists(main_scpt):
                subprocess.run(["osacompile", "-o", main_scpt], input=sc_kodu, text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                with open(marker, "w", encoding="utf-8") as f:
                    f.write(SCRIPT_DIR)
        except Exception:
            pass
        return  # uygulama zaten var: ikon işlemini tekrarlama (her açılışı yavaşlatır)

    # İkon dosyasını ve özel Finder rozetini ayarla (sadece ilk oluşturmada)
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

        if os.path.exists(png_kaynak) and subprocess.run(["xcode-select", "-p"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            swift_cmd = f'import Cocoa; if let img = NSImage(contentsOfFile: "{png_kaynak}") {{ NSWorkspace.shared.setIcon(img, forFile: "{app_yolu}", options: []) }}'
            subprocess.run(["swift", "-e", swift_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        with open(os.path.join(app_yolu, "Contents", "Resources", ".script_v5"), "w", encoding="utf-8") as f:
            f.write(SCRIPT_DIR)
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


def yayin_saati_kaydet(saat):
    """yayin_saati.json ve yayin_saati.csv dosyalarını günceller."""
    json_yolu = os.path.join(BASE_DIR, "yayin_saati.json")
    with open(json_yolu, "w", encoding="utf-8") as f:
        json.dump({"baslik": f"Bu Aksam {saat}"}, f, ensure_ascii=False)

    csv_yolu = os.path.join(BASE_DIR, "yayin_saati.csv")
    with open(csv_yolu, "wb") as f:
        f.write(f'baslik\n"Bu Aksam {saat}"'.encode("utf-8"))


def yapim_asamasinda_goster(baslik):
    """Henüz yapım aşamasında olan modüller için standart bilgilendirme kutusu."""
    console.print(Panel(
        f"[bold yellow]🚧 Yapım aşamasında...[/bold yellow]\n\n[dim]{baslik} duyuru otomasyonu yakında eklenecek.[/dim]",
        title=f"[bold cyan]{baslik}[/bold cyan]",
        expand=False
    ))
    Prompt.ask("\n[bold green]Geri dönmek için Enter'a basın[/bold green]", default="")


def haftalik_program_yap():
    """Uykusuz Tosba Haftalık Program duyuru görsellerini ve videosunu hazırlar."""
    saat = saat_al("Yayın Saat kaçta? (Örn: 21:00)")

    yayin_saati_kaydet(saat)

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

    if Confirm.ask("[bold yellow]Photoshop ile Haftalık Program Thumbnail (Kapak Görseli) oluşturulsun mu?[/bold yellow]", default=True):
        haftalik_thumbnail_olustur()


def canli_mac_veya_sonu_yap(mac_sonu=False):
    """Canlı Maç Sohbeti veya Maç Sonu duyuru otomasyonunu yürütür."""
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
        return

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
        return

    tr_time = datetime.strptime(mac_verisi['fixture']['date'], "%Y-%m-%dT%H:%M:%S%z").astimezone(timezone(timedelta(hours=3)))

    if mac_sonu:
        nihai_saat = saat_al("Yayın Saati kaçta? (Örn: 23:45)")
    else:
        yayin_saati_oto = (tr_time - timedelta(minutes=15)).strftime("%H:%M")
        nihai_saat = saat_al(f"Yayın Saati ({yayin_saati_oto} olarak hesaplandı). Farklı bir saat girmek ister misiniz?", default=yayin_saati_oto)

    yayin_saati_kaydet(nihai_saat)

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

    prog_adi = "Maç Sonu" if mac_sonu else "Canlı Maç Sohbetleri"
    klasor = cikti_klasoru_al(prog_adi, tarih=tarih)
    if Confirm.ask("[bold yellow]Dosyalar güncellendi. Render başlatılsın mı?[/bold yellow]"):
        video_adi = f"{'Mac_Sonu' if mac_sonu else 'Mac_Sohbeti'}_{nihai_saat.replace(':', '')}.mp4"
        ae_render_baslat(video_adi, hedef_klasor=klasor)
        seo_canli_yaz(mac_verisi, nihai_saat, video_adi, mac_sonu=mac_sonu, hedef_klasor=klasor)
    else:
        console.print("[dim]Render atlandı.[/dim]")

    if Confirm.ask("[bold yellow]Photoshop ile Canlı Maç Thumbnail (Kapak Görseli) oluşturulsun mu?[/bold yellow]", default=True):
        canli_mac_thumbnail_olustur(mac_verisi)


def uykusuz_tosba_menu():
    """Uykusuz Tosba alt programları için interaktif menü."""
    while True:
        console.print("\n")
        menu = """[bold cyan]1.[/bold cyan] Haftalık Program
[bold cyan]2.[/bold cyan] Canlı Maç Sohbetleri
[bold cyan]3.[/bold cyan] Maç Sonu
[bold cyan]4.[/bold cyan] Canlı Maç Thumbnail Oluştur (Photoshop) 🎨
[bold cyan]5.[/bold cyan] Tek Maçtan Yatanlar
[bold cyan]6.[/bold cyan] FC27 Kariyer
[bold cyan]7.[/bold cyan] Tosba Lojistik (ETS2)
[bold cyan]8.[/bold cyan] Geri"""
        console.print(Panel(menu, title=f"[bold yellow]🐢 Uykusuz Tosba Duyuru Sistemi [cyan]v{SURUM}[/cyan]", expand=False))

        secim = Prompt.ask("[bold green]İşlem seçin[/bold green]", choices=["1", "2", "3", "4", "5", "6", "7", "8"])

        if secim == "8":
            break

        try:
            if secim == "1":
                haftalik_program_yap()
            elif secim == "2":
                canli_mac_veya_sonu_yap(mac_sonu=False)
            elif secim == "3":
                canli_mac_veya_sonu_yap(mac_sonu=True)
            elif secim == "4":
                canli_mac_thumbnail_olustur_sihirbazi()
            elif secim == "5":
                tek_mac_yatanlar_yap()
            elif secim == "6":
                fc27_kariyer_yap()
            elif secim == "7":
                yapim_asamasinda_goster("Tosba Lojistik (ETS2)")
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


def seo_memleket_yaz(saat, video_adi, hedef_klasor=None):
    icerik = MEM_SEO_SABLON.format(saat=saat)
    plan, onceki_gun = planlama_saati(saat)
    if plan:
        gun = " (bir önceki gün)" if onceki_gun else ""
        planla = f"-Bu videoyu {plan} saatine planla{gun}"
    else:
        planla = "-Bu videoyu yayın saatinden 4 saat önceye planla"
    icerik += f"\n\n\n-Cem ve Burhan'ı etiketle\n\n-Videoya cyberpunk türü veya Cem'in şarkılarından birini koy\n\n{planla}\n"
    seo_yaz("seo_Filtresiz_memleket_Duyuru.txt", icerik, video_adi, hedef_klasor=hedef_klasor)


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

    if Confirm.ask("[bold yellow]Photoshop ile YouTube Thumbnail (Kapak Görseli) oluşturulsun mu?[/bold yellow]", default=True):
        memleket_thumbnail_olustur_sihirbazi()


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
    # 1. Önce buluttan okumayı dene
    try:
        r = requests.get(f"{FIREBASE_DB_URL}/durum/fc_takim.json", timeout=2.0)
        if r.status_code == 200 and r.json():
            ad_bulut = r.json()
            if isinstance(ad_bulut, str) and ad_bulut.strip():
                # Yerel dosyayı da senkronize et
                try:
                    with open(FC_TAKIM_DOSYASI, "w", encoding="utf-8") as f:
                        json.dump({"takim": ad_bulut.strip()}, f, ensure_ascii=False)
                except Exception:
                    pass
                return ad_bulut.strip()
    except Exception:
        pass

    # 2. Yerel dosyadan oku
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
    try:
        requests.put(f"{FIREBASE_DB_URL}/durum/fc_takim.json", json=ad, timeout=2.0)
    except Exception:
        pass


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


def memleket_thumbnail_olustur_sihirbazi():
    """
    Adobe Photoshop 2026 otomasyonu:
    - /Users/ufukcelen/Desktop/memleketYatay.psd dosyasını açar.
    - 'bolumno' text katmanına bölüm numarasını (#...) yazar.
    - 'renk1' ve 'renk2' Hue/Saturation katmanlarına rastgele (-180, 180) Hue uygular.
    - /Users/ufukcelen/Desktop/memleket{bolum_no}.jpg olarak maksimum kalitede kaydeder.
    - Orijinal PSD'yi kaydetmeden kapatır.
    """
    psd_yolu = os.path.join(MASAUSTU, "memleketYatay.psd")
    if not os.path.exists(psd_yolu):
        console.print(f"\n[bold red][HATA][/bold red] PSD şablonu bulunamadı:\n[dim]{psd_yolu}[/dim]\n[yellow]Lütfen 'memleketYatay.psd' dosyasını Masaüstüne yerleştirin.[/yellow]\n")
        Prompt.ask("[dim]Devam etmek için Enter'a basın...[/dim]")
        return

    console.print()
    panel_metni = (
        "[bold cyan]🎨 Filtresiz Memleket Havası — Thumbnail Oluşturucu[/bold cyan]\n\n"
        "[dim]• Şablon: memleketYatay.psd\n"
        "• 'bolumno' text katmanı otomatik güncellenir.\n"
        "• 'renk1' ve 'renk2' katmanlarına dinamik rastgele renk tonu (Hue) atanır.\n"
        "• Masaüstüne 'memleket{no}.jpg' olarak kaydedilir.[/dim]"
    )
    console.print(Panel(panel_metni, title="[bold yellow]📸 Photoshop Otomasyonu", expand=False))

    bolum_giris = Prompt.ask("[bold green]Bölüm Numarasını girin (Örn: 25 veya #25)[/bold green]", default="").strip()
    if not bolum_giris or bolum_giris.lower() in ("q", "iptal", "exit", "esc"):
        console.print("[dim yellow]İşlem iptal edildi.[/dim yellow]")
        return

    temiz_no = bolum_giris.lstrip("#").strip()
    etiket_no = f"#{temiz_no}"
    jpg_cikis_yolu = os.path.join(MASAUSTU, f"memleket{temiz_no}.jpg")

    hue1 = random.randint(-180, 180)
    hue2 = random.randint(-180, 180)

    jsx_script = f"""#target photoshop
app.displayDialogs = DialogModes.NO;

function selectLayerByName(name) {{
    var desc = new ActionDescriptor();
    var ref = new ActionReference();
    ref.putName(charIDToTypeID('Lyr '), name);
    desc.putReference(charIDToTypeID('null'), ref);
    desc.putBoolean(charIDToTypeID('MkVs'), false);
    executeAction(charIDToTypeID('slct'), desc, DialogModes.NO);
}}

function changeHue(hueVal) {{
    var desc = new ActionDescriptor();
    var ref = new ActionReference();
    ref.putEnumerated(charIDToTypeID('AdjL'), charIDToTypeID('Ordn'), charIDToTypeID('Trgt'));
    desc.putReference(charIDToTypeID('null'), ref);

    var descTo = new ActionDescriptor();
    descTo.putEnumerated(stringIDToTypeID('presetKind'), stringIDToTypeID('presetKindType'), stringIDToTypeID('presetKindCustom'));

    var list = new ActionList();
    var item = new ActionDescriptor();
    item.putInteger(charIDToTypeID('H   '), hueVal);
    item.putInteger(charIDToTypeID('Strt'), 0);
    item.putInteger(charIDToTypeID('Lght'), 0);
    list.putObject(charIDToTypeID('HStr'), item);

    descTo.putList(charIDToTypeID('Adjs'), list);
    desc.putObject(charIDToTypeID('T   '), charIDToTypeID('HStr'), descTo);

    executeAction(charIDToTypeID('setd'), desc, DialogModes.NO);
}}

try {{
    var doc = app.open(new File('{psd_yolu}'));

    selectLayerByName('bolumno');
    doc.activeLayer.textItem.contents = '{etiket_no}';

    selectLayerByName('renk1');
    changeHue({hue1});

    selectLayerByName('renk2');
    changeHue({hue2});

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

    temp_jsx = f"/tmp/corvus_thumbnail_{temiz_no}.jsx"
    try:
        with open(temp_jsx, "w", encoding="utf-8") as f:
            f.write(jsx_script)

        applescript_cmd = f'''tell application "Adobe Photoshop 2026"
            do javascript (file "{temp_jsx}")
        end tell'''

        with console.status(f"[bold cyan]Photoshop 2026 çalışıyor... (Bölüm: {etiket_no}, Ton1: {hue1}, Ton2: {hue2})[/bold cyan]"):
            proc = subprocess.run(
                ["osascript", "-e", applescript_cmd],
                capture_output=True,
                text=True
            )

        sonuc = proc.stdout.strip()
        if "ERROR" in sonuc or proc.returncode != 0:
            hata_mesaji = sonuc or proc.stderr.strip()
            console.print(f"\n[bold red][Photoshop Hatası][/bold red] {hata_mesaji}\n")
        else:
            ses_cal()
            console.print()
            bilgi_paneli = (
                f"[bold green]✓ Thumbnail Başarıyla Oluşturuldu![/bold green]\n\n"
                f"[bold cyan]Bölüm   :[/bold cyan] {etiket_no}\n"
                f"[bold cyan]Renk Tonları:[/bold cyan] Renk1: [bold yellow]{hue1}[/bold yellow] | Renk2: [bold yellow]{hue2}[/bold yellow]\n"
                f"[bold cyan]Kayıt Yolu  :[/bold cyan] [bold white]{jpg_cikis_yolu}[/bold white]"
            )
            console.print(Panel(bilgi_paneli, title="🎉 İşlem Tamamlandı", expand=False))
            
            if Confirm.ask("[bold yellow]Görseli açmak ister misiniz?[/bold yellow]", default=True):
                subprocess.run(["open", jpg_cikis_yolu])
    except Exception as e:
        console.print(f"\n[bold red][HATA][/bold red] İşlem başarısız: {e}\n")
    finally:
        if os.path.exists(temp_jsx):
            try:
                os.remove(temp_jsx)
            except Exception:
                pass


def haftalik_thumbnail_olustur():
    """
    Photoshop 2026'da masaüstündeki haftalık.psd dosyasını açar ve
    hiçbir katmanı değiştirmeden maksimum kalitede haftalik_program.jpg olarak kaydeder.
    """
    psd_yolu = os.path.join(MASAUSTU, "haftalık.psd")
    if not os.path.exists(psd_yolu):
        console.print(f"\n[bold red][HATA][/bold red] PSD şablonu bulunamadı:\n[dim]{psd_yolu}[/dim]\n[yellow]Lütfen 'haftalık.psd' dosyasını Masaüstüne yerleştirin.[/yellow]\n")
        Prompt.ask("[dim]Devam etmek için Enter'a basın...[/dim]")
        return False

    cikis_yolu = os.path.join(MASAUSTU, "haftalik_program.jpg")

    jsx_script = f"""#target photoshop
app.displayDialogs = DialogModes.NO;

try {{
    var doc = app.open(new File('{psd_yolu}'));

    var jpgFile = new File('{cikis_yolu}');
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

    temp_jsx = "/tmp/corvus_haftalik_thumb.jsx"
    try:
        with open(temp_jsx, "w", encoding="utf-8") as f:
            f.write(jsx_script)

        applescript_cmd = f'''tell application "Adobe Photoshop 2026"
            do javascript (file "{temp_jsx}")
        end tell'''

        with console.status("[bold cyan]Photoshop 2026 çalışıyor... (haftalık.psd dışa aktarılıyor)[/bold cyan]"):
            proc = subprocess.run(
                ["osascript", "-e", applescript_cmd],
                capture_output=True,
                text=True
            )

        sonuc = proc.stdout.strip()
        if "ERROR" in sonuc or proc.returncode != 0:
            hata_mesaji = sonuc or proc.stderr.strip()
            console.print(f"\n[bold red][Photoshop Hatası][/bold red] {hata_mesaji}\n")
            return False
        else:
            ses_cal()
            console.print()
            bilgi_paneli = (
                f"[bold green]✓ Haftalık Program Thumbnail Başarıyla Oluşturuldu![/bold green]\n\n"
                f"[bold cyan]Şablon    :[/bold cyan] haftalık.psd\n"
                f"[bold cyan]Kayıt Yolu:[/bold cyan] [bold white]{cikis_yolu}[/bold white]"
            )
            console.print(Panel(bilgi_paneli, title="🎉 İşlem Tamamlandı", expand=False))

            if Confirm.ask("[bold yellow]Görseli açmak ister misiniz?[/bold yellow]", default=True):
                subprocess.run(["open", cikis_yolu])
            return True
    except Exception as e:
        console.print(f"\n[bold red][HATA][/bold red] İşlem başarısız: {e}\n")
        return False
    finally:
        if os.path.exists(temp_jsx):
            try:
                os.remove(temp_jsx)
            except Exception:
                pass


def canli_mac_thumbnail_olustur(mac_verisi):
    """
    Seçilen karşılaşma verisine göre Photoshop 2026'da canlimac.psd dosyasını günceller:
    - Turnuva katmanını (superlig, cl, europa, conf, uluslar) gösterir, diğerlerini gizler.
    - Ev sahibi ve deplasman logolarını evtakim ve deptakim Smart Object'lerine yerleştirir.
    - Masaüstüne canlimacyatay.jpg olarak kaydeder.
    """
    psd_yolu = os.path.join(MASAUSTU, "canlimac.psd")
    if not os.path.exists(psd_yolu):
        console.print(f"\n[bold red][HATA][/bold red] PSD şablonu bulunamadı:\n[dim]{psd_yolu}[/dim]\n[yellow]Lütfen 'canlimac.psd' dosyasını Masaüstüne yerleştirin.[/yellow]\n")
        Prompt.ask("[dim]Devam etmek için Enter'a basın...[/dim]")
        return False

    lig_id = mac_verisi['league']['id']
    # 2: Şampiyonlar Ligi -> cl
    # 3: Europa Ligi -> europa
    # 848: Konferans Ligi -> conf
    # 203: Süper Lig -> superlig
    # 5: Uluslar Ligi -> uluslar
    turnuva_map = {
        2: "cl",
        3: "europa",
        848: "conf",
        203: "superlig",
        5: "uluslar"
    }
    aktif_turnuva = turnuva_map.get(lig_id, "superlig")

    ev_logo_url = mac_verisi['teams']['home'].get('logo')
    dep_logo_url = mac_verisi['teams']['away'].get('logo')

    ev_logo_yolu = f"/tmp/ev_logo_{mac_verisi['teams']['home']['id']}.png"
    dep_logo_yolu = f"/tmp/dep_logo_{mac_verisi['teams']['away']['id']}.png"

    def smart_object_logo_hazirla(url, hedef_yol, is_ev_sahibi=True):
        try:
            from PIL import Image
            r = requests.get(url, timeout=12)
            r.raise_for_status()
            img = Image.open(io.BytesIO(r.content)).convert("RGBA")
            # Varsa kenardaki gereksiz saydam boşlukları kırp
            bbox = img.getbbox()
            if bbox:
                img = img.crop(bbox)
            
            w, h = img.size
            if w > 0 and h > 0:
                aspect = w / h
                # Optik Hacim (Optical Weight):
                # Dairesel veya kareye yakın logolar (Konya, FB, City vb.) kütle olarak çok dolgun olduğu için 225px
                # Dar, dikey veya yıldızlı logolar (GS, BJK vb.) gövdesi ezilmesin diye 280px
                if 0.82 <= aspect <= 1.20:
                    target_dim = 225
                else:
                    target_dim = 280

                ratio = min(target_dim / w, target_dim / h)
                new_w = max(1, int(w * ratio))
                new_h = max(1, int(h * ratio))
                img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            else:
                img_resized = img

            canvas = Image.new("RGBA", (300, 300), (0, 0, 0, 0))
            # Optik merkezleme: Tuvalin hem yatay hem dikey tam merkezine yerleştir
            x = (300 - img_resized.width) // 2
            y = (300 - img_resized.height) // 2
            canvas.paste(img_resized, (x, y), img_resized)
            canvas.save(hedef_yol, format="PNG")
            return True
        except Exception as e:
            console.print(f"[bold yellow][UYARI][/bold yellow] Logo hazırlanamadı ({e}).")
            return False

    with console.status("[bold cyan]Takım logoları indiriliyor ve tuvale yerleştiriliyor...[/bold cyan]"):
        if ev_logo_url:
            smart_object_logo_hazirla(ev_logo_url, ev_logo_yolu, is_ev_sahibi=True)
        if dep_logo_url:
            smart_object_logo_hazirla(dep_logo_url, dep_logo_yolu, is_ev_sahibi=False)

    # Yedek kontrol: Eğer logolar indirilemediyse BASE_DIR'e bak
    if not os.path.exists(ev_logo_yolu):
        ev_logo_yolu = os.path.join(BASE_DIR, "evTakım.png")
    if not os.path.exists(dep_logo_yolu):
        dep_logo_yolu = os.path.join(BASE_DIR, "depTakım.png")

    cikis_yolu = os.path.join(MASAUSTU, "canlimacyatay.jpg")

    jsx_script = f"""#target photoshop
app.displayDialogs = DialogModes.NO;

function selectLayerByName(name) {{
    var desc = new ActionDescriptor();
    var ref = new ActionReference();
    ref.putName(charIDToTypeID('Lyr '), name);
    desc.putReference(charIDToTypeID('null'), ref);
    desc.putBoolean(charIDToTypeID('MkVs'), false);
    executeAction(charIDToTypeID('slct'), desc, DialogModes.NO);
}}

function replaceSmartObject(layerName, filePath) {{
    selectLayerByName(layerName);
    var desc = new ActionDescriptor();
    desc.putPath(charIDToTypeID('null'), new File(filePath));
    executeAction(stringIDToTypeID('placedLayerReplaceContents'), desc, DialogModes.NO);
}}

try {{
    var doc = app.open(new File('{psd_yolu}'));

    // 1. Turnuva katmanlarını ayarla (Sadece eşleşen görünür, diğerleri gizli)
    var turnuvalar = ['superlig', 'cl', 'europa', 'conf', 'uluslar'];
    for (var i = 0; i < turnuvalar.length; i++) {{
        try {{
            selectLayerByName(turnuvalar[i]);
            doc.activeLayer.visible = (turnuvalar[i] === '{aktif_turnuva}');
        }} catch(e) {{}}
    }}

    // 2. Akıllı nesneleri güncelle (oran bozulmadan)
    replaceSmartObject('evtakim', '{ev_logo_yolu}');
    replaceSmartObject('deptakim', '{dep_logo_yolu}');

    // 2.1. İki logonun optik merkezini (Center Y) aynı yatay eksene kilitle (TV Yayın Standardı)
    try {{
        var evLayer = doc.artLayers.getByName('evtakim');
        var depLayer = doc.artLayers.getByName('deptakim');

        var evB = evLayer.bounds;
        var depB = depLayer.bounds;

        var evCenterY = (evB[1].value + evB[3].value) / 2;
        var depCenterY = (depB[1].value + depB[3].value) / 2;

        var targetCenterY = 340;
        var evShift = targetCenterY - evCenterY;
        var depShift = targetCenterY - depCenterY;

        if (Math.abs(evShift) > 0.1) {{
            evLayer.translate(0, evShift);
        }}
        if (Math.abs(depShift) > 0.1) {{
            depLayer.translate(0, depShift);
        }}
    }} catch(e) {{}}

    // 3. JPG Olarak Kaydet (Maksimum Kalite: 12)
    var jpgFile = new File('{cikis_yolu}');
    var jpgOpts = new JPEGSaveOptions();
    jpgOpts.quality = 12;
    jpgOpts.embedColorProfile = true;
    doc.saveAs(jpgFile, jpgOpts, true, Extension.LOWERCASE);

    // 4. Orijinal PSD'yi kaydetmeden kapat
    doc.close(SaveOptions.DONOTSAVECHANGES);
    'SUCCESS';
}} catch (e) {{
    'ERROR: ' + e.message;
}}
"""

    temp_jsx = "/tmp/corvus_canlimac_thumb.jsx"
    try:
        with open(temp_jsx, "w", encoding="utf-8") as f:
            f.write(jsx_script)

        applescript_cmd = f'''tell application "Adobe Photoshop 2026"
            do javascript (file "{temp_jsx}")
        end tell'''

        ev_ad = mac_verisi['teams']['home']['name']
        dep_ad = mac_verisi['teams']['away']['name']
        lig_ad = mac_verisi['league']['name']

        with console.status(f"[bold cyan]Photoshop 2026 çalışıyor... ({ev_ad} vs {dep_ad} | {lig_ad})[/bold cyan]"):
            proc = subprocess.run(
                ["osascript", "-e", applescript_cmd],
                capture_output=True,
                text=True
            )

        sonuc = proc.stdout.strip()
        if "ERROR" in sonuc or proc.returncode != 0:
            hata_mesaji = sonuc or proc.stderr.strip()
            console.print(f"\n[bold red][Photoshop Hatası][/bold red] {hata_mesaji}\n")
            return False
        else:
            ses_cal()
            console.print()
            bilgi_paneli = (
                f"[bold green]✓ Canlı Maç Thumbnail Başarıyla Oluşturuldu![/bold green]\n\n"
                f"[bold cyan]Karşılaşma :[/bold cyan] [bold yellow]{ev_ad}[/bold yellow] vs [bold yellow]{dep_ad}[/bold yellow]\n"
                f"[bold cyan]Turnuva    :[/bold cyan] {lig_ad} [dim]({aktif_turnuva})[/dim]\n"
                f"[bold cyan]Kayıt Yolu :[/bold cyan] [bold white]{cikis_yolu}[/bold white]"
            )
            console.print(Panel(bilgi_paneli, title="🎉 İşlem Tamamlandı", expand=False))

            if Confirm.ask("[bold yellow]Görseli açmak ister misiniz?[/bold yellow]", default=True):
                subprocess.run(["open", cikis_yolu])
            return True
    except Exception as e:
        console.print(f"\n[bold red][HATA][/bold red] İşlem başarısız: {e}\n")
        return False
    finally:
        if os.path.exists(temp_jsx):
            try:
                os.remove(temp_jsx)
            except Exception:
                pass


def canli_mac_thumbnail_olustur_sihirbazi():
    """Kullanıcıya maç seçtirerek Canlı Maç Thumbnail (canlimacyatay.jpg) oluşturan bağımsız sihirbaz."""
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
        return

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
    secilen_id = sira_to_id.get(girdi, girdi)
    mac_verisi = next((m for m in maclar if str(m['fixture']['id']) == secilen_id), None)

    if not mac_verisi:
        console.print("[bold red][UYARI][/bold red] Maç bulunamadı.")
        return

    canli_mac_thumbnail_olustur(mac_verisi)


def thumbnail_ana_menusu():
    """Tüm programlar için Photoshop Thumbnail Üretim Merkezi."""
    while True:
        console.print("\n")
        menu = """[bold cyan]1.[/bold cyan] Filtresiz Memleket Havası (memleketYatay.psd)
[bold cyan]2.[/bold cyan] Canlı Maç Sohbetleri (canlimac.psd)
[bold cyan]3.[/bold cyan] Haftalık Program (haftalık.psd)
[bold cyan]4.[/bold cyan] Geri"""
        console.print(Panel(menu, title=f"[bold yellow]🎨 Photoshop Thumbnail Merkezi [cyan]v{SURUM}[/cyan]", expand=False))

        secim = Prompt.ask("[bold green]İşlem seçin[/bold green]", choices=["1", "2", "3", "4"])
        if secim == "4":
            break
        elif secim == "1":
            try:
                memleket_thumbnail_olustur_sihirbazi()
            except Exception as e:
                console.print(f"\n[bold red][HATA][/bold red] İşlem sırasında sorun oluştu: {e}")
        elif secim == "2":
            try:
                canli_mac_thumbnail_olustur_sihirbazi()
            except Exception as e:
                console.print(f"\n[bold red][HATA][/bold red] İşlem sırasında sorun oluştu: {e}")
        elif secim == "3":
            try:
                haftalik_thumbnail_olustur()
            except Exception as e:
                console.print(f"\n[bold red][HATA][/bold red] İşlem sırasında sorun oluştu: {e}")


def radio_mocas_menu():
    while True:
        console.print("\n")
        menu = """[bold cyan]1.[/bold cyan] Filtresiz Memleket Havası
[bold cyan]2.[/bold cyan] Memleket Thumbnail Oluştur (Photoshop) 🎨
[bold cyan]3.[/bold cyan] Albert ve Cem
[bold cyan]4.[/bold cyan] Mocas Bey ve Radyosu
[bold cyan]5.[/bold cyan] Aklımdaki Filmler
[bold cyan]6.[/bold cyan] Geri"""
        console.print(Panel(menu, title=f"[bold yellow]📻 Radio Mocas Duyuru Sistemi [cyan]v{SURUM}[/cyan]", expand=False))

        secim = Prompt.ask("[bold green]İşlem seçin[/bold green]", choices=["1", "2", "3", "4", "5", "6"])
        if secim == "6":
            break
        if secim == "1":
            try:
                memleket_duyuru_yap()
            except Exception as e:
                console.print(f"\n[bold red][HATA][/bold red] İşlem sırasında sorun oluştu: {e}")
        elif secim == "2":
            try:
                memleket_thumbnail_olustur_sihirbazi()
            except Exception as e:
                console.print(f"\n[bold red][HATA][/bold red] İşlem sırasında sorun oluştu: {e}")
        elif secim == "3":
            try:
                albert_ve_cem_yap()
            except Exception as e:
                console.print(f"\n[bold red][HATA][/bold red] İşlem sırasında sorun oluştu: {e}")
        elif secim == "4":
            yapim_asamasinda_goster("Mocas Bey ve Radyosu")
        elif secim == "5":
            yapim_asamasinda_goster("Aklımdaki Filmler")


def banner_yazdir():
    """Program başlığındaki şık ASCII art Corvus logosunu ve kanal bilgilerini yazdırır."""
    art = [
        (r"  ____ ___  ______     ___   _ ____  ", r""),
        (r" / ___/ _ \|  _ \ \   / / | | / ___| ", r"  [bold cyan]/uykusuztosba[/bold cyan]   [bold magenta]/radiomocas[/bold magenta]"),
        (r"| |  | | | | |_) \ \ / /| | | \___ \ ", f"  [dim]Yayın & Stüdyo Otomasyonu[/dim] [bold yellow]v{SURUM}[/bold yellow]"),
        (r"| |__| |_| |  _ < \ V / | |_| |___) |", r""),
        (r" \____\___/|_| \_\ \_/   \__,_|____/ ", r""),
    ]
    console.print()
    for sol, sag in art:
        console.print(f"[bold cyan]{sol:<37}[/bold cyan]{sag}")
    console.print()


# =====================================================================
# KULLANICI KİMLİK VE BİLDİRİM SİSTEMİ (Ufuk & Yiğit)
# =====================================================================
KULLANICILAR = {
    "1": "Ufuk",
    "2": "Yiğit"
}
USER_FILE = os.path.join(SCRIPT_DIR, "user.txt")
SON_BILDIRIM_FILE = os.path.join(SCRIPT_DIR, ".son_bildirim")

NTFY_TOPIC_UFUK_TO_YIGIT = "tellal_duyuru_ufuk_yigit_u2y_7294"
NTFY_TOPIC_YIGIT_TO_UFUK = "tellal_duyuru_ufuk_yigit_y2u_7294"


def kullanici_belirle():
    """user.txt dosyasından kimliği okur; dosya yoksa veya geçersizse kullanıcıya sorup kaydeder."""
    secim = None
    if os.path.exists(USER_FILE):
        try:
            with open(USER_FILE, "r", encoding="utf-8") as f:
                secim = f.read().strip()
        except Exception:
            secim = None

    if secim not in KULLANICILAR:
        console.print()
        panel_metni = """[bold cyan]Corvus Kullanıcı Tanımlama[/bold cyan]

[bold yellow]Sen Kimsin?[/bold yellow]
[bold cyan]1.[/bold cyan] Ufuk
[bold cyan]2.[/bold cyan] Yiğit

[dim]Bu seçim 'user.txt' dosyasına kaydedilecek ve bir daha sorulmayacaktır.[/dim]"""
        console.print(Panel(panel_metni, title="[bold green]👤 Kimlik Seçimi", expand=False))
        secim = Prompt.ask("[bold green]Kimliğinizi seçin[/bold green]", choices=["1", "2"])
        try:
            with open(USER_FILE, "w", encoding="utf-8") as f:
                f.write(secim)
        except Exception as e:
            console.print(f"[dim red]user.txt kaydedilemedi: {e}[/dim red]")

    return secim, KULLANICILAR[secim]


def kullanici_degistir():
    """Mevcut kimlik dosyasını temizler ve tekrar kimlik seçtirir."""
    if os.path.exists(USER_FILE):
        try:
            os.remove(USER_FILE)
        except Exception:
            pass
    return kullanici_belirle()


def bildirimleri_kontrol_et(kullanici_id):
    """Program açıldığında veya menüde karşı taraftan gelen yeni bildirimleri denetler, macOS bildirimi ve kutuyla gösterir."""
    if kullanici_id == "1":
        dinlenen_topic = NTFY_TOPIC_YIGIT_TO_UFUK
        gonderen_adi = "Yiğit"
    else:
        dinlenen_topic = NTFY_TOPIC_UFUK_TO_YIGIT
        gonderen_adi = "Ufuk"

    son_zaman = 0
    if os.path.exists(SON_BILDIRIM_FILE):
        try:
            with open(SON_BILDIRIM_FILE, "r", encoding="utf-8") as f:
                icerik = f.read().strip()
                if icerik.isdigit():
                    son_zaman = int(icerik)
        except Exception:
            son_zaman = 0

    # Eğer daha önce hiç kayıt yoksa son 24 saatteki mesajlara bak
    if son_zaman == 0:
        son_zaman = int(datetime.now(timezone.utc).timestamp()) - 86400

    url = f"https://ntfy.sh/{dinlenen_topic}/json?poll=1&since={son_zaman + 1}"
    try:
        yanit = requests.get(url, timeout=3.5)
        if yanit.status_code != 200 or not yanit.text.strip():
            return

        yeni_mesajlar = []
        en_buyuk_zaman = son_zaman

        for satir in yanit.text.strip().split("\n"):
            if not satir:
                continue
            try:
                veri = json.loads(satir)
                if veri.get("event") == "message":
                    mesaj_zamani = veri.get("time", 0)
                    if mesaj_zamani > son_zaman:
                        yeni_mesajlar.append(veri)
                        if mesaj_zamani > en_buyuk_zaman:
                            en_buyuk_zaman = mesaj_zamani
            except Exception:
                continue

        if yeni_mesajlar:
            for m in yeni_mesajlar:
                mesaj_metni = m.get("message", "")
                zaman_ts = m.get("time", 0)
                zaman_str = datetime.fromtimestamp(zaman_ts).strftime("%d.%m.%Y %H:%M") if zaman_ts else ""

                # macOS yerel sesli bildirimi
                if platform.system() == "Darwin":
                    try:
                        temiz_mesaj = mesaj_metni.replace('"', "'")
                        subprocess.run(
                            ["osascript", "-e", f'display notification "{temiz_mesaj}" with title "Corvus - {gonderen_adi}" sound name "Glass"'],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                    except Exception:
                        pass

                # Konsolda şık bildirim paneli
                bildirim_paneli = f"[bold white]{mesaj_metni}[/bold white]\n\n[dim]Gönderilme: {zaman_str}[/dim]"
                console.print()
                console.print(Panel(bildirim_paneli, title=f"[bold yellow]📬 {gonderen_adi}'den Yeni Bildirim!", expand=False))
                console.print()

            # En son okunan zaman damgasını güncelle
            try:
                with open(SON_BILDIRIM_FILE, "w", encoding="utf-8") as f:
                    f.write(str(en_buyuk_zaman))
            except Exception:
                pass

    except Exception:
        # Ağ kesintisi durumunda program akışı engellenmez
        pass


def bildirim_gonder(kullanici_id):
    """Karşı kullanıcıya bildirim gönderir."""
    if kullanici_id == "1":
        hedef_adi = "Yiğit"
        hedef_topic = NTFY_TOPIC_UFUK_TO_YIGIT
        gonderen_adi = "Ufuk"
    else:
        hedef_adi = "Ufuk"
        hedef_topic = NTFY_TOPIC_YIGIT_TO_UFUK
        gonderen_adi = "Yiğit"

    console.print()
    panel_metni = (
        f"[bold cyan]{hedef_adi}'e Bildirim Gönder[/bold cyan]\n\n"
        f"[dim]• {hedef_adi} Corvus'u açtığı anda Mac'inde sesli masaüstü bildirimi belirecektir.\n"
        f"• Geri dönmek / vazgeçmek için boş bırakıp Enter'a basın veya 'q' yazın.[/dim]"
    )
    console.print(Panel(panel_metni, title="[bold yellow]📢 Bildirim Sistemi", expand=False))

    mesaj = Prompt.ask(f"[bold green]{hedef_adi}'e iletilecek mesaj[/bold green]", default="").strip()

    if not mesaj or mesaj.lower() in ("q", "iptal", "exit", "esc"):
        console.print("[dim yellow]İşlem iptal edildi, ana menüye dönülüyor.[/dim yellow]")
        return

    try:
        payload = {
            "topic": hedef_topic,
            "title": f"Corvus - {gonderen_adi}",
            "message": mesaj,
            "priority": 4,
            "tags": ["loudspeaker", "bell"]
        }
        res = requests.post("https://ntfy.sh", json=payload, timeout=5)
        if res.status_code == 200:
            console.print(f"\n[bold green]✓ Bildirim başarıyla gönderildi![/bold green] [dim]({hedef_adi} Corvus'u açtığında görecek)[/dim]\n")
        else:
            console.print(f"\n[bold red]Bildirim gönderilemedi (Hata: {res.status_code})[/bold red]\n")
    except Exception as e:
        console.print(f"\n[bold red]Bağlantı hatası: {e}[/bold red]\n")


# =====================================================================
# TAKVİM VE GELECEK YAYINLAR SİSTEMİ (Firebase RTDB + Yerel Senkronizasyon)
# =====================================================================
TAKVIM_DOSYASI = os.path.join(SCRIPT_DIR, "takvim.txt")
TAKVIM_SYNC_DOSYASI = os.path.join(SCRIPT_DIR, ".takvim_sync")
NTFY_TOPIC_TAKVIM = "tellal_takvim_sync_u_y_8832"
FIREBASE_DB_URL = "https://tellal-otomasyon-default-rtdb.europe-west1.firebasedatabase.app/tellal_db"

YAYIN_SECENEKLERI = [
    "Haftalık Program",
    "Canlı Maç Sohbetleri",
    "Maç Sonu",
    "Tek Maçtan Yatanlar",
    "FC27 Kariyer",
    "Tosba Lojistik (ETS2)",
    "Filtresiz Memleket Havası",
    "Albert ve Cem",
    "Mocas Bey ve Radyosu",
    "Aklımdaki Filmler"
]

def dinamik_gunleri_al():
    """Bugünden itibaren başlayan 7 günlük listeyi döndürür. (Örn: bugün Perşembe ise: Bugün (Perşembe), Cuma, Cumartesi...)"""
    gunler = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    bugun_idx = datetime.now(timezone(timedelta(hours=3))).weekday()
    sonuc = []
    for i in range(7):
        idx = (bugun_idx + i) % 7
        gun_adi = gunler[idx]
        if i == 0:
            etiket = f"Bugün ({gun_adi})"
            deger = f"Bugün ({gun_adi})"
        else:
            etiket = gun_adi
            deger = gun_adi
        sonuc.append((etiket, deger))
    return sonuc


def takvim_filtrele_ve_duzenle(satirlar):
    """Gemini AI bot satırlarını yayın takviminden ayıklar; Canlı Maç Sohbetleri gibi gerçek yayınları korur ve numaralandırmayı düzeltir."""
    temiz = []
    for s in satirlar:
        if not s or not s.strip():
            continue
        s_clean = s.strip()
        # Sadece ve sadece Gemini AI botuna ait yapay satırları ayıkla
        # "Canlı Maç Sohbetleri" ve "Canlı Maç Sohbeti" gerçek yayınlardır, korunur!
        if "Gemini AI" in s_clean or "[Gemini AI]" in s_clean or s_clean.startswith("Gemini AI:"):
            continue
        temiz.append(s_clean)

    # Numaralandırmayı 1'den başlayarak yeniden düzenle
    duzenli = []
    for idx, s in enumerate(temiz, 1):
        if "-)" in s:
            parcalar = s.split("-)", 1)
            duzenli.append(f"{idx}-) {parcalar[1].strip()}")
        else:
            duzenli.append(f"{idx}-) {s}")
    return duzenli


def takvim_senkronize_et():
    """Bulut veritabanından (Firebase RTDB) ve ntfy üzerinden en güncel takvimi yerel takvim.txt ile eşitler."""
    guncellendi = False

    # 1. Birincil: Firebase Realtime Database
    try:
        url_fb = f"{FIREBASE_DB_URL}/takvim.json"
        res_fb = requests.get(url_fb, timeout=2.5)
        if res_fb.status_code == 200:
            data = res_fb.json()
            if isinstance(data, dict):
                if data.get("bos_mu"):
                    satirlar = []
                else:
                    raw = data.get("satirlar") or []
                    if isinstance(raw, dict):
                        raw = list(raw.values())
                    raw_satirlar = [s for s in raw if s and isinstance(s, str) and s.strip()]
                    satirlar = takvim_filtrele_ve_duzenle(raw_satirlar)
                icerik = "\n".join(satirlar) + ("\n" if satirlar else "")
                with open(TAKVIM_DOSYASI, "w", encoding="utf-8") as f:
                    f.write(icerik)
                guncellendi = True
    except Exception:
        pass

    # 2. İkincil / Fallback: Ntfy
    if not guncellendi:
        son_zaman = 0
        if os.path.exists(TAKVIM_SYNC_DOSYASI):
            try:
                with open(TAKVIM_SYNC_DOSYASI, "r", encoding="utf-8") as f:
                    c = f.read().strip()
                    if c.isdigit():
                        son_zaman = int(c)
            except Exception:
                son_zaman = 0

        url = f"https://ntfy.sh/{NTFY_TOPIC_TAKVIM}/json?poll=1&since=all"
        try:
            r = requests.get(url, timeout=2.5)
            if r.status_code == 200 and r.text.strip():
                en_yeni_mesaj = None
                for line in r.text.strip().split("\n"):
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                        if d.get("event") == "message":
                            m_time = d.get("time", 0)
                            if m_time >= son_zaman:
                                en_yeni_mesaj = d
                                son_zaman = m_time
                    except Exception:
                        continue

                if en_yeni_mesaj is not None:
                    raw_icerik = en_yeni_mesaj.get("message", "")
                    if raw_icerik == "__BOS_TAKVIM__":
                        satirlar = []
                    else:
                        satirlar = takvim_filtrele_ve_duzenle(raw_icerik.splitlines())
                    icerik = "\n".join(satirlar) + ("\n" if satirlar else "")
                    with open(TAKVIM_DOSYASI, "w", encoding="utf-8") as f:
                        f.write(icerik)
                    with open(TAKVIM_SYNC_DOSYASI, "w", encoding="utf-8") as f:
                        f.write(str(son_zaman))
                    guncellendi = True
        except Exception:
            pass


def takvim_uzaga_gonder(icerik, guncelleyen="Ufuk"):
    """Güncellenmiş takvim.txt içeriğini Firebase Realtime Database'e ve ntfy üzerine kaydeder."""
    satirlar = takvim_filtrele_ve_duzenle([s.strip() for s in icerik.strip().split("\n") if s.strip()])
    temiz_icerik = "\n".join(satirlar) + ("\n" if satirlar else "")

    # 1. Birincil: Firebase Realtime Database'e kaydet (bos_mu bayrağı boş listeyi garantiye alır)
    try:
        url_fb = f"{FIREBASE_DB_URL}/takvim.json"
        payload_fb = {
            "satirlar": satirlar,
            "bos_mu": len(satirlar) == 0,
            "son_guncelleme": int(datetime.now(timezone.utc).timestamp()),
            "guncelleyen": guncelleyen
        }
        requests.put(url_fb, json=payload_fb, timeout=3.5)
    except Exception:
        pass

    # 2. İkincil: Ntfy bildirim kanalı
    try:
        mesaj = temiz_icerik if temiz_icerik.strip() else "__BOS_TAKVIM__"
        payload = {
            "topic": NTFY_TOPIC_TAKVIM,
            "title": "Corvus Takvim Güncellemesi",
            "message": mesaj,
            "priority": 3,
            "tags": ["calendar"]
        }
        r = requests.post("https://ntfy.sh", json=payload, timeout=3.5)
        if r.status_code == 200:
            try:
                res_data = r.json()
                t = res_data.get("time")
                if t:
                    with open(TAKVIM_SYNC_DOSYASI, "w", encoding="utf-8") as f:
                        f.write(str(t))
            except Exception:
                pass
    except Exception:
        pass

    # 3. Üçüncül: Google Takvim ("Yayın Takvimi") Otomatik Eşitleme (Yalnızca kullanıcı yayın oluşturduğunda/sildiğinde)
    if not guncelleyen.startswith("Sistem"):
        try:
            from gcalendar_sync import google_takvim_senkronize_et
            google_takvim_senkronize_et(satirlar)
        except Exception:
            pass


def takvim_oku():
    """Takvim dosyasını senkronize edip satır satır liste olarak döndürür."""
    takvim_senkronize_et()
    if not os.path.exists(TAKVIM_DOSYASI):
        return []
    try:
        with open(TAKVIM_DOSYASI, "r", encoding="utf-8") as f:
            satirlar = [s.strip() for s in f if s.strip()]
        temiz = takvim_filtrele_ve_duzenle(satirlar)
        if len(temiz) != len(satirlar):
            icerik = "\n".join(temiz) + ("\n" if temiz else "")
            with open(TAKVIM_DOSYASI, "w", encoding="utf-8") as f:
                f.write(icerik)
            takvim_uzaga_gonder(icerik, guncelleyen="Sistem (Temizlik)")
        return temiz
    except Exception:
        return []


def takvime_yayin_ekle():
    """Ufuk için adım adım yayın ekleme sihirbazı."""
    # 1. Adım: Yayın Adı Seçimi
    console.print()

    yayin_satirlari = [f"[bold cyan]{i}.[/bold cyan] {ad}" for i, ad in enumerate(YAYIN_SECENEKLERI, 1)]
    yayin_satirlari.append(f"[bold cyan]{len(YAYIN_SECENEKLERI) + 1}.[/bold cyan] Geri")
    console.print(Panel("\n".join(yayin_satirlari), title="[bold yellow]📺 1. Adım: Yayın Seçin", expand=False))

    gecerli_yayin_secimleri = [str(i) for i in range(1, len(YAYIN_SECENEKLERI) + 2)]
    yayin_secim = Prompt.ask("[bold green]Yayın seçin[/bold green]", choices=gecerli_yayin_secimleri)

    if yayin_secim == str(len(YAYIN_SECENEKLERI) + 1):
        console.print("[dim yellow]İşlem iptal edildi, ana menüye dönülüyor.[/dim yellow]")
        return

    secilen_yayin = YAYIN_SECENEKLERI[int(yayin_secim) - 1]

    # 2. Adım: Yayın Günü Seçimi (Bugünden itibaren 7 gün)
    dinamik_gunler = dinamik_gunleri_al()
    console.print()
    gun_satirlari = [f"[bold cyan]{i}.[/bold cyan] {etiket}" for i, (etiket, _) in enumerate(dinamik_gunler, 1)]
    gun_satirlari.append(f"[bold cyan]{len(dinamik_gunler) + 1}.[/bold cyan] Geri")
    console.print(Panel("\n".join(gun_satirlari), title=f"[bold yellow]📅 2. Adım: {secilen_yayin} için Yayın Günü Seçin", expand=False))

    gecerli_gun_secimleri = [str(i) for i in range(1, len(dinamik_gunler) + 2)]
    gun_secim = Prompt.ask("[bold green]Gün seçin[/bold green]", choices=gecerli_gun_secimleri)

    if gun_secim == str(len(dinamik_gunler) + 1):
        console.print("[dim yellow]İşlem iptal edildi, ana menüye dönülüyor.[/dim yellow]")
        return

    secilen_gun = dinamik_gunler[int(gun_secim) - 1][1]

    # 3. Adım: Yayın Saati Belirleme
    console.print()
    saat_paneli = (
        f"[bold cyan]Yayın :[/bold cyan] [bold white]{secilen_yayin}[/bold white]\n"
        f"[bold cyan]Gün   :[/bold cyan] [bold white]{secilen_gun}[/bold white]\n\n"
        "[dim]Yayın saatini SS:DD formatında girin (Örn: 21:00).\n"
        "Vazgeçmek için 'g' veya 'q' yazıp Enter'a basabilirsiniz.[/dim]"
    )
    console.print(Panel(saat_paneli, title="⏰ 3. Adım: Yayın Saati Belirleyin", expand=False))

    while True:
        saat_girdisi = Prompt.ask("[bold green]Yayın Saati[/bold green]", default="21:00").strip()
        if saat_girdisi.lower() in ("g", "geri", "q", "iptal", "exit"):
            console.print("[dim yellow]İşlem iptal edildi, ana menüye dönülüyor.[/dim yellow]")
            return
        if re.fullmatch(r"^(?:[01]\d|2[0-3]):[0-5]\d$", saat_girdisi):
            secilen_saat = saat_girdisi
            break
        console.print("[bold red][HATA][/bold red] Lütfen saati [bold yellow]SS:DD[/bold yellow] formatında girin (Örn: 21:00, 20:30).")

    # 4. Adım: Yayın Bilgisi / Notu Belirleme
    console.print()
    bilgi_paneli = (
        f"[bold cyan]Yayın :[/bold cyan] [bold white]{secilen_yayin}[/bold white]\n"
        f"[bold cyan]Gün   :[/bold cyan] [bold white]{secilen_gun}[/bold white]\n"
        f"[bold cyan]Saat  :[/bold cyan] [bold white]{secilen_saat}[/bold white]\n\n"
        "[dim]Yayın hakkında ek bilgi veya not yazın (İsteğe bağlı).\n"
        "Eklemek istemiyorsanız doğrudan Enter'a basıp geçebilirsiniz.\n"
        "Vazgeçmek için 'g' veya 'q' yazabilirsiniz.[/dim]"
    )
    console.print(Panel(bilgi_paneli, title="📝 4. Adım: Bilgi / Not Ekleyin", expand=False))

    bilgi = Prompt.ask("[bold green]Bilgi[/bold green]", default="").strip()
    if bilgi.lower() in ("g", "geri"):
        console.print("[dim yellow]İşlem iptal edildi, ana menüye dönülüyor.[/dim yellow]")
        return

    # Mevcut takvim verilerini oku ve numaralandırarak ekle
    mevcut_yayinlar = takvim_oku()
    siradaki_no = len(mevcut_yayinlar) + 1
    if bilgi:
        yeni_satir = f"{siradaki_no}-) {secilen_yayin} - {secilen_gun} - {secilen_saat} | Bilgi: {bilgi}"
    else:
        yeni_satir = f"{siradaki_no}-) {secilen_yayin} - {secilen_gun} - {secilen_saat}"

    mevcut_yayinlar.append(yeni_satir)
    yeni_icerik = "\n".join(mevcut_yayinlar) + "\n"

    try:
        with open(TAKVIM_DOSYASI, "w", encoding="utf-8") as f:
            f.write(yeni_icerik)
        takvim_uzaga_gonder(yeni_icerik)
        console.print(f"\n[bold green]✓ Yayın takvime eklendi:[/bold green] [bold yellow]{yeni_satir}[/bold yellow]\n")
    except Exception as e:
        console.print(f"\n[bold red][HATA] Takvim kaydedilemedi: {e}[/bold red]\n")


def yayin_satiri_formatla(satir, numarayi_vurgula=False):
    """
    Takvim satırını zenginleştirilmiş metin (Rich formatı) olarak biçimlendirir.
    Örn: '1-) Canlı Yayın ✅ | Bilgi: Pazartesi 20:00'
    """
    if " | Bilgi: " in satir:
        ana_kisim, bilgi_kismi = satir.split(" | Bilgi: ", 1)
        bilgi_metni = f" [bold yellow]({bilgi_kismi.strip()})[/bold yellow]" if bilgi_kismi.strip() else ""
    else:
        ana_kisim, bilgi_metni = satir, ""

    if "-)" in ana_kisim:
        no, rest = ana_kisim.split("-)", 1)
        rest_metni = rest.strip()
        if "✅" in rest_metni:
            rest_metni = rest_metni.replace("✅", "[bold green]✅[/bold green]")
        if "❌" in rest_metni:
            rest_metni = rest_metni.replace("❌", "[bold red]❌[/bold red]")
        if numarayi_vurgula:
            return f"[bold cyan]{no}-)[/bold cyan] [bold white]{rest_metni}[/bold white]{bilgi_metni}"
        else:
            return f"[bold white]{no}-) {rest_metni}[/bold white]{bilgi_metni}"
    else:
        metin = ana_kisim
        if "✅" in metin:
            metin = metin.replace("✅", "[bold green]✅[/bold green]")
        if "❌" in metin:
            metin = metin.replace("❌", "[bold red]❌[/bold red]")
        return f"[bold white]{metin}[/bold white]{bilgi_metni}"


def yayin_listesi_metinleri_al(yayinlar, numarayi_vurgula=False):
    """Yayın listesindeki her bir satırı biçimlendirip liste olarak döndürür."""
    return [yayin_satiri_formatla(s, numarayi_vurgula=numarayi_vurgula) for s in yayinlar]


def yayin_iptal_et():
    """Kullanıcı 1 (Ufuk) için takvimdeki bir yayını iptal eder ve isminin yanına ❌ ekler."""
    yayinlar = takvim_oku()
    if not yayinlar:
        console.print("\n[dim yellow]Takvimde henüz planlanmış bir yayın bulunmuyor.[/dim yellow]\n")
        return

    console.print()
    yayin_metinleri = yayin_listesi_metinleri_al(yayinlar)

    panel_icerik = (
        "[bold cyan]Takvimdeki Mevcut Yayınlar:[/bold cyan]\n\n" +
        "\n".join(yayin_metinleri) + "\n\n"
        "[dim]İptal etmek istediğiniz yayının numarasını girin.\n"
        "(Geri dönmek için 'g' veya boş Enter basabilirsiniz)[/dim]"
    )
    console.print(Panel(panel_icerik, title="[bold red]❌ Yayın İptal", expand=False))

    # Terminal girdi tamponunda kalan karakterleri temizle
    if sys.stdin.isatty() and termios is not None:
        try:
            termios.tcflush(sys.stdin.fileno(), termios.TCIFLUSH)
        except Exception:
            pass

    girdi = Prompt.ask("[bold green]İptal edilecek yayın numarası[/bold green]", default="").strip()
    if not girdi or girdi.lower() in ("g", "geri", "q", "iptal", "exit"):
        console.print("[dim yellow]İşlem iptal edildi, ana menüye dönülüyor.[/dim yellow]")
        return

    try:
        secilen_no = int(girdi)
        if not (1 <= secilen_no <= len(yayinlar)):
            console.print(f"[bold red][HATA][/bold red] Lütfen 1 ile {len(yayinlar)} arasında bir numara girin.")
            return
    except ValueError:
        console.print("[bold red][HATA][/bold red] Geçerli bir sayı girmelisiniz.")
        return

    yeni_satirlar = []
    iptal_edilen_ad = ""

    for i, satir in enumerate(yayinlar, 1):
        if i == secilen_no:
            if "❌" in satir:
                console.print("\n[dim yellow]Bu yayın zaten iptal edilmiş olarak işaretli.[/dim yellow]\n")
                return
            satir_temiz = satir.replace(" ✅", "").replace("✅", "")
            bilgi_eki = ""
            ana_kisim = satir_temiz
            if " | Bilgi: " in satir_temiz:
                ana_kisim, bilgi_kismi = satir_temiz.split(" | Bilgi: ", 1)
                bilgi_eki = f" | Bilgi: {bilgi_kismi}"

            parts = ana_kisim.rsplit(" - ", 2)
            if len(parts) == 3:
                guncel_satir = f"{parts[0]} ❌ - {parts[1]} - {parts[2]}{bilgi_eki}"
                iptal_edilen_ad = parts[0]
            elif " - " in ana_kisim:
                parts = ana_kisim.rsplit(" - ", 1)
                guncel_satir = f"{parts[0]} ❌ - {parts[1]}{bilgi_eki}"
                iptal_edilen_ad = parts[0]
            else:
                guncel_satir = f"{ana_kisim} ❌{bilgi_eki}"
                iptal_edilen_ad = ana_kisim
            yeni_satirlar.append(guncel_satir)
        else:
            yeni_satirlar.append(satir)

    yeni_icerik = "\n".join(yeni_satirlar) + "\n"
    try:
        with open(TAKVIM_DOSYASI, "w", encoding="utf-8") as f:
            f.write(yeni_icerik)
        takvim_uzaga_gonder(yeni_icerik)
        console.print(f"\n[bold green]✓ {secilen_no} numaralı yayın iptal edildi olarak işaretlendi! (İsminin yanına ❌ eklendi)[/bold green]\n")
    except Exception as e:
        console.print(f"\n[bold red][HATA] Takvim kaydedilemedi: {e}[/bold red]\n")


def yayin_sil():
    """Takvimdeki bir yayını silme veya tüm listeyi temizleme sihirbazı."""
    # Terminal girdi tamponunda kalan karakterleri temizle
    if sys.stdin.isatty() and termios is not None:
        try:
            termios.tcflush(sys.stdin.fileno(), termios.TCIFLUSH)
        except Exception:
            pass

    yayinlar = takvim_oku()
    if not yayinlar:
        console.print("\n[dim yellow]Takvimde silinecek herhangi bir yayın bulunmuyor.[/dim yellow]\n")
        return

    console.print()
    yayin_metinleri = yayin_listesi_metinleri_al(yayinlar)

    panel_icerik = (
        "[bold cyan]Takvimdeki Mevcut Yayınlar:[/bold cyan]\n\n" +
        "\n".join(yayin_metinleri) + "\n\n"
        "[dim]• Silmek istediğiniz yayının numarasını girin (Örn: 1 veya 2)\n"
        "• Yayının adını da yazabilirsiniz (Örn: Haftalık, Memleket, Canlı Maç)\n"
        "• Tüm listeyi temizlemek için 'hepsi' yazın\n"
        "• Geri dönmek / iptal etmek için 'g' yazın[/dim]"
    )
    console.print(Panel(panel_icerik, title="[bold red]🗑️ Yayın Sil", expand=False))

    while True:
        girdi = Prompt.ask("[bold green]Silinecek yayın seçimi (No / Ad / 'hepsi' / 'g')[/bold green]").strip()
        if not girdi or girdi.lower() in ("g", "geri", "q", "iptal", "exit", "vazgec", "vazgeç"):
            console.print("[dim yellow]İşlem iptal edildi, ana menüye dönülüyor.[/dim yellow]")
            return

        # Hepsi seçeneği
        if girdi.lower() in ("hepsi", "tumu", "tümü", "all"):
            onay = Prompt.ask("[bold red]Tüm yayın takvimini tamamen silmek istediğinize emin misiniz? (e/h)[/bold red]", choices=["e", "h", "evet", "hayır"], default="h")
            if onay.lower() in ("e", "evet"):
                try:
                    with open(TAKVIM_DOSYASI, "w", encoding="utf-8") as f:
                        f.write("")
                    takvim_uzaga_gonder("")
                    console.print("\n[bold green]✓ Yayın takvimi tamamen temizlendi ve buluta eşitlendi.[/bold green]\n")
                except Exception as e:
                    console.print(f"\n[bold red][HATA] Takvim temizlenirken hata: {e}[/bold red]\n")
            else:
                console.print("[dim]İşlem iptal edildi.[/dim]")
            return

        # Numara veya metin eşleme
        silinecek_idx = None
        match_no = re.search(r"\b(\d+)\b", girdi)
        if match_no:
            val = int(match_no.group(1))
            if 1 <= val <= len(yayinlar):
                silinecek_idx = val - 1

        # Eğer sayı ile bulunamadıysa yayın adı eşleşmesi dene
        if silinecek_idx is None:
            g_low = girdi.lower()
            for idx, y in enumerate(yayinlar):
                if g_low in y.lower():
                    silinecek_idx = idx
                    break

        if silinecek_idx is None:
            console.print(f"[bold red][HATA][/bold red] Lütfen 1 ile {len(yayinlar)} arasında bir numara girin ya da 'hepsi' / 'g' yazın.")
            continue

        silinen_yayin = yayinlar.pop(silinecek_idx)
        # Numaralandırmayı 1'den başlayarak yeniden düzenle
        yeni_satirlar = []
        for yeni_no, satir in enumerate(yayinlar, 1):
            if "-)" in satir:
                _, rest = satir.split("-)", 1)
                yeni_satirlar.append(f"{yeni_no}-) {rest.strip()}")
            else:
                yeni_satirlar.append(f"{yeni_no}-) {satir.strip()}")

        yeni_icerik = "\n".join(yeni_satirlar) + ("\n" if yeni_satirlar else "")
        try:
            with open(TAKVIM_DOSYASI, "w", encoding="utf-8") as f:
                f.write(yeni_icerik)
            takvim_uzaga_gonder(yeni_icerik)
            console.print(f"\n[bold green]✓ Yayın takvimden silindi ve bulutla eşitlendi:[/bold green]\n  [bold red]- {silinen_yayin}[/bold red]\n")
        except Exception as e:
            console.print(f"\n[bold red][HATA] Takvim kaydedilemedi: {e}[/bold red]\n")
        return


def duyurulari_yapildi_isaretle():
    """Kullanıcı 2 (Yiğit) için yapılan/planlanan duyuruları işaretler ve takvime yeşil check sembolü ekler."""
    yayinlar = takvim_oku()
    if not yayinlar:
        console.print("\n[dim yellow]Takvimde henüz planlanmış bir yayın bulunmuyor.[/dim yellow]\n")
        return

    console.print()
    yayin_metinleri = yayin_listesi_metinleri_al(yayinlar)

    panel_icerik = (
        "[bold cyan]Takvimdeki Mevcut Yayınlar:[/bold cyan]\n\n" +
        "\n".join(yayin_metinleri) + "\n\n"
        "[dim]Yapılan / planlanan duyuruların numaralarını girin.\n"
        "Örnek: 1 veya 1-2 veya 1-2-3 veya 1,2,3 (Geri dönmek için 'g' veya boş Enter):[/dim]"
    )
    console.print(Panel(panel_icerik, title="[bold yellow]✅ Duyuruları Tamamla", expand=False))

    # Terminal girdi tamponunda kalan karakterleri temizle
    if sys.stdin.isatty() and termios is not None:
        try:
            termios.tcflush(sys.stdin.fileno(), termios.TCIFLUSH)
        except Exception:
            pass

    girdi = Prompt.ask("[bold green]Duyuru Numaraları[/bold green]", default="").strip()
    if not girdi or girdi.lower() in ("g", "geri", "q", "iptal", "exit"):
        console.print("[dim yellow]İşlem iptal edildi, ana menüye dönülüyor.[/dim yellow]")
        return

    secilen_nolar = set()
    if girdi.lower() in ("hepsi", "tumu", "tümü", "all"):
        secilen_nolar = set(range(1, len(yayinlar) + 1))
    else:
        for n_str in re.findall(r"\d+", girdi):
            secilen_nolar.add(int(n_str))

    if not secilen_nolar:
        console.print("[bold red][HATA][/bold red] Geçerli bir duyuru numarası bulunamadı.")
        return

    yeni_satirlar = []
    isaretlenenler = []

    for i, satir in enumerate(yayinlar, 1):
        if i in secilen_nolar:
            # Yayının adının sonuna yeşil check sembolü ekle; varsa eski ❌ iptal işaretini temizle
            satir_temiz = satir.replace(" ❌", "").replace("❌", "")
            if "✅" not in satir_temiz:
                bilgi_eki = ""
                ana_kisim = satir_temiz
                if " | Bilgi: " in satir_temiz:
                    ana_kisim, bilgi_kismi = satir_temiz.split(" | Bilgi: ", 1)
                    bilgi_eki = f" | Bilgi: {bilgi_kismi}"

                parts = ana_kisim.rsplit(" - ", 2)
                if len(parts) == 3:
                    guncel_satir = f"{parts[0]} ✅ - {parts[1]} - {parts[2]}{bilgi_eki}"
                elif " - " in ana_kisim:
                    parts = ana_kisim.rsplit(" - ", 1)
                    guncel_satir = f"{parts[0]} ✅ - {parts[1]}{bilgi_eki}"
                else:
                    guncel_satir = f"{ana_kisim} ✅{bilgi_eki}"
                yeni_satirlar.append(guncel_satir)
                isaretlenenler.append(i)
            else:
                yeni_satirlar.append(satir_temiz)
                isaretlenenler.append(i)
        else:
            yeni_satirlar.append(satir)

    if not isaretlenenler:
        console.print("[dim yellow]Belirtilen numaralar listede bulunamadı.[/dim yellow]")
        return

    yeni_icerik = "\n".join(yeni_satirlar) + "\n"
    try:
        with open(TAKVIM_DOSYASI, "w", encoding="utf-8") as f:
            f.write(yeni_icerik)
        takvim_uzaga_gonder(yeni_icerik)
        numaralar_str = ", ".join(str(n) for n in isaretlenenler)
        console.print(f"\n[bold green]✓ {numaralar_str} numaralı yayın(lar) için duyurular yapıldı olarak işaretlendi! (Yeşil check eklendi)[/bold green]\n")
    except Exception as e:
        console.print(f"\n[bold red][HATA] Takvim kaydedilemedi: {e}[/bold red]\n")


# =====================================================================
# CHAT SİSTEMİ
# =====================================================================
CHAT_DOSYASI = os.path.join(SCRIPT_DIR, "chat.txt")
CHAT_SYNC_DOSYASI = os.path.join(SCRIPT_DIR, ".chat_sync")
NTFY_TOPIC_CHAT = "tellal_chat_sync_u_y_8832"

def chat_filtrele(mesajlar):
    """Chat mesajlarından bot/yapay zeka bildirimlerini ayıklar; yalnızca gerçek ekip mesajlarını tutar."""
    if not mesajlar:
        return []
    temiz = []
    for m in mesajlar:
        if not m or not isinstance(m, str):
            continue
        m_str = m.strip()
        if not m_str:
            continue
        # Gemini AI bot bildirimlerini engelle
        if "Gemini AI" in m_str or m_str.startswith("Gemini AI:") or ("🤖" in m_str and "Gemini" in m_str):
            continue
        temiz.append(m_str)
    return temiz


def chat_senkronize_et(aktif_kullanici_adi=None):
    """Bulut veritabanından (Firebase RTDB) ve ntfy üzerinden en güncel chat verisini yerel chat.txt ile eşitler."""
    guncellendi = False

    # 1. Birincil: Firebase Realtime Database
    try:
        url_fb = f"{FIREBASE_DB_URL}/chat.json"
        res_fb = requests.get(url_fb, timeout=2.5)
        if res_fb.status_code == 200:
            data = res_fb.json()
            if isinstance(data, dict) and "mesajlar" in data:
                raw = data.get("mesajlar") or []
                if isinstance(raw, dict):
                    raw = list(raw.values())
                raw_mesajlar = [m for m in raw if m and isinstance(m, str) and m.strip()]
                mesajlar = chat_filtrele(raw_mesajlar)
                yeni_icerik = "\n".join(mesajlar) + ("\n" if mesajlar else "")

                # Eski içeriği oku
                eski_icerik = ""
                if os.path.exists(CHAT_DOSYASI):
                    try:
                        with open(CHAT_DOSYASI, "r", encoding="utf-8") as f:
                            eski_icerik = f.read()
                    except Exception:
                        eski_icerik = ""

                # macOS sesli bildirimi (karşı taraftan yeni mesaj geldiyse)
                if platform.system() == "Darwin" and aktif_kullanici_adi and yeni_icerik != eski_icerik and mesajlar:
                    son_satir = mesajlar[-1]
                    diger_kullanici = "Yiğit" if aktif_kullanici_adi == "Ufuk" else "Ufuk"
                    if son_satir.startswith(f"{diger_kullanici}:") or son_satir.startswith("3. Kullanıcı:") or son_satir.startswith("Cem:") or son_satir.startswith("Cem Yıldırım:"):
                        try:
                            temiz = son_satir.replace('"', "'")
                            subprocess.run(
                                ["osascript", "-e", f'display notification "{temiz}" with title "Corvus Chat" sound name "Glass"'],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL
                            )
                        except Exception:
                            pass

                with open(CHAT_DOSYASI, "w", encoding="utf-8") as f:
                    f.write(yeni_icerik)
                guncellendi = True
    except Exception:
        pass

    # 2. İkincil / Fallback: Ntfy
    if not guncellendi:
        son_zaman = 0
        if os.path.exists(CHAT_SYNC_DOSYASI):
            try:
                with open(CHAT_SYNC_DOSYASI, "r", encoding="utf-8") as f:
                    c = f.read().strip()
                    if c.isdigit():
                        son_zaman = int(c)
            except Exception:
                son_zaman = 0

        url = f"https://ntfy.sh/{NTFY_TOPIC_CHAT}/json?poll=1&since=all"
        try:
            r = requests.get(url, timeout=2.5)
            if r.status_code == 200 and r.text.strip():
                en_yeni_mesaj = None
                ilk_son_zaman = son_zaman
                for line in r.text.strip().split("\n"):
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                        if d.get("event") == "message":
                            m_time = d.get("time", 0)
                            if m_time >= son_zaman:
                                en_yeni_mesaj = d
                                son_zaman = m_time
                    except Exception:
                        continue

                if en_yeni_mesaj is not None:
                    icerik = en_yeni_mesaj.get("message", "")
                    if icerik == "__BOS_CHAT__":
                        icerik = ""
                    temiz_satirlar = chat_filtrele(icerik.split("\n"))
                    icerik = "\n".join(temiz_satirlar) + ("\n" if temiz_satirlar else "")

                    with open(CHAT_DOSYASI, "w", encoding="utf-8") as f:
                        f.write(icerik)
                    with open(CHAT_SYNC_DOSYASI, "w", encoding="utf-8") as f:
                        f.write(str(son_zaman))
        except Exception:
            pass


def chat_uzaga_gonder(icerik):
    """Güncellenmiş chat.txt içeriğini Firebase Realtime Database'e ve ntfy üzerine kaydeder."""
    ham_mesajlar = [s.strip() for s in icerik.strip().split("\n") if s.strip()]
    mesajlar = chat_filtrele(ham_mesajlar)
    temiz_icerik = "\n".join(mesajlar) + ("\n" if mesajlar else "")

    # 1. Birincil: Firebase Realtime Database
    try:
        url_fb = f"{FIREBASE_DB_URL}/chat.json"
        payload_fb = {
            "mesajlar": mesajlar,
            "son_guncelleme": int(datetime.now(timezone.utc).timestamp())
        }
        requests.put(url_fb, json=payload_fb, timeout=3.5)
    except Exception:
        pass

    # 2. İkincil: Ntfy
    try:
        mesaj = temiz_icerik if temiz_icerik.strip() else "__BOS_CHAT__"
        payload = {
            "topic": NTFY_TOPIC_CHAT,
            "title": "Corvus Chat Güncellemesi",
            "message": mesaj,
            "priority": 3,
            "tags": ["speech_balloon"]
        }
        r = requests.post("https://ntfy.sh", json=payload, timeout=3.5)
        if r.status_code == 200:
            try:
                res_data = r.json()
                t = res_data.get("time")
                if t:
                    with open(CHAT_SYNC_DOSYASI, "w", encoding="utf-8") as f:
                        f.write(str(t))
            except Exception:
                pass
    except Exception:
        pass


def chat_oku(aktif_kullanici_adi=None):
    """Chat dosyasını senkronize edip satır satır liste olarak döndürür."""
    chat_senkronize_et(aktif_kullanici_adi)
    if not os.path.exists(CHAT_DOSYASI):
        return []
    try:
        with open(CHAT_DOSYASI, "r", encoding="utf-8") as f:
            satirlar = [satir.strip() for satir in f if satir.strip()]
            return chat_filtrele(satirlar)
    except Exception:
        return []


def veri_temizligi_yap():
    """Program açılışında takvim.txt ve chat.txt dosyalarını Gemini AI yapay satırlarından arındırır ve bulutla eşitler."""
    try:
        if os.path.exists(TAKVIM_DOSYASI):
            with open(TAKVIM_DOSYASI, "r", encoding="utf-8") as f:
                satirlar = f.read().splitlines()
            temiz = takvim_filtrele_ve_duzenle(satirlar)
            if len(temiz) != len(satirlar):
                icerik = "\n".join(temiz) + ("\n" if temiz else "")
                with open(TAKVIM_DOSYASI, "w", encoding="utf-8") as f:
                    f.write(icerik)
                takvim_uzaga_gonder(icerik, guncelleyen="Sistem (Temizlik)")
        if os.path.exists(CHAT_DOSYASI):
            with open(CHAT_DOSYASI, "r", encoding="utf-8") as f:
                c_satirlar = f.read().splitlines()
            c_temiz = chat_filtrele(c_satirlar)
            if len(c_temiz) != len(c_satirlar):
                c_icerik = "\n".join(c_temiz) + ("\n" if c_temiz else "")
                with open(CHAT_DOSYASI, "w", encoding="utf-8") as f:
                    f.write(c_icerik)
                chat_uzaga_gonder(c_icerik)
    except Exception:
        pass


def formatli_chat_satiri(satir):
    """Chat satırını WhatsApp renkleri (Ufuk: cyan, Yiğit: magenta, Cem: yellow) ile biçimlendirir."""
    satir_str = satir.strip()
    if satir_str.startswith("Ufuk:"):
        _, msg = satir_str.split("Ufuk:", 1)
        return f"[bold cyan]Ufuk:[/bold cyan] [bold white]{escape(msg.strip())}[/bold white]"
    elif satir_str.startswith("Yiğit:") or satir_str.startswith("Yigit:"):
        prefix = "Yiğit:" if satir_str.startswith("Yiğit:") else "Yigit:"
        _, msg = satir_str.split(prefix, 1)
        return f"[bold magenta]Yiğit:[/bold magenta] [bold white]{escape(msg.strip())}[/bold white]"
    elif satir_str.startswith("Cem Yıldırım:") or satir_str.startswith("Cem:"):
        prefix = "Cem Yıldırım:" if satir_str.startswith("Cem Yıldırım:") else "Cem:"
        _, msg = satir_str.split(prefix, 1)
        return f"[bold yellow]{prefix}[/bold yellow] [bold white]{escape(msg.strip())}[/bold white]"
    return f"[bold white]{escape(satir_str)}[/bold white]"


def chat_mesaj_gonder(kullanici_id, kullanici_adi):
    """Kullanıcının chat kutusuna mesaj göndermesini sağlar."""
    diger_adi = "Yiğit" if kullanici_id == "1" else "Ufuk"

    console.print()
    mesajlar = chat_oku(kullanici_adi)
    if mesajlar:
        formatli = [formatli_chat_satiri(s) for s in mesajlar[-10:]]
        sohbet_gecmisi = "\n".join(formatli) + "\n\n"
    else:
        sohbet_gecmisi = "[dim]Henüz sohbet mesajı yok.[/dim]\n\n"

    panel_metni = (
        sohbet_gecmisi +
        f"[dim]• Mesajınızı yazıp Enter'a basın.\n"
        f"• Mesajınız ana ekrandaki Chat kutusunda görünecektir.\n"
        f"• Geri dönmek / vazgeçmek için 'g' yazın veya boş Enter'a basın.[/dim]"
    )
    console.print(Panel(panel_metni, title=f"[bold yellow]💬 Chat ({diger_adi} ile Sohbet)", expand=False))

    # Terminal girdi tamponunda kalan karakterleri temizle
    if sys.stdin.isatty() and termios is not None:
        try:
            termios.tcflush(sys.stdin.fileno(), termios.TCIFLUSH)
        except Exception:
            pass

    mesaj = Prompt.ask(f"[bold green]{kullanici_adi}[/bold green]", default="").strip()

    if not mesaj or mesaj.lower() in ("g", "geri", "q", "iptal", "exit"):
        console.print("[dim yellow]İşlem iptal edildi, ana menüye dönülüyor.[/dim yellow]")
        return

    # Gizli sohbet geçmişi temizleme komutu
    if mesaj.lower() in ("/temizle", "/clear"):
        try:
            with open(CHAT_DOSYASI, "w", encoding="utf-8") as f:
                f.write("")
            chat_uzaga_gonder("")
            console.print("\n[bold green]✓ Sohbet geçmişi temizlendi.[/bold green]\n")
            return
        except Exception as e:
            console.print(f"\n[bold red][HATA] Sohbet temizlenemedi: {e}[/bold red]\n")
            return

    # Tek satır olarak hazırla
    mesaj = mesaj.replace("\n", " ").strip()
    yeni_satir = f"{kullanici_adi}: {mesaj}"
    mevcut = []
    if os.path.exists(CHAT_DOSYASI):
        try:
            with open(CHAT_DOSYASI, "r", encoding="utf-8") as f:
                mevcut = [line.strip() for line in f if line.strip()]
        except Exception:
            mevcut = []

    mevcut.append(yeni_satir)
    if len(mevcut) > 50:
        mevcut = mevcut[-50:]

    yeni_icerik = "\n".join(mevcut) + "\n"
    try:
        with open(CHAT_DOSYASI, "w", encoding="utf-8") as f:
            f.write(yeni_icerik)
        chat_uzaga_gonder(yeni_icerik)
        console.print(f"\n[bold green]✓ Mesaj gönderildi![/bold green]\n")
    except Exception as e:
        console.print(f"\n[bold red][HATA] Mesaj kaydedilemedi: {e}[/bold red]\n")


def chat_temizle():
    """Kullanıcı 1 (Ufuk) için chat geçmişini (chat.txt) temizler ve senkronize eder."""
    console.print()
    if not os.path.exists(CHAT_DOSYASI):
        console.print("[dim yellow]Zaten silinecek bir sohbet geçmişi bulunmuyor.[/dim yellow]")
        return

    try:
        with open(CHAT_DOSYASI, "r", encoding="utf-8") as f:
            icerik = f.read().strip()
        if not icerik:
            console.print("[dim yellow]Sohbet geçmişi zaten boş.[/dim yellow]")
            return
    except Exception:
        pass

    panel_metni = (
        "[bold red]Tüm sohbet geçmişi (chat.txt) kalıcı olarak silinecektir.[/bold red]\n\n"
        "[dim]Bu işlem her iki tarafın (Ufuk & Yiğit) ekranındaki sohbet kutusunu temizler.[/dim]"
    )
    console.print(Panel(panel_metni, title="[bold red]🗑️ Chat'i Sil[/bold red]", expand=False))

    onay = Confirm.ask("[bold red]Sohbet geçmişini silmek istediğinize emin misiniz?[/bold red]", default=False)
    if not onay:
        console.print("[dim yellow]İşlem iptal edildi, ana menüye dönülüyor.[/dim yellow]")
        return

    try:
        with open(CHAT_DOSYASI, "w", encoding="utf-8") as f:
            f.write("")
        chat_uzaga_gonder("")
        console.print("\n[bold green]✓ Chat geçmişi başarıyla silindi ve temizlendi.[/bold green]\n")
    except Exception as e:
        console.print(f"\n[bold red][HATA] Chat silinemedi: {e}[/bold red]\n")


# =====================================================================
# ANA MENÜ
# =====================================================================
def ana_menu_secim_al(prompt_metni, gecerli_secimler):
    """
    Ana menü için özel girdi alıcı.
    Kullanıcı 'r' veya 'R' tuşuna bastığında ekrana hiçbir şey yazdırmadan (r bir yere yazılmadan)
    anında 'r' döndürür ve yenilemeyi tetikler.
    Diğer seçimler için karakter ekrana yazılır ve Enter ile onaylanır.
    """
    if not sys.stdin.isatty() or termios is None or tty is None:
        return Prompt.ask(prompt_metni, choices=gecerli_secimler).lower()

    console.print(prompt_metni, end=" ")
    sys.stdout.flush()

    fd = sys.stdin.fileno()
    eski_ayarlar = termios.tcgetattr(fd)
    buffer = ""
    try:
        tty.setcbreak(fd)
        while True:
            ch = sys.stdin.read(1)
            # Ctrl+C kontrolü
            if ch == "\x03":
                raise KeyboardInterrupt

            # Henüz hiçbir şey yazılmamışken r veya R tuşuna basıldıysa:
            # "r bir yere yazılmasın r ye hiçbir text box içinde değilken basıldığında..."
            if ch in ("r", "R") and len(buffer) == 0:
                # Ekrana r yazılmadan anında 'r' olarak döndür
                return "r"

            # Enter basıldıysa:
            if ch in ("\r", "\n"):
                secim = buffer.strip().lower()
                if secim in gecerli_secimler:
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    return secim
                elif not secim:
                    continue
                else:
                    sys.stdout.write(f"\n[Geçersiz seçim: {secim}]\n")
                    sys.stdout.flush()
                    buffer = ""
                    console.print(prompt_metni, end=" ")
                    sys.stdout.flush()
                    continue

            # Backspace / Silme:
            if ch in ("\x7f", "\x08"):
                if len(buffer) > 0:
                    buffer = buffer[:-1]
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
                continue

            # Normal yazılabilir karakterler (1, 2, 3... k vs):
            if ch.isprintable() and len(ch) == 1:
                buffer += ch
                sys.stdout.write(ch)
                sys.stdout.flush()
    finally:
        try:
            termios.tcflush(fd, termios.TCIFLUSH)
        except Exception:
            pass
        termios.tcsetattr(fd, termios.TCSADRAIN, eski_ayarlar)


def ana_menu_paneli_olustur(kullanici_id):
    """Kullanıcıya özel ana menü panelini ve geçerli seçim listesini oluşturur."""
    if kullanici_id == "1":
        menu = f"""[bold cyan]1.[/bold cyan] Uykusuz Tosba Duyuru Sistemi
[bold cyan]2.[/bold cyan] Radio Mocas Duyuru Sistemi
[bold cyan]3.[/bold cyan] Chat 💬
[bold cyan]4.[/bold cyan] Chat'i Sil... 🗑️
[bold cyan]5.[/bold cyan] Yayın Ekle... 📅
[bold cyan]6.[/bold cyan] Yayın İptal... ❌
[bold cyan]7.[/bold cyan] Yayın Sil... 🗑️
[bold cyan]8.[/bold cyan] Thumbnail Oluştur (Photoshop) 🎨
[bold cyan]9.[/bold cyan] Çıkış

[dim cyan]Chat Refresh Yenile(R)[/dim cyan]"""
        gecerli_secimler = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "k", "r", "t"]
    else:
        menu = f"""[bold cyan]1.[/bold cyan] Uykusuz Tosba Duyuru Sistemi
[bold cyan]2.[/bold cyan] Radio Mocas Duyuru Sistemi
[bold cyan]3.[/bold cyan] Chat 💬
[bold cyan]4.[/bold cyan] Duyurular Yapıldı ✅
[bold cyan]5.[/bold cyan] Yayın Ekle... 📅
[bold cyan]6.[/bold cyan] Yayın İptal... ❌
[bold cyan]7.[/bold cyan] Yayın Sil... 🗑️
[bold cyan]8.[/bold cyan] Thumbnail Oluştur (Photoshop) 🎨
[bold cyan]9.[/bold cyan] Çıkış

[dim cyan]Chat Refresh Yenile(R)[/dim cyan]"""
        gecerli_secimler = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "k", "r", "t"]

    return Panel(menu, title=f"[bold yellow]▶️  Youtube Duyuru Sistemi [cyan]v{SURUM}[/cyan]", expand=False), gecerli_secimler


def gelecek_yayinlar_paneli_olustur():
    """Takvimdeki gelecek yayınları gösteren kutu panelini oluşturur."""
    yayin_listesi = takvim_oku()
    if yayin_listesi:
        formatli_satirlar = yayin_listesi_metinleri_al(yayin_listesi, numarayi_vurgula=True)
        liste_metni = "\n".join(formatli_satirlar)
    else:
        liste_metni = "[dim]Henüz planlanmış bir yayın yok.[/dim]"
    return Panel(liste_metni, title="[bold yellow]📅 Gelecek Yayınlar[/bold yellow]", expand=False)


def chat_paneli_olustur(kullanici_adi):
    """Ana menü altındaki son chat mesajları panelini oluşturur."""
    chat_mesajlari = chat_oku(kullanici_adi)
    if chat_mesajlari:
        formatli_chat = [formatli_chat_satiri(s) for s in chat_mesajlari[-12:]]
        chat_metni = "\n".join(formatli_chat)
    else:
        chat_metni = "[dim]Henüz sohbet mesajı yok.[/dim]"
    return Panel(chat_metni, title="[bold yellow]💬 Chat[/bold yellow]", expand=False)


def uygulamadan_cik():
    """Programdan çıkış yapar ve gerekirse macOS Terminal penceresini kapatır."""
    console.print("[bold yellow]Çıkış yapılıyor...[/bold yellow]")
    if platform.system() == "Darwin":
        try:
            subprocess.run(
                ["osascript", "-e", 'tell application "Terminal" to close front window saving no'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass


def ana_menu(kullanici_id, kullanici_adi):
    """Ana menü arayüzü ve işlem yönlendiricisi."""
    yenilendi_mesaji = False
    while True:
        banner_yazdir()
        console.print(f"[bold green]👤 Aktif Kullanıcı:[/bold green] [bold yellow]{kullanici_adi}[/bold yellow]  [dim](Değiştirmek için 'k')[/dim]")
        if yenilendi_mesaji:
            console.print("[bold green]✓[/bold green] [dim cyan]Yayın durumu ve Chat yenilendi.[/dim cyan]")
            yenilendi_mesaji = False

        # Karşı taraftan yeni bir bildirim var mı diye sessizce kontrol et
        bildirimleri_kontrol_et(kullanici_id)

        # 1. Kutu: Ana Menü
        menu_paneli, gecerli_secimler = ana_menu_paneli_olustur(kullanici_id)
        console.print(menu_paneli)

        # 2. Kutu: Gelecek Yayınlar
        console.print(gelecek_yayinlar_paneli_olustur())

        # 3. Kutu: Chat
        console.print(chat_paneli_olustur(kullanici_adi))

        ana_secim = ana_menu_secim_al("[bold green]Seçim yapın[/bold green]", gecerli_secimler)

        # R tuşuna basıldığında yayın durumu, chat ve bildirimleri anında yenile (API çağrıları hariç)
        if ana_secim == "r":
            takvim_senkronize_et()
            chat_senkronize_et(kullanici_adi)
            bildirimleri_kontrol_et(kullanici_id)
            yenilendi_mesaji = True
            continue

        if kullanici_id == "1":
            if ana_secim == "9":
                uygulamadan_cik()
                break
            elif ana_secim == "1":
                uykusuz_tosba_menu()
            elif ana_secim == "2":
                radio_mocas_menu()
            elif ana_secim == "3":
                chat_mesaj_gonder(kullanici_id, kullanici_adi)
            elif ana_secim == "4":
                chat_temizle()
            elif ana_secim == "5":
                takvime_yayin_ekle()
            elif ana_secim == "6":
                yayin_iptal_et()
            elif ana_secim == "7":
                yayin_sil()
            elif ana_secim in ("8", "t"):
                thumbnail_ana_menusu()
            elif ana_secim == "k":
                kullanici_id, kullanici_adi = kullanici_degistir()
                console.print(Panel(f"[bold green]✨ Hoş geldin {kullanici_adi}![/bold green]", expand=False))
                bildirimleri_kontrol_et(kullanici_id)
        else:
            if ana_secim == "9":
                uygulamadan_cik()
                break
            elif ana_secim == "1":
                uykusuz_tosba_menu()
            elif ana_secim == "2":
                radio_mocas_menu()
            elif ana_secim == "3":
                chat_mesaj_gonder(kullanici_id, kullanici_adi)
            elif ana_secim == "4":
                duyurulari_yapildi_isaretle()
            elif ana_secim == "5":
                takvime_yayin_ekle()
            elif ana_secim == "6":
                yayin_iptal_et()
            elif ana_secim == "7":
                yayin_sil()
            elif ana_secim in ("8", "t"):
                thumbnail_ana_menusu()
            elif ana_secim == "k":
                kullanici_id, kullanici_adi = kullanici_degistir()
                console.print(Panel(f"[bold green]✨ Hoş geldin {kullanici_adi}![/bold green]", expand=False))
                bildirimleri_kontrol_et(kullanici_id)




if __name__ == "__main__":
    masaustu_app_olustur()
    guncelleme_kontrol()
    veri_temizligi_yap()
    yenilikleri_goster()
    k_id, k_ad = kullanici_belirle()
    console.print(Panel(f"[bold green]✨ Hoş geldin {k_ad}![/bold green]", expand=False))
    bildirimleri_kontrol_et(k_id)
    ana_menu(k_id, k_ad)



