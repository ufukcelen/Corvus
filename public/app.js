/**
 * Tellal Cloud Web Portal - JavaScript Logic
 * Firebase Hosting & Ntfy Realtime Sync Desteği
 */

// Global State
const NTFY_TOPIC_TAKVIM = "tellal_takvim_sync_u_y_8832";
const STORAGE_KEY_TAKVIM = "tellal_web_takvim";
const STORAGE_KEY_USER = "tellal_web_user";

const savedUser = localStorage.getItem(STORAGE_KEY_USER);
let state = {
  currentUser: (savedUser && savedUser !== "3. Kullanıcı (Editör)") ? savedUser : "Cem Yıldırım",
  yayinlar: [],
  geminiMatches: [],
  activeFilter: "all",
  searchQuery: "",
  isSyncing: false,
  lastSyncTime: 0,
  calendarYear: new Date().getFullYear(),
  calendarMonth: new Date().getMonth()
};

let chatState = {
  mesajlar: [],
  lastRaw: "",
  isSending: false
};

// DOM Yüklendiğinde Başlat
document.addEventListener("DOMContentLoaded", () => {
  initUser();
  initCalendarData();
  setupEventListeners();
  startNtfyPolling();
  initMonthCalendar();
  initChat();
  checkGeminiAiAutoRun();
  updateClock();
  setInterval(updateClock, 1000);
});

// 1. Kullanıcı Yönetimi
function initUser() {
  const userElem = document.getElementById("activeUserName");
  if (userElem) userElem.textContent = state.currentUser;
  const chatLabel = document.getElementById("chatActiveUserLabel");
  if (chatLabel) chatLabel.textContent = state.currentUser;
  const chatInput = document.getElementById("chatInput");
  if (chatInput) chatInput.placeholder = `${state.currentUser} olarak ekip arkadaşlarına mesaj yaz...`;
}

function switchUser() {
  const current = state.currentUser;
  const yeniAd = prompt("Aktif Kullanıcı İsminizi Girin (Örn: Cem Yıldırım, Ufuk, Yiğit):", current);
  if (yeniAd && yeniAd.trim()) {
    state.currentUser = yeniAd.trim();
    localStorage.setItem(STORAGE_KEY_USER, state.currentUser);
    initUser();
    showToast(`Aktif kullanıcı "${state.currentUser}" olarak güncellendi.`, "info");
  }
}

// 2. Takvim Verisi Yükleme & Parse Etme
async function initCalendarData() {
  const localData = localStorage.getItem(STORAGE_KEY_TAKVIM);
  if (localData) {
    try {
      state.yayinlar = JSON.parse(localData);
      // Yayın takviminde kalmış olabilecek eski Gemini bot satırlarını ayıkla
      state.yayinlar = state.yayinlar.filter(y => !(y.includes("Gemini AI") || y.includes("[Gemini AI]")));
    } catch (e) {
      state.yayinlar = [];
    }
  }

  // Gemini AI Maçlarını localStorage'dan veya varsayılan fikstürden yükle (Normal Takvim gridi için)
  const localMatches = localStorage.getItem("tellal_gemini_matches");
  if (localMatches) {
    try {
      state.geminiMatches = JSON.parse(localMatches);
    } catch (e) {
      state.geminiMatches = [...GEMINI_AI_FIXTURES];
    }
  } else {
    state.geminiMatches = [...GEMINI_AI_FIXTURES];
  }

  renderCalendar();
  updateStats();
  renderMonthCalendar();

  // Doğrudan Firebase Bulut Veritabanından en güncel veriyi çek ve eşitle
  await senkronizeEtUzak(false);
  await senkronizeGeminiMatches();
  checkGeminiAiAutoRun();
}

function kaydetYerel() {
  localStorage.setItem(STORAGE_KEY_TAKVIM, JSON.stringify(state.yayinlar));
}

// Satır Parse Fonksiyonu
function parseYayinSatiri(satir, index) {
  let temizSatir = satir.trim();
  let no = index + 1;
  let isDone = temizSatir.includes("✅");
  let isCanceled = temizSatir.includes("❌");
  
  let bilgi = "";
  if (temizSatir.includes(" | Bilgi: ")) {
    const parts = temizSatir.split(" | Bilgi: ");
    temizSatir = parts[0];
    bilgi = parts[1].trim();
  }

  // Numarayı ayıkla (1-) vs.)
  if (temizSatir.includes("-)")) {
    const noParts = temizSatir.split("-)");
    no = parseInt(noParts[0].trim()) || (index + 1);
    temizSatir = noParts[1].trim();
  }

  // Durum sembollerini metinden temizle
  temizSatir = temizSatir.replace("✅", "").replace("❌", "").trim();

  // "Yayın Adı - Gün - Saat" ayrıştırması
  let yayinAdi = temizSatir;
  let gun = "Belirtilmedi";
  let saat = "20:00";

  if (temizSatir.includes(" - ")) {
    const segmentler = temizSatir.split(" - ");
    if (segmentler.length >= 3) {
      saat = segmentler[segmentler.length - 1].trim();
      gun = segmentler[segmentler.length - 2].trim();
      yayinAdi = segmentler.slice(0, -2).join(" - ").trim();
    } else if (segmentler.length === 2) {
      gun = segmentler[1].trim();
      yayinAdi = segmentler[0].trim();
    }
  }

  // Kanal Belirleme
  let kanal = "Uykusuz Tosba";
  const lowerAdi = yayinAdi.toLowerCase();
  if (lowerAdi.includes("memleket") || lowerAdi.includes("albert") || lowerAdi.includes("mocas") || lowerAdi.includes("film")) {
    kanal = "Radio Mocas";
  }

  return {
    raw: satir,
    index: index,
    no: no,
    yayinAdi: yayinAdi,
    kanal: kanal,
    gun: gun,
    saat: saat,
    bilgi: bilgi,
    isDone: isDone,
    isCanceled: isCanceled
  };
}

// 3. Takvimi Render Etme (Glassmorphism Cards)
function renderCalendar() {
  const container = document.getElementById("broadcastListContainer");
  const countBadge = document.getElementById("broadcastCountBadge");
  if (!container) return;

  const parsedItems = state.yayinlar.map((s, i) => parseYayinSatiri(s, i));

  // Filtreleme
  let filtered = parsedItems.filter(item => {
    // Arama
    if (state.searchQuery) {
      const q = state.searchQuery.toLowerCase();
      const matchTitle = item.yayinAdi.toLowerCase().includes(q);
      const matchNote = item.bilgi.toLowerCase().includes(q);
      const matchDay = item.gun.toLowerCase().includes(q);
      if (!matchTitle && !matchNote && !matchDay) return false;
    }

    // Tab Filtresi
    if (state.activeFilter === "tosba") return item.kanal === "Uykusuz Tosba";
    if (state.activeFilter === "mocas") return item.kanal === "Radio Mocas";
    if (state.activeFilter === "done") return item.isDone;
    if (state.activeFilter === "canceled") return item.isCanceled;
    return true;
  });

  if (countBadge) countBadge.textContent = `${filtered.length} Yayın`;

  if (filtered.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">📅</div>
        <h3>Eşleşen Yayın Bulunamadı</h3>
        <p>Arama kriterlerinize veya seçilen filtreye uygun planlanmış bir yayın yok.</p>
        <button class="btn btn-primary btn-sm" onclick="openAddModal()">+ Yeni Yayın Ekle</button>
      </div>
    `;
    renderMonthCalendar();
    return;
  }

  container.innerHTML = filtered.map(item => {
    const channelClass = item.kanal === "Uykusuz Tosba" ? "channel-tosba" : "channel-mocas";
    let statusClass = "";
    let pillHtml = `<span class="status-pill pill-planned">⏳ Planlandı</span>`;

    if (item.isDone) {
      statusClass = "status-done";
      pillHtml = `<span class="status-pill pill-done">✓ Duyuruldu</span>`;
    } else if (item.isCanceled) {
      statusClass = "status-canceled";
      pillHtml = `<span class="status-pill pill-canceled">✕ İptal</span>`;
    }

    return `
      <div class="broadcast-card ${statusClass}" data-index="${item.index}">
        <div class="card-left">
          <div class="card-number">${item.no}</div>
          <div class="card-main-info">
            <div class="card-title-row">
              <span class="card-title">${escapeHtml(item.yayinAdi)}</span>
              <span class="channel-tag ${channelClass}">${item.kanal}</span>
            </div>
            <div class="card-meta-row">
              <span class="meta-item">🗓️ ${escapeHtml(item.gun)}</span>
              <span class="meta-item">⏰ ${escapeHtml(item.saat)}</span>
              ${item.bilgi ? `<span class="meta-info-note">💬 ${escapeHtml(item.bilgi)}</span>` : ""}
            </div>
          </div>
        </div>

        <div class="card-right">
          ${pillHtml}
          <div class="card-actions">
            <button class="action-icon-btn done-btn" title="Duyuruldu / Tamamlandı Olarak İşaretle" onclick="toggleYayinDurumu(${item.index}, 'done')">
              ✓
            </button>
            <button class="action-icon-btn cancel-btn" title="Yayını İptal Et (❌)" onclick="toggleYayinDurumu(${item.index}, 'cancel')">
              ✕
            </button>
            <button class="action-icon-btn delete-btn" title="Yayını Takvimden Sil" onclick="silYayin(${item.index})">
              🗑️
            </button>
          </div>
        </div>
      </div>
    `;
  }).join("");

  renderMonthCalendar();
}

// 4. İstatistikleri Güncelleme
function updateStats() {
  const parsed = state.yayinlar.map((s, i) => parseYayinSatiri(s, i));
  const total = parsed.length;
  const done = parsed.filter(p => p.isDone).length;
  const canceled = parsed.filter(p => p.isCanceled).length;
  const active = parsed.filter(p => !p.isDone && !p.isCanceled).length;

  const totalElem = document.getElementById("statTotalBroadcasts");
  const doneElem = document.getElementById("statDoneBroadcasts");
  const canceledElem = document.getElementById("statCanceledBroadcasts");
  const activeElem = document.getElementById("statActiveBroadcasts");

  if (totalElem) totalElem.textContent = total;
  if (doneElem) doneElem.textContent = done;
  if (canceledElem) canceledElem.textContent = canceled;
  if (activeElem) activeElem.textContent = active;
}

// 5. Yeni Yayın Ekleme
function yeniYayinKaydet(e) {
  e.preventDefault();
  const form = document.getElementById("addBroadcastForm");
  const kanal = document.getElementById("inputKanal").value;
  const selectElem = document.getElementById("inputProgramSelect");
  let program = selectElem ? selectElem.value.trim() : "";
  if (program === "__CUSTOM__") {
    const customInput = document.getElementById("inputCustomProgram");
    program = customInput ? customInput.value.trim() : "";
  }
  const gun = document.getElementById("inputGun").value.trim();
  const saat = document.getElementById("inputSaat").value.trim();
  const bilgi = document.getElementById("inputBilgi").value.trim();

  if (!program || !gun || !saat) {
    showToast("Lütfen program, gün ve saat alanlarını doldurun.", "warning");
    return;
  }

  const siradakiNo = state.yayinlar.length + 1;
  let yeniSatir = `${siradakiNo}-) ${program} - ${gun} - ${saat}`;
  if (bilgi) {
    yeniSatir += ` | Bilgi: ${bilgi}`;
  }

  state.yayinlar.push(yeniSatir);
  kaydetYerel();
  renderCalendar();
  updateStats();
  closeAddModal();
  form.reset();
  guncelleProgramListesi();

  // Ntfy üzerinden buluta ve masaüstü tellal.py'ye aktar!
  yayinlariBulutaGonder(`${state.currentUser} webden yeni yayın ekledi: ${program}`);
  showToast(`✓ "${program}" yayını başarıyla takvime eklendi ve Tellal Cloud'a senkronize edildi!`, "success");
}

// 6. Yayın Durumu Değiştirme (Tamamla / İptal)
function toggleYayinDurumu(index, action) {
  if (index < 0 || index >= state.yayinlar.length) return;
  let satir = state.yayinlar[index];

  // Ek bilgi kısmını ayır
  let bilgiEki = "";
  let anaSatir = satir;
  if (satir.includes(" | Bilgi: ")) {
    const parts = satir.split(" | Bilgi: ");
    anaSatir = parts[0];
    bilgiEki = ` | Bilgi: ${parts.slice(1).join(" | Bilgi: ")}`;
  }

  // Mevcut durum simgelerini temizle
  let temizAna = anaSatir.replace(/ ✅/g, "").replace(/✅/g, "").replace(/ ❌/g, "").replace(/❌/g, "").trim();

  if (action === "done") {
    if (satir.includes("✅")) {
      satir = `${temizAna}${bilgiEki}`;
      showToast("Duyuru işareti kaldırıldı.", "info");
    } else {
      const parts = temizAna.split(" - ");
      if (parts.length >= 3) {
        const saat = parts[parts.length - 1].trim();
        const gun = parts[parts.length - 2].trim();
        const yayinAdi = parts.slice(0, -2).join(" - ").trim();
        satir = `${yayinAdi} ✅ - ${gun} - ${saat}${bilgiEki}`;
      } else if (parts.length === 2) {
        satir = `${parts[0].trim()} ✅ - ${parts[1].trim()}${bilgiEki}`;
      } else {
        satir = `${temizAna} ✅${bilgiEki}`;
      }
      showToast("✓ Yayın duyurusu tamamlandı olarak işaretlendi!", "success");
    }
  } else if (action === "cancel") {
    if (satir.includes("❌")) {
      satir = `${temizAna}${bilgiEki}`;
      showToast("İptal işareti kaldırıldı.", "info");
    } else {
      const parts = temizAna.split(" - ");
      if (parts.length >= 3) {
        const saat = parts[parts.length - 1].trim();
        const gun = parts[parts.length - 2].trim();
        const yayinAdi = parts.slice(0, -2).join(" - ").trim();
        satir = `${yayinAdi} ❌ - ${gun} - ${saat}${bilgiEki}`;
      } else if (parts.length === 2) {
        satir = `${parts[0].trim()} ❌ - ${parts[1].trim()}${bilgiEki}`;
      } else {
        satir = `${temizAna} ❌${bilgiEki}`;
      }
      showToast("❌ Yayın iptal edildi olarak işaretlendi.", "warning");
    }
  }

  state.yayinlar[index] = satir;
  kaydetYerel();
  renderCalendar();
  updateStats();
  yayinlariBulutaGonder(`${state.currentUser} web üzerinden yayın durumunu güncelledi.`);
}

// 7. Yayın Silme
function silYayin(index) {
  if (index < 0 || index >= state.yayinlar.length) return;
  const onay = confirm("Bu yayını takvimden tamamen silmek istediğinize emin misiniz?");
  if (!onay) return;

  state.yayinlar.splice(index, 1);

  // Yeniden numaralandır
  state.yayinlar = state.yayinlar.map((satir, i) => {
    const yeniNo = i + 1;
    if (satir.includes("-)")) {
      const rest = satir.split("-)")[1].trim();
      return `${yeniNo}-) ${rest}`;
    }
    return `${yeniNo}-) ${satir}`;
  });

  kaydetYerel();
  renderCalendar();
  updateStats();
  yayinlariBulutaGonder(`${state.currentUser} webden bir yayını sildi.`);
  showToast("Yayın takvimden silindi ve liste yeniden numaralandırıldı.", "info");
}

// 8. Firebase Realtime Database & Ntfy Çift Yönlü Senkronizasyon (tellal.py ile Anında Konuşma)
const FIREBASE_DB_URL = "https://tellal-otomasyon-default-rtdb.europe-west1.firebasedatabase.app/tellal_db";

async function yayinlariBulutaGonder(ozetMesaj = "") {
  const icerik = state.yayinlar.join("\n") + (state.yayinlar.length ? "\n" : "");
  
  // 1. Birincil: Firebase Realtime Database'e Anında Yaz
  try {
    await fetch(`${FIREBASE_DB_URL}/takvim.json`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        satirlar: state.yayinlar,
        bos_mu: state.yayinlar.length === 0,
        son_guncelleme: Date.now(),
        guncelleyen: state.currentUser
      })
    });
  } catch (err) {
    console.warn("Firebase RTDB yazma hatası:", err);
  }

  // 2. İkincil: Ntfy Kanalına Yedek Bildirim Gönder
  const payload = {
    topic: NTFY_TOPIC_TAKVIM,
    title: "Tellal Takvim Güncellemesi (Web)",
    message: icerik || "__BOS_TAKVIM__",
    priority: 3,
    tags: ["calendar", "globe_with_meridians"]
  };

  try {
    const res = await fetch("https://ntfy.sh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      const data = await res.json();
      if (data.time) state.lastSyncTime = data.time;
    }
  } catch (err) {
    console.warn("Ntfy senkronizasyonu ağ hatası:", err);
  }
}

async function senkronizeEtUzak(bildirimVer = true) {
  if (state.isSyncing) return;
  state.isSyncing = true;
  const syncBtn = document.getElementById("manualSyncBtn");
  if (syncBtn) syncBtn.classList.add("rotating");

  // 1. Birincil ve Ana Veri Kaynağı: Firebase Realtime Database
  try {
    const res = await fetch(`${FIREBASE_DB_URL}/takvim.json?t=${Date.now()}`);
    if (res.ok) {
      const data = await res.json();
      if (data && typeof data === "object") {
        let gelenSatirlar = [];
        if (data.bos_mu) {
          gelenSatirlar = [];
        } else {
          let rawList = data.satirlar;
          if (rawList && typeof rawList === "object" && !Array.isArray(rawList)) {
            rawList = Object.values(rawList);
          }
          if (Array.isArray(rawList)) {
            // Yayın takviminde sadece gerçek yayınlar kalır, Gemini AI maçları normal takvim gridine aittir
            gelenSatirlar = rawList.filter(s => s && typeof s === "string" && s.trim() && !(s.includes("Gemini AI") || s.includes("[Gemini AI]")));
          }
        }

        // Sadece ve sadece veri gerçekten değiştiyse DOM'u güncelle
        if (JSON.stringify(gelenSatirlar) !== JSON.stringify(state.yayinlar)) {
          state.yayinlar = gelenSatirlar;
          kaydetYerel();
          renderCalendar();
          updateStats();
          if (bildirimVer) {
            const kimden = data.guncelleyen ? `(${data.guncelleyen})` : "";
            showToast(`✓ Buluttan en güncel takvim eşitlendi! ${kimden}`, "success");
          }
        } else if (bildirimVer) {
          showToast("Takvim zaten güncel.", "info");
        }
      }
    }
  } catch (err) {
    console.warn("Firebase RTDB okunamadı:", err);
  }

  state.isSyncing = false;
  if (syncBtn) syncBtn.classList.remove("rotating");
}

function startNtfyPolling() {
  // Her 6 saniyede bir sessizce Firebase Realtime Database'den değişiklik var mı diye kontrol et
  setInterval(() => {
    senkronizeEtUzak(false);
  }, 6000);

  // Gemini AI maç fikstürünü 20 saniyede bir sessizce kontrol et
  setInterval(() => {
    senkronizeGeminiMatches();
  }, 20000);
}

// 9. Event Listener'lar ve Modal Kontrolleri
function setupEventListeners() {
  // Modal açma & kapama
  const openModalBtn = document.getElementById("openAddModalBtn");
  const closeModalBtn = document.getElementById("closeModalBtn");
  const cancelModalBtn = document.getElementById("cancelModalBtn");
  const modalOverlay = document.getElementById("addBroadcastModal");

  if (openModalBtn) openModalBtn.addEventListener("click", openAddModal);
  if (closeModalBtn) closeModalBtn.addEventListener("click", closeAddModal);
  if (cancelModalBtn) cancelModalBtn.addEventListener("click", closeAddModal);

  // Etkinlik Detay Modalı Kapatma Butonu
  const closeEventModalBtn = document.getElementById("closeEventModalBtn");
  if (closeEventModalBtn) closeEventModalBtn.addEventListener("click", closeEventModal);

  // Form submit & Klavyeden Enter'a basınca yayını oluşturma
  const form = document.getElementById("addBroadcastForm");
  if (form) {
    form.addEventListener("submit", yeniYayinKaydet);
    form.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && e.target.tagName !== "TEXTAREA") {
        e.preventDefault();
        form.requestSubmit();
      }
    });
  }

  // Manuel Yenile Butonu
  const syncBtn = document.getElementById("manualSyncBtn");
  if (syncBtn) syncBtn.addEventListener("click", () => senkronizeEtUzak(true));

  // Arama Kutusu
  const searchInput = document.getElementById("searchInput");
  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      state.searchQuery = e.target.value.trim();
      renderCalendar();
    });
  }

  // Filtre Butonları
  const filterBtns = document.querySelectorAll(".filter-btn");
  filterBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      filterBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      state.activeFilter = btn.getAttribute("data-filter") || "all";
      renderCalendar();
    });
  });

  // Gemini AI Maç Tara Butonu
  const geminiBtn = document.getElementById("btnGeminiAiScan");
  if (geminiBtn) {
    geminiBtn.addEventListener("click", () => runGeminiAiMatchScanner(true));
  }

  // Hızlı Gün Seçimi için Dinamik Doldurma
  setupGunOptions();
  guncelleProgramListesi();
}

// Kanal Program Havuzu (Kullanıcının Verdiği Listeler)
const KANAL_PROGRAMLARI = {
  "Uykusuz Tosba": [
    { ad: "Haftalık Program", saat: "20:00" },
    { ad: "Canlı Maç Sohbetleri", saat: "20:30" },
    { ad: "Maç Sonu", saat: "22:45" },
    { ad: "Tek Maçtan Yatanlar", saat: "23:00" },
    { ad: "FC27 Kariyer", saat: "18:00" },
    { ad: "Tosba Lojistik (ETS2)", saat: "21:00" }
  ],
  "Radio Mocas": [
    { ad: "Filtresiz Memleket Havası", saat: "21:00" },
    { ad: "Albert ve Cem", saat: "21:30" },
    { ad: "Mocas Bey ve Radyosu", saat: "22:00" },
    { ad: "Aklımdaki Filmler", saat: "21:00" }
  ]
};

function guncelleProgramListesi() {
  const kanalSelect = document.getElementById("inputKanal");
  const programSelect = document.getElementById("inputProgramSelect");
  const customGroup = document.getElementById("customProgramGroup");
  const saatInput = document.getElementById("inputSaat");
  if (!kanalSelect || !programSelect) return;

  const secilenKanal = kanalSelect.value || "Uykusuz Tosba";
  const programlar = KANAL_PROGRAMLARI[secilenKanal] || [];

  let optionsHtml = programlar.map((p, idx) => {
    return `<option value="${escapeHtml(p.ad)}" data-saat="${p.saat}">${idx + 1}. ${escapeHtml(p.ad)}</option>`;
  }).join("");

  optionsHtml += `<option value="__CUSTOM__">✏️ Diğer / Özel Yayın Adı Girin...</option>`;
  programSelect.innerHTML = optionsHtml;

  if (customGroup) customGroup.style.display = "none";

  // İlk programın saatini otomatik doldur
  if (programlar.length > 0 && saatInput) {
    saatInput.value = programlar[0].saat || "20:00";
  }
}

function onProgramSelectChange() {
  const programSelect = document.getElementById("inputProgramSelect");
  const customGroup = document.getElementById("customProgramGroup");
  const customInput = document.getElementById("inputCustomProgram");
  const saatInput = document.getElementById("inputSaat");
  if (!programSelect) return;

  if (programSelect.value === "__CUSTOM__") {
    if (customGroup) customGroup.style.display = "block";
    if (customInput) customInput.focus();
  } else {
    if (customGroup) customGroup.style.display = "none";
    const secilenOpt = programSelect.options[programSelect.selectedIndex];
    if (secilenOpt && secilenOpt.dataset.saat && saatInput) {
      saatInput.value = secilenOpt.dataset.saat;
    }
  }
}

function setupGunOptions() {
  const gunSelect = document.getElementById("inputGun");
  if (!gunSelect) return;

  const now = new Date();
  let optionsHtml = "";

  // Önümüzdeki 14 günün kesin tarihli seçenekleri
  for (let i = 0; i < 14; i++) {
    const targetDate = new Date(now.getFullYear(), now.getMonth(), now.getDate() + i);
    const dayNum = targetDate.getDate();
    const monthName = AY_ISIMLERI[targetDate.getMonth()];
    const dayOfWeek = (targetDate.getDay() + 6) % 7;
    const dayName = GUN_ADLARI[dayOfWeek];

    let labelPrefix = "";
    if (i === 0) labelPrefix = "Bugün — ";
    else if (i === 1) labelPrefix = "Yarın — ";

    const val = `${dayNum} ${monthName} (${dayName})`;
    optionsHtml += `<option value="${val}">${labelPrefix}${val}</option>`;
  }

  // Tekrarlayan seçenekler
  optionsHtml += `<optgroup label="Tekrarlayan (Her Hafta)">`;
  GUN_ADLARI.forEach(g => {
    optionsHtml += `<option value="Her ${g}">Her ${g} (Haftalık)</option>`;
  });
  optionsHtml += `</optgroup>`;

  gunSelect.innerHTML = optionsHtml;
}

function openAddModal(resetProgram = true) {
  const modal = document.getElementById("addBroadcastModal");
  if (modal) {
    modal.classList.add("open");
    if (resetProgram) {
      guncelleProgramListesi();
    }
    const pSelect = document.getElementById("inputProgramSelect");
    if (pSelect) pSelect.focus();
  }
}

function closeAddModal() {
  const modal = document.getElementById("addBroadcastModal");
  if (modal) modal.classList.remove("open");
}

// =====================================================================
// AYLIK TAKVİM FONKSİYONLARI (Sleek Dark Grid - Image 2)
// =====================================================================
const AY_ISIMLERI = [
  "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
  "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"
];

const AY_KISALTMALARI = [
  "Oca", "Şub", "Mar", "Nis", "May", "Haz",
  "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"
];

const GUN_ADLARI = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"];

function initMonthCalendar() {
  const prevBtn = document.getElementById("prevMonthBtn");
  const nextBtn = document.getElementById("nextMonthBtn");
  const todayBtn = document.getElementById("todayMonthBtn");

  if (prevBtn) {
    prevBtn.addEventListener("click", () => {
      state.calendarMonth--;
      if (state.calendarMonth < 0) {
        state.calendarMonth = 11;
        state.calendarYear--;
      }
      renderMonthCalendar();
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener("click", () => {
      state.calendarMonth++;
      if (state.calendarMonth > 11) {
        state.calendarMonth = 0;
        state.calendarYear++;
      }
      renderMonthCalendar();
    });
  }

  if (todayBtn) {
    todayBtn.addEventListener("click", () => {
      const now = new Date();
      state.calendarYear = now.getFullYear();
      state.calendarMonth = now.getMonth();
      renderMonthCalendar();
    });
  }

  renderMonthCalendar();
}

function renderMonthCalendar() {
  const grid = document.getElementById("calendarDaysGrid");
  const title = document.getElementById("calendarCurrentMonthTitle");
  if (!grid || !title) return;

  // Başlık: "Ekim 2026" (Ekran görüntüsündeki gibi temiz metin)
  title.textContent = `${AY_ISIMLERI[state.calendarMonth]} ${state.calendarYear}`;

  const now = new Date();
  const isThisMonth = (now.getFullYear() === state.calendarYear && now.getMonth() === state.calendarMonth);
  const todayDate = now.getDate();

  const firstDay = new Date(state.calendarYear, state.calendarMonth, 1);
  const firstDayIndex = (firstDay.getDay() + 6) % 7; // 0 = Pazartesi, 6 = Pazar
  const daysInMonth = new Date(state.calendarYear, state.calendarMonth + 1, 0).getDate();
  const prevMonthDays = new Date(state.calendarYear, state.calendarMonth, 0).getDate();
  const prevMonthIdx = (state.calendarMonth + 11) % 12;
  const prevMonthYear = state.calendarMonth === 0 ? state.calendarYear - 1 : state.calendarYear;
  const nextMonthIdx = (state.calendarMonth + 1) % 12;
  const nextMonthYear = state.calendarMonth === 11 ? state.calendarYear + 1 : state.calendarYear;

  const parsedItems = state.yayinlar.map((s, i) => parseYayinSatiri(s, i));

  let html = "";

  // 1. Önceki aydan kalan günler (Sol boşluklar)
  for (let i = firstDayIndex - 1; i >= 0; i--) {
    const prevDayNum = prevMonthDays - i;
    const prevMatches = (state.geminiMatches || []).filter(m => m.gun === prevDayNum && m.ay === prevMonthIdx && m.yil === prevMonthYear);
    let prevEventsHtml = "";
    if (prevMatches.length > 0) {
      prevEventsHtml = prevMatches.map(m => {
        const tipClass = m.tip || "lig";
        const icon = tipClass === "milli" ? "🇹🇷" : "⚽";
        return `
          <div class="cal-event-pill gemini-match ${tipClass}" 
               title="${escapeHtml(m.aciklama)} (Detaylar ve İşlemler)"
               onclick="event.stopPropagation(); openGeminiMatchModal('${escapeHtml(m.id)}')">
            <span class="pill-time">${icon} ${escapeHtml(m.saat)}</span>
            <span class="pill-title">${escapeHtml(m.kisaAd || m.takimlar)}</span>
          </div>
        `;
      }).join("");
    }

    html += `
      <div class="cal-day-cell other-month" onclick="state.calendarMonth = ${prevMonthIdx}; state.calendarYear = ${prevMonthYear}; renderMonthCalendar();">
        <div class="cal-day-top">
          <span class="cal-day-number">${prevDayNum}</span>
        </div>
        <div class="cal-cell-events">${prevEventsHtml}</div>
      </div>
    `;
  }

  // 2. Bu ayın günleri
  for (let d = 1; d <= daysInMonth; d++) {
    const isToday = isThisMonth && (d === todayDate);
    const dayDate = new Date(state.calendarYear, state.calendarMonth, d);
    const dayOfWeek = (dayDate.getDay() + 6) % 7;
    const dayName = GUN_ADLARI[dayOfWeek];

    // Günün sağ üst köşesindeki etiket: 1. günse "1 Eki", bugünse kırmızı yuvarlak, değilse sadece sayı
    let dayTopHtml = "";
    if (isToday) {
      dayTopHtml = `<span class="cal-today-circle">${d}</span>`;
    } else if (d === 1) {
      dayTopHtml = `<span class="cal-day-number first-day-text">1 ${AY_KISALTMALARI[state.calendarMonth]}</span>`;
    } else {
      dayTopHtml = `<span class="cal-day-number">${d}</span>`;
    }

    // A) Bu güne denk gelen GERÇEK YouTube yayınları (Yayın Takvimi öğeleri)
    const matchingBroadcasts = parsedItems.filter(item => {
      if (item.bilgi.includes("Gemini AI") || item.yayinAdi.includes("Gemini AI")) return false;
      return broadcastMatchesDay(item, d, state.calendarMonth, state.calendarYear, dayName, isToday, todayDate);
    });

    // B) Bu güne denk gelen GEMINI AI maç eventleri (Kullanıcının istediği normal takvim hücre eventleri)
    const matchingMatches = (state.geminiMatches || []).filter(m => {
      return m.gun === d && m.ay === state.calendarMonth && m.yil === state.calendarYear;
    });

    let eventsHtml = "";

    // 1. Gerçek yayın pilleri
    if (matchingBroadcasts.length > 0) {
      eventsHtml += matchingBroadcasts.map(b => {
        const chClass = b.kanal === "Uykusuz Tosba" ? "tosba" : "mocas";
        let statusClass = "";
        if (b.isDone) statusClass = "done";
        else if (b.isCanceled) statusClass = "canceled";

        return `
          <div class="cal-event-pill ${chClass} ${statusClass}" 
               title="${escapeHtml(b.saat)} - ${escapeHtml(b.yayinAdi)} (${escapeHtml(b.kanal)}) (Detay ve İşlemler)"
               onclick="event.stopPropagation(); openBroadcastModal(${b.index})">
            <span class="pill-time">${escapeHtml(b.saat)}</span>
            <span class="pill-title">${escapeHtml(b.yayinAdi)}</span>
          </div>
        `;
      }).join("");
    }

    // 2. Gemini AI futbol maç pilleri (Özel futbol/derbi/milli takım rozeti)
    if (matchingMatches.length > 0) {
      eventsHtml += matchingMatches.map(m => {
        const tipClass = m.tip || "lig";
        const icon = tipClass === "milli" ? "🇹🇷" : "⚽";

        return `
          <div class="cal-event-pill gemini-match ${tipClass}" 
               title="${escapeHtml(m.aciklama)} (Detaylar ve İşlemler)"
               onclick="event.stopPropagation(); openGeminiMatchModal('${escapeHtml(m.id)}')">
            <span class="pill-time">${icon} ${escapeHtml(m.saat)}</span>
            <span class="pill-title">${escapeHtml(m.kisaAd || m.takimlar)}</span>
          </div>
        `;
      }).join("");
    }

    html += `
      <div class="cal-day-cell" data-day="${d}" onclick="selectCalendarDay(${d}, '${dayName}')">
        <div class="cal-day-top">
          ${dayTopHtml}
        </div>
        <div class="cal-cell-events">
          ${eventsHtml}
        </div>
      </div>
    `;
  }

  // 3. Gelecek aydan kalan günler (Sağ boşluklar)
  const totalCells = firstDayIndex + daysInMonth;
  const remainingCells = (totalCells % 7 === 0) ? 0 : 7 - (totalCells % 7);
  for (let n = 1; n <= remainingCells; n++) {
    let nextDayLabel = "";
    if (n === 1) {
      nextDayLabel = `<span class="cal-day-number first-day-text">1 ${AY_KISALTMALARI[nextMonthIdx]}</span>`;
    } else {
      nextDayLabel = `<span class="cal-day-number">${n}</span>`;
    }

    const nextMatches = (state.geminiMatches || []).filter(m => m.gun === n && m.ay === nextMonthIdx && m.yil === nextMonthYear);
    let nextEventsHtml = "";
    if (nextMatches.length > 0) {
      nextEventsHtml = nextMatches.map(m => {
        const tipClass = m.tip || "lig";
        const icon = tipClass === "milli" ? "🇹🇷" : "⚽";
        return `
          <div class="cal-event-pill gemini-match ${tipClass}" 
               title="${escapeHtml(m.aciklama)} (Detaylar ve İşlemler)"
               onclick="event.stopPropagation(); openGeminiMatchModal('${escapeHtml(m.id)}')">
            <span class="pill-time">${icon} ${escapeHtml(m.saat)}</span>
            <span class="pill-title">${escapeHtml(m.kisaAd || m.takimlar)}</span>
          </div>
        `;
      }).join("");
    }

    html += `
      <div class="cal-day-cell other-month" onclick="state.calendarMonth = ${nextMonthIdx}; state.calendarYear = ${nextMonthYear}; renderMonthCalendar();">
        <div class="cal-day-top">
          ${nextDayLabel}
        </div>
        <div class="cal-cell-events">${nextEventsHtml}</div>
      </div>
    `;
  }

  grid.innerHTML = html;
}

function selectCalendarDay(day, dayName) {
  const gunSelect = document.getElementById("inputGun");
  const monthName = AY_ISIMLERI[state.calendarMonth];
  const targetVal = `${day} ${monthName} (${dayName})`;

  if (gunSelect) {
    let found = false;
    for (let opt of gunSelect.options) {
      if (opt.value === targetVal || opt.value.includes(`${day} ${monthName}`)) {
        gunSelect.value = opt.value;
        found = true;
        break;
      }
    }
    if (!found) {
      const newOpt = document.createElement("option");
      newOpt.value = targetVal;
      newOpt.textContent = targetVal;
      gunSelect.insertBefore(newOpt, gunSelect.firstChild);
      gunSelect.value = targetVal;
    }
  }
  openAddModal();
  showToast(`🗓️ ${day} ${monthName} (${dayName}) seçildi. Yayın ekleyebilirsiniz.`, "info");
}

// Belirtilen günün yayınla eşleşme kontrolü (Sadece belirtilen güne eşleme)
function broadcastMatchesDay(item, d, monthIdx, year, dayName, isToday, todayDate) {
  const g = item.gun.toLowerCase().trim();
  const dayNameLower = dayName.toLowerCase();

  // 1. Eğer kullanıcı açıkça "Her <Gün>" veya "Haftalık <Gün>" yazmışsa tüm o günlerde göster
  if (g.startsWith("her ") || g.startsWith("haftalık ")) {
    return g.includes(dayNameLower);
  }

  // 2. Sayısal gün tespiti (örn: "28 Ekim", "28", "28 Ekim (Çarşamba)")
  const numMatch = g.match(/\b([1-9]|[12]\d|3[01])\b/);
  if (numMatch) {
    const specifiedDay = parseInt(numMatch[1], 10);
    if (specifiedDay !== d) return false;

    // Ay adı da yazıyorsa ayı da doğrula
    for (let m = 0; m < AY_ISIMLERI.length; m++) {
      if (g.includes(AY_ISIMLERI[m].toLowerCase())) {
        return m === monthIdx;
      }
    }
    return true;
  }

  // 3. "Bugün" etiketi -> Sadece bugün olan günde göster!
  if (g.includes("bugün")) {
    return isToday;
  }

  // 4. "Yarın" etiketi -> Sadece yarın olan günde göster!
  if (g.includes("yarın")) {
    const now = new Date();
    const isThisMonth = (now.getFullYear() === year && now.getMonth() === monthIdx);
    return isThisMonth && (d === todayDate + 1);
  }

  // 5. Eğer sadece gün adı yazılmışsa (örn: "Çarşamba"):
  // Kullanıcı yaklaşan günü kastettiği için, önümüzdeki o güne eşle!
  if (g.includes(dayNameLower)) {
    const now = new Date();
    const currentDayOfWeek = (now.getDay() + 6) % 7; // 0 = Pazartesi
    const targetDayOfWeek = GUN_ADLARI.findIndex(gn => gn.toLowerCase() === dayNameLower);
    
    if (targetDayOfWeek !== -1) {
      let diffDays = targetDayOfWeek - currentDayOfWeek;
      if (diffDays < 0) diffDays += 7; // Geçmiş güne değil, önümüzdeki o güne eşle
      const targetDate = new Date(now.getFullYear(), now.getMonth(), now.getDate() + diffDays);
      return (targetDate.getDate() === d && targetDate.getMonth() === monthIdx && targetDate.getFullYear() === year);
    }
  }

  return false;
}

// =====================================================================
// GEMINI AI MAÇ TAKİP VE TAKVİM ASİSTANI (NORMAL TAKVİM GRİDİ İÇİN)
// =====================================================================
const GEMINI_AI_FIXTURES = [
  {
    id: "derbi-gs-fb",
    takimlar: "Galatasaray - Fenerbahçe",
    kisaAd: "GS - FB (Dev Derbi)",
    lig: "Süper Lig",
    tip: "derbi",
    gun: 26,
    ay: 9, // Ekim (0-indexed: 9 = Ekim)
    yil: 2026,
    saat: "20:00",
    aciklama: "⚽ 20:00 Galatasaray vs Fenerbahçe Dev Derbi"
  },
  {
    id: "bjk-basaksehir",
    takimlar: "Beşiktaş - Başakşehir",
    kisaAd: "BJK - Başakşehir",
    lig: "Süper Lig",
    tip: "lig",
    gun: 26,
    ay: 9,
    yil: 2026,
    saat: "20:00",
    aciklama: "⚽ 20:00 Beşiktaş vs Başakşehir"
  },
  {
    id: "rize-ts",
    takimlar: "Çaykur Rizespor - Trabzonspor",
    kisaAd: "Rizespor - TS",
    lig: "Süper Lig",
    tip: "lig",
    gun: 26,
    ay: 9,
    yil: 2026,
    saat: "20:00",
    aciklama: "⚽ 20:00 Çaykur Rizespor vs Trabzonspor"
  },
  {
    id: "konya-gs",
    takimlar: "Konyaspor - Galatasaray",
    kisaAd: "Konya - GS",
    lig: "Süper Lig",
    tip: "lig",
    gun: 30,
    ay: 9,
    yil: 2026,
    saat: "20:00",
    aciklama: "⚽ 20:00 Konyaspor vs Galatasaray"
  },
  {
    id: "fb-goztepe",
    takimlar: "Fenerbahçe - Göztepe",
    kisaAd: "FB - Göztepe",
    lig: "Süper Lig",
    tip: "lig",
    gun: 31,
    ay: 9,
    yil: 2026,
    saat: "19:00",
    aciklama: "⚽ 19:00 Fenerbahçe vs Göztepe"
  },
  {
    id: "ts-gaziantep",
    takimlar: "Trabzonspor - Gaziantep FK",
    kisaAd: "TS - Gaziantep",
    lig: "Süper Lig",
    tip: "lig",
    gun: 1,
    ay: 10, // Kasım (0-indexed: 10 = Kasım)
    yil: 2026,
    saat: "16:00",
    aciklama: "⚽ 16:00 Trabzonspor vs Gaziantep FK"
  },
  {
    id: "kasimpasa-bjk",
    takimlar: "Kasımpaşa - Beşiktaş",
    kisaAd: "Kasımpaşa - BJK",
    lig: "Süper Lig",
    tip: "lig",
    gun: 1,
    ay: 10,
    yil: 2026,
    saat: "19:00",
    aciklama: "⚽ 19:00 Kasımpaşa vs Beşiktaş"
  },
  {
    id: "milli-tur-wal",
    takimlar: "Türkiye - Galler",
    kisaAd: "Türkiye - Galler 🇹🇷",
    lig: "UEFA Uluslar Ligi",
    tip: "milli",
    gun: 16,
    ay: 10,
    yil: 2026,
    saat: "20:45",
    aciklama: "🇹🇷 20:45 A Milli Takım: Türkiye vs Galler"
  }
];

async function senkronizeGeminiMatches() {
  try {
    const res = await fetch(`${FIREBASE_DB_URL}/gemini_matches.json?t=${Date.now()}`);
    if (res.ok) {
      const data = await res.json();
      if (data && Array.isArray(data.matches)) {
        if (JSON.stringify(data.matches) !== JSON.stringify(state.geminiMatches)) {
          state.geminiMatches = data.matches;
          localStorage.setItem("tellal_gemini_matches", JSON.stringify(state.geminiMatches));
          renderMonthCalendar();
        }
      }
    }
  } catch (err) {
    console.warn("Gemini maç senkronizasyon:", err);
  }
}

async function runGeminiAiMatchScanner(isManual = false) {
  // 1. Gemini AI maçlarını state'e yükle (Yayın takvimine değil, doğrudan normal takvim gridine eklenir)
  state.geminiMatches = [...GEMINI_AI_FIXTURES];
  localStorage.setItem("tellal_gemini_matches", JSON.stringify(state.geminiMatches));

  // 2. Eğer daha önceden state.yayinlar'a yanlışlıkla girmiş bot satırları varsa yayın takviminden tamamen sil
  const oncekiUzunluk = state.yayinlar.length;
  state.yayinlar = state.yayinlar.filter(y => !(y.includes("Gemini AI") || y.includes("[Gemini AI]")));
  if (state.yayinlar.length !== oncekiUzunluk) {
    kaydetYerel();
    renderCalendar();
    updateStats();
    await yayinlariBulutaGonder("Yayın takviminden Gemini AI satırları temizlendi.");
  }

  // 3. Normal takvimi yeniden render et (maçlar takvim hücrelerinde parlayacak)
  renderMonthCalendar();

  // 4. Firebase RTDB gemini_matches.json tablosuna kaydet
  try {
    await fetch(`${FIREBASE_DB_URL}/gemini_matches.json`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        matches: state.geminiMatches,
        son_guncelleme: Math.floor(Date.now() / 1000),
        kaynak: "Gemini AI"
      })
    });
  } catch (e) {
    console.warn("Gemini matches bulut kaydı hatası:", e);
  }

  // 5. Toast göster (Chate veya yayın takvimine ASLA yazılmaz)
  if (isManual) {
    showToast("✨ Gemini AI: Maçlar doğrudan normal takvim gridine event olarak işlendi! ⚽", "success");
  }
}

// Saat hesaplama yardımcısı: Belirtilen saatten 15 dakika öncesini hesaplar (Örn: "20:00" -> "19:45")
function hesapla15DkOnce(saatStr) {
  if (!saatStr || typeof saatStr !== "string" || !saatStr.includes(":")) {
    return "19:45";
  }
  const parts = saatStr.trim().split(":");
  let saat = parseInt(parts[0], 10);
  let dakika = parseInt(parts[1], 10);
  if (isNaN(saat) || isNaN(dakika)) return "19:45";
  dakika -= 15;
  if (dakika < 0) {
    dakika += 60;
    saat = (saat - 1 + 24) % 24;
  }
  return `${String(saat).padStart(2, "0")}:${String(dakika).padStart(2, "0")}`;
}

// 1. Gemini AI Maç Etkinliği Detay Modalı (Ev Sahibi - Deplasman, Lig, Saat, Butonlar)
function openGeminiMatchModal(matchId) {
  const match = (state.geminiMatches || []).find(m => m.id === matchId);
  if (!match) return;

  const modal = document.getElementById("eventActionModal");
  const modalTitleText = document.getElementById("eventModalTitleText");
  const modalIcon = document.getElementById("eventModalIcon");
  const modalBody = document.getElementById("eventModalBody");
  const modalFooter = document.getElementById("eventModalFooter");

  if (!modal || !modalBody || !modalFooter) return;

  const [evSahibi, deplasman] = match.takimlar.includes(" - ") 
    ? match.takimlar.split(" - ") 
    : [match.takimlar, ""];

  const ayAdi = AY_ISIMLERI[match.ay] || "";
  const gunDate = new Date(match.yil, match.ay, match.gun);
  const gunAdi = GUN_ADLARI[(gunDate.getDay() + 6) % 7] || "";
  const formattedTarih = `${match.gun} ${ayAdi} ${match.yil} (${gunAdi})`;

  if (modalIcon) modalIcon.textContent = match.tip === "milli" ? "🇹🇷" : "⚽";
  if (modalTitleText) modalTitleText.textContent = "Gemini AI Maç Etkinliği";

  modalBody.innerHTML = `
    <div class="event-detail-card">
      <div class="event-detail-header-card">
        <div class="event-detail-teams">${escapeHtml(evSahibi)} ${deplasman ? `<span style="color:var(--text-muted);font-weight:400;font-size:0.95rem;margin:0 6px;">vs</span> ${escapeHtml(deplasman)}` : ""}</div>
        <div class="event-detail-sub">
          <span class="ai-badge">${escapeHtml(match.lig || "Futbol")}</span>
          <span class="stat-badge primary">${escapeHtml(match.saat)}</span>
        </div>
      </div>

      <div class="event-detail-grid">
        <div class="event-detail-row">
          <span class="event-detail-label">Ev Sahibi</span>
          <span class="event-detail-value">${escapeHtml(evSahibi)}</span>
        </div>
        <div class="event-detail-row">
          <span class="event-detail-label">Deplasman</span>
          <span class="event-detail-value">${escapeHtml(deplasman || "-")}</span>
        </div>
        <div class="event-detail-row">
          <span class="event-detail-label">Lig / Turnuva</span>
          <span class="event-detail-value">${escapeHtml(match.lig || "Süper Lig")}</span>
        </div>
        <div class="event-detail-row">
          <span class="event-detail-label">Maç Saati</span>
          <span class="event-detail-value">⏰ ${escapeHtml(match.saat)}</span>
        </div>
      </div>

      <div class="event-detail-row" style="grid-column: 1 / -1;">
        <span class="event-detail-label">Tarih</span>
        <span class="event-detail-value">📅 ${escapeHtml(formattedTarih)}</span>
      </div>
    </div>
  `;

  modalFooter.innerHTML = `
    <button type="button" class="btn btn-secondary" onclick="closeEventModal()">Kapat</button>
    <button type="button" class="btn btn-danger" onclick="removeGeminiMatch('${escapeHtml(match.id)}')">
      <span>🗑️</span>
      <span>Maçı Takvimden Kaldır</span>
    </button>
    <button type="button" class="btn btn-primary" onclick="geminiMacaYayinEkle('${escapeHtml(match.id)}')">
      <span>➕</span>
      <span>Bu Maç İçin Yayın Ekle</span>
    </button>
  `;

  modal.classList.add("open");
}

// 2. Maçı Takvimden Kaldırma (state, localStorage ve Firebase RTDB gemini_matches.json tablosundan silinir)
async function removeGeminiMatch(matchId) {
  const matchIndex = (state.geminiMatches || []).findIndex(m => m.id === matchId);
  if (matchIndex === -1) return;

  const match = state.geminiMatches[matchIndex];
  state.geminiMatches.splice(matchIndex, 1);

  // Yerel hafızaya kaydet
  localStorage.setItem("tellal_gemini_matches", JSON.stringify(state.geminiMatches));

  // Modalı kapat ve takvim hücresinden anında kaybolmasını sağla
  closeEventModal();
  renderMonthCalendar();

  // Firebase gemini_matches.json tablosundan sil/güncelle
  try {
    await fetch(`${FIREBASE_DB_URL}/gemini_matches.json`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        matches: state.geminiMatches,
        son_guncelleme: Math.floor(Date.now() / 1000),
        kaynak: "Web Takvimden Kaldırıldı"
      })
    });
  } catch (err) {
    console.warn("Gemini match silme hatası:", err);
  }

  showToast(`🗑️ "${match.takimlar}" maçı takvimden kaldırıldı.`, "info");
}

// 3. Gerçek Yayın Detay Modalı (Takvimden çıkarma / silme seçeneği)
function openBroadcastModal(index) {
  if (index < 0 || index >= state.yayinlar.length) return;
  const item = parseYayinSatiri(state.yayinlar[index], index);

  const modal = document.getElementById("eventActionModal");
  const modalTitleText = document.getElementById("eventModalTitleText");
  const modalIcon = document.getElementById("eventModalIcon");
  const modalBody = document.getElementById("eventModalBody");
  const modalFooter = document.getElementById("eventModalFooter");

  if (!modal || !modalBody || !modalFooter) return;

  const chClass = item.kanal === "Uykusuz Tosba" ? "badge-tosba" : "badge-mocas";
  let statusBadge = `<span class="stat-badge warning">Planlandı</span>`;
  if (item.isDone) {
    statusBadge = `<span class="stat-badge success">Tamamlandı ✅</span>`;
  } else if (item.isCanceled) {
    statusBadge = `<span class="stat-badge danger">İptal Edildi ❌</span>`;
  }

  if (modalIcon) modalIcon.textContent = "📺";
  if (modalTitleText) modalTitleText.textContent = "Yayın Detayı & İşlemler";

  modalBody.innerHTML = `
    <div class="event-detail-card">
      <div class="event-detail-header-card">
        <div class="event-detail-teams">${escapeHtml(item.yayinAdi)}</div>
        <div class="event-detail-sub">
          <span class="channel-badge ${chClass}">${escapeHtml(item.kanal)}</span>
          ${statusBadge}
        </div>
      </div>

      <div class="event-detail-grid">
        <div class="event-detail-row">
          <span class="event-detail-label">Yayın Günü</span>
          <span class="event-detail-value">📅 ${escapeHtml(item.gun)}</span>
        </div>
        <div class="event-detail-row">
          <span class="event-detail-label">Yayın Saati</span>
          <span class="event-detail-value">⏰ ${escapeHtml(item.saat)}</span>
        </div>
      </div>

      <div class="event-detail-row" style="grid-column: 1 / -1;">
        <span class="event-detail-label">Ek Not / Bilgi</span>
        <span class="event-detail-value">${escapeHtml(item.bilgi || "Ek bilgi belirtilmedi")}</span>
      </div>
    </div>
  `;

  modalFooter.innerHTML = `
    <button type="button" class="btn btn-secondary" onclick="closeEventModal()">Kapat</button>
    <button type="button" class="btn btn-danger" onclick="silYayinFromModal(${item.index})">
      <span>🗑️</span>
      <span>Yayını Takvimden Kaldır / Sil</span>
    </button>
  `;

  modal.classList.add("open");
}

function silYayinFromModal(index) {
  closeEventModal();
  silYayin(index);
}

function closeEventModal() {
  const modal = document.getElementById("eventActionModal");
  if (modal) modal.classList.remove("open");
}

// 4. Gemini Maçı İçin Yayın Oluşturma:
// - "Canlı Maç Sohbetleri" (Uykusuz Tosba) seçili form oluşturur
// - Yayın saatini maç saatinden 15 dk önceye ayarlar
// - Ek not bilgi bölümüne "X - Y takımı maçı" yazar
function geminiMacaYayinEkle(arg1, argSaat, argGun, argAyIdx) {
  closeEventModal();

  let match = null;
  if (typeof arg1 === "string" && !argSaat) {
    match = (state.geminiMatches || []).find(m => m.id === arg1);
  }

  let takimlar = match ? match.takimlar : arg1;
  let saat = match ? match.saat : (argSaat || "20:00");
  let gun = match ? match.gun : (argGun || 1);
  let ayIdx = match ? match.ay : (argAyIdx !== undefined ? argAyIdx : state.calendarMonth);
  let yil = match ? match.yil : state.calendarYear;

  const ayAdi = AY_ISIMLERI[ayIdx] || "";
  const dayDate = new Date(yil, ayIdx, gun);
  const dayName = GUN_ADLARI[(dayDate.getDay() + 6) % 7] || "";
  const targetGunVal = `${gun} ${ayAdi} (${dayName})`;

  // 1. Kanalı "Uykusuz Tosba" seç
  const kanalSelect = document.getElementById("inputKanal");
  if (kanalSelect) kanalSelect.value = "Uykusuz Tosba";

  // 2. Uykusuz Tosba program listesini yükle
  guncelleProgramListesi();

  // 3. "Canlı Maç Sohbetleri" seçili olsun
  const selectProgram = document.getElementById("inputProgramSelect");
  const customProgram = document.getElementById("inputCustomProgram");
  const customGroup = document.getElementById("customProgramGroup");

  if (selectProgram) {
    selectProgram.value = "Canlı Maç Sohbetleri";
    if (selectProgram.options && selectProgram.options.length > 0) {
      let matched = false;
      for (let opt of selectProgram.options) {
        if (opt.value === "Canlı Maç Sohbetleri" || opt.value.includes("Canlı Maç")) {
          selectProgram.value = opt.value;
          matched = true;
          break;
        }
      }
      if (!matched) {
        selectProgram.value = "__CUSTOM__";
        if (customGroup) customGroup.style.display = "block";
        if (customProgram) customProgram.value = "Canlı Maç Sohbetleri";
      } else if (customGroup) {
        customGroup.style.display = "none";
      }
    } else if (customGroup) {
      customGroup.style.display = "none";
    }
  }

  // 4. Günü eşle
  const gunSelect = document.getElementById("inputGun");
  if (gunSelect) {
    let found = false;
    for (let opt of gunSelect.options) {
      if (opt.value === targetGunVal || opt.value.includes(`${gun} ${ayAdi}`)) {
        gunSelect.value = opt.value;
        found = true;
        break;
      }
    }
    if (!found) {
      const newOpt = document.createElement("option");
      newOpt.value = targetGunVal;
      newOpt.textContent = targetGunVal;
      gunSelect.insertBefore(newOpt, gunSelect.firstChild);
      gunSelect.value = targetGunVal;
    }
  }

  // 5. Yayının saatini maçın saatinden 15dk önceye ayarla
  const yayinSaati = hesapla15DkOnce(saat);
  const saatInput = document.getElementById("inputSaat");
  if (saatInput) saatInput.value = yayinSaati;

  // 6. Ek not bilgi bölümüne "X - Y takımı maçı" yaz
  const bilgiInput = document.getElementById("inputBilgi");
  if (bilgiInput) {
    bilgiInput.value = `${takimlar} maçı`;
  }

  // 7. Modalı aç (seçilen program ve saati koruyarak)
  openAddModal(false);
  showToast(`⚽ "${takimlar}" maçı için Canlı Maç Sohbeti yayını 15 dk öncesine (${yayinSaati}) planlandı.`, "info");
}

function checkGeminiAiAutoRun() {
  const now = new Date();
  const isSunday = (now.getDay() === 0);
  const todayStr = now.toISOString().split("T")[0];
  const lastSundayRun = localStorage.getItem("gemini_ai_last_sunday");

  // Normal takvim maçlarını başlat/tara
  runGeminiAiMatchScanner(false);

  if (isSunday && lastSundayRun !== todayStr) {
    localStorage.setItem("gemini_ai_last_sunday", todayStr);
  }
}

function filterByCalendarBroadcast(title) {
  const searchInput = document.getElementById("searchInput");
  if (searchInput) {
    searchInput.value = title;
    state.searchQuery = title;
    renderCalendar();
    window.scrollTo({ top: 300, behavior: "smooth" });
  }
}

// =====================================================================
// CANLI EKİP CHAT SİSTEMİ (Cem Yıldırım, Ufuk, Yiğit)
// =====================================================================
function initChat() {
  const chatForm = document.getElementById("chatForm");
  if (chatForm) {
    chatForm.addEventListener("submit", sendChatMessage);
  }

  // İlk mesajları çek
  fetchChatData();

  // Her 3.5 saniyede bir chat veritabanını kontrol et
  setInterval(fetchChatData, 3500);
}

async function fetchChatData() {
  try {
    const res = await fetch(`${FIREBASE_DB_URL}/chat.json?t=${Date.now()}`);
    if (res.ok) {
      const data = await res.json();
      let rawList = data ? data.mesajlar : [];
      if (rawList && typeof rawList === "object" && !Array.isArray(rawList)) {
        rawList = Object.values(rawList);
      }
      if (Array.isArray(rawList)) {
        rawList = rawList.filter(m => m && typeof m === "string" && m.trim() && !m.includes("Gemini AI"));
      } else {
        rawList = [];
      }
      const rawStr = JSON.stringify(rawList);
      if (rawStr !== chatState.lastRaw) {
        chatState.lastRaw = rawStr;
        chatState.mesajlar = rawList;
        renderChatMessages();
      }
    }
  } catch (err) {
    console.warn("Chat verisi alınamadı:", err);
  }
}

function renderChatMessages() {
  const container = document.getElementById("chatMessagesContainer");
  if (!container) return;

  if (!chatState.mesajlar || chatState.mesajlar.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; color: var(--text-dim); padding: 40px 10px; font-size: 0.88rem;">
        💬 Henüz bir mesaj yok. Ekip için ilk mesajı Cem Yıldırım olarak yazın!
      </div>
    `;
    return;
  }

  container.innerHTML = chatState.mesajlar.map(msgStr => {
    let sender = "Bilinmeyen";
    let text = msgStr;
    let senderClass = "chat-sender-cem";

    if (msgStr.includes(":")) {
      const p = msgStr.split(":", 2);
      sender = p[0].trim();
      text = msgStr.substring(p[0].length + 1).trim();
    }

    const sLower = sender.toLowerCase();
    const isOwn = (sender === state.currentUser || sLower.includes("cem"));

    if (sLower.includes("gemini")) {
      senderClass = "chat-sender-gemini";
    } else if (sLower.includes("ufuk")) {
      senderClass = "chat-sender-ufuk";
    } else if (sLower.includes("yiğit") || sLower.includes("yigit")) {
      senderClass = "chat-sender-yigit";
    } else {
      senderClass = "chat-sender-cem";
    }

    return `
      <div class="chat-msg-row ${isOwn ? "own-msg" : ""}">
        <div class="chat-msg-header">
          <span class="${senderClass}">${escapeHtml(sender)}</span>
        </div>
        <div class="chat-msg-body">
          ${escapeHtml(text)}
        </div>
      </div>
    `;
  }).join("");

  // Otomatik olarak en son mesaja kaydır
  container.scrollTop = container.scrollHeight;
}

async function sendChatMessage(e) {
  if (e) e.preventDefault();
  const input = document.getElementById("chatInput");
  if (!input) return;

  const text = input.value.trim();
  if (!text || chatState.isSending) return;

  chatState.isSending = true;
  const sendBtn = document.getElementById("chatSendBtn");
  if (sendBtn) sendBtn.disabled = true;

  const senderName = state.currentUser || "Cem Yıldırım";
  const formattedLine = `${senderName}: ${text}`;

  // Optimistik arayüz güncellemesi
  chatState.mesajlar.push(formattedLine);
  renderChatMessages();
  input.value = "";

  try {
    // 1. Birincil: Firebase Realtime Database'e yaz
    const updatedMessages = [...chatState.mesajlar];
    await fetch(`${FIREBASE_DB_URL}/chat.json`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        mesajlar: updatedMessages,
        son_guncelleme: Math.floor(Date.now() / 1000),
        guncelleyen: senderName
      })
    });

    // 2. İkincil: Ntfy Kanalına Bildir (tellal.py'de ses çalması ve senkronize olması için)
    await fetch("https://ntfy.sh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        topic: "tellal_chat_sync_u_y_8832",
        title: "Tellal Chat Güncellemesi",
        message: updatedMessages.join("\n"),
        priority: 3,
        tags: ["speech_balloon"]
      })
    });
  } catch (err) {
    console.warn("Chat gönderme hatası:", err);
    showToast("Mesaj gönderilirken bir hata oluştu.", "warning");
  } finally {
    chatState.isSending = false;
    if (sendBtn) sendBtn.disabled = false;
  }
}

// 10. Canlı Saat
function updateClock() {
  const clockElem = document.getElementById("liveClock");
  if (clockElem) {
    const now = new Date();
    clockElem.textContent = now.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  }
}

// 11. Toast Bildirim Sistemi
function showToast(message, type = "info") {
  let container = document.getElementById("toastContainer");
  if (!container) {
    container = document.createElement("div");
    container.id = "toastContainer";
    container.className = "toast-container";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  
  let icon = "ℹ️";
  if (type === "success") icon = "✓";
  if (type === "warning") icon = "⚠️";
  if (type === "error") icon = "✕";

  toast.innerHTML = `<span>${icon}</span> <span>${escapeHtml(message)}</span>`;
  container.appendChild(toast);

  // Göster animasyonu
  setTimeout(() => toast.classList.add("show"), 20);

  // Gizle & Kaldır
  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => toast.remove(), 350);
  }, 4000);
}

// Yardımcı: HTML Escape
function escapeHtml(text) {
  if (!text) return "";
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
