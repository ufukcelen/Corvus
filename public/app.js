/**
 * Corvus Cloud Web Portal - JavaScript Logic
 * Firebase Hosting & Ntfy Realtime Sync Desteği
 * Sürüm: v1.4.8
 */

const APP_VERSION = "1.6.1";

// Global State
const NTFY_TOPIC_TAKVIM = "tellal_takvim_sync_u_y_8832";
const STORAGE_KEY_TAKVIM = "corvus_web_takvim";
const STORAGE_KEY_USER = "corvus_web_user";
const STORAGE_KEY_AUTH = "corvus_auth_session";
const FIREBASE_DB_URL = "https://tellal-otomasyon-default-rtdb.europe-west1.firebasedatabase.app/tellal_db";

// Kullanıcı Şehir Eşleştirmesi (Weatherstack & Open-Meteo Canlı Hava Durumu)
const USER_CITY_MAP = {
  "Ufuk Çelen": { cityKey: "Istanbul", displayName: "İstanbul", lat: 41.0082, lon: 28.9784 },
  "Cem Yıldırım": { cityKey: "Ankara", displayName: "Ankara", lat: 39.9334, lon: 32.8597 },
  "Mustafa Yiğit Kızılel": { cityKey: "Denizli", displayName: "Denizli", lat: 37.7765, lon: 29.0864 },
  "Kadir Tekin": { cityKey: "Yalova", displayName: "Yalova", lat: 40.6550, lon: 29.2769 },
  "Yağız Pekdemir": { cityKey: "Sakarya", displayName: "Sakarya", lat: 40.7569, lon: 30.3783 },
  "Burhan Mutlugöz": { cityKey: "Nagold,Germany", displayName: "Nagold (Almanya)", lat: 48.5505, lon: 8.7237 }
};

const WEATHER_DESC_TR = {
  "sunny": "Güneşli",
  "clear": "Açık",
  "partly cloudy": "Parçalı Bulutlu",
  "cloudy": "Bulutlu",
  "overcast": "Kapalı / Bulutlu",
  "patchy rain possible": "Yer Yer Yağmurlu",
  "patchy light rain": "Hafif Yağmurlu",
  "light rain": "Hafif Yağmurlu",
  "moderate rain": "Orta Şiddetli Yağmur",
  "heavy rain": "Kuvvetli Yağmurlu",
  "rain": "Yağmurlu",
  "thunderstorm": "Gök Gürültülü Fırtına",
  "snow": "Karlı",
  "fog": "Sisli",
  "mist": "Puslu"
};

let currentWeatherCache = null;
let GEMINI_API_KEY = localStorage.getItem("corvus_gemini_api_key") || "";

async function getGeminiApiKey() {
  if (GEMINI_API_KEY) return GEMINI_API_KEY;
  try {
    const res = await fetch(`${FIREBASE_DB_URL}/config/gemini_key.json`);
    if (res.ok) {
      const key = await res.json();
      if (key && typeof key === "string") {
        GEMINI_API_KEY = key;
        localStorage.setItem("corvus_gemini_api_key", key);
        return key;
      }
    }
  } catch (e) {
    console.warn("Gemini API key yükleme hatası:", e);
  }
  return "";
}

// Rol Tanımları
const ROLES = {
  ADMIN: "admin",
  YONETICI: "yonetici",
  USER: "user"
};

// 6 Adet Yetkili Kullanıcı ve Şifreleri
const AUTH_USERS = [
  {
    name: "Ufuk Çelen",
    role: "admin",
    roleTitle: "Admin",
    password: "JCH2dmHQmYUgsauS"
  },
  {
    name: "Cem Yıldırım",
    role: "admin",
    roleTitle: "Admin",
    password: "j2MdzLpIvNsWckiv"
  },
  {
    name: "Mustafa Yiğit Kızılel",
    role: "admin",
    roleTitle: "Admin",
    password: "h7gFMjXnrwwmEFAs"
  },
  {
    name: "Kadir Tekin",
    role: "yonetici",
    roleTitle: "Yönetici",
    password: "TM0ifvnM9m7nhz0R"
  },
  {
    name: "Yağız Pekdemir",
    role: "yonetici",
    roleTitle: "Yönetici",
    password: "cGagCBKvxdxYG5ti"
  },
  {
    name: "Burhan Mutlugöz",
    role: "yonetici",
    roleTitle: "Yönetici",
    password: "hTFUHYrif2fSLraH"
  }
];

// Eski uydurma (mock) maç ID'leri listesi (asla takvime alınmaz)
const MOCK_MATCH_IDS = new Set([
  'derbi-gs-fb', 'bjk-basaksehir', 'rize-ts', 'konya-gs', 'fb-goztepe', 'ts-gaziantep', 
  'kasimpasa-bjk', 'uefa-ajax-gs', 'uefa-bjk-malmo', 'uefa-ts-rapid', 'uefa-az-fb', 
  'voleybol-ita', 'voleybol-srb', 'voleybol-brezilya', 'voleybol-polonya', 
  'vol-tur-ita', 'vol-tur-srb', 'vol-tur-bra', 'vol-tur-pol',
  'nba-lakers-warriors', 'nba-celtics-nuggets', 'nba-rockets-clippers', 'nba-bucks-mavs', 'nba-heat-suns', 
  'nba-lal-gsw', 'nba-bos-den', 'nba-hou-lac', 'nba-mil-dal', 'nba-mia-phx',
  'eurolig-fb-madrid', 'eurolig-efes-pana', 'eurolig-oly-fb', 'eurolig-efes-barca', 'eurolig-fb-maccabi', 
  'euro-fb-rma', 'euro-efs-pao', 'euro-oly-fb', 'euro-efs-bar', 'euro-fb-mta',
  'tenis-paris-semi', 'tenis-paris-final', 'tenis-atp-torino', 'tenis-atp-final', 
  'ten-alc-sin', 'ten-paris-final', 'ten-djo-med', 'ten-atp-final',
  'f1-meksika-gp', 'f1-brezilya-sprint', 'f1-brezilya-gp', 'f1-vegas-gp', 
  'f1-mexico-gp', 'f1-brazil-sprint', 'f1-brazil-gp',
  'milli-tur-wal'
]);

let state = {
  currentUser: "Ufuk Çelen",
  userRole: "admin",
  yayinlar: [],
  geminiMatches: [],
  activeFilter: "all",
  searchQuery: "",
  isSyncing: false,
  lastSyncTime: 0,
  calendarYear: new Date().getFullYear(),
  calendarMonth: new Date().getMonth(),
  selectedSports: ["futbol", "voleybol", "nba", "eurolig", "tenis", "f1"]
};

let chatState = {
  mesajlar: [],
  lastRaw: "",
  isSending: false
};

// DOM Yüklendiğinde Başlat
document.addEventListener("DOMContentLoaded", () => {
  initAuth();
  initCalendarData();
  setupEventListeners();
  startNtfyPolling();
  initMonthCalendar();
  initChat();
  checkGeminiAiAutoRun();
  updateClock();
  setInterval(updateClock, 1000);
  loadAndDisplayWeather();
  setInterval(loadAndDisplayWeather, 600000);
});

// 1. Oturum & Rol Yetkilendirme Yönetimi
function initAuth() {
  const savedAuth = localStorage.getItem(STORAGE_KEY_AUTH) || localStorage.getItem("tellal_auth_session");
  if (savedAuth) {
    try {
      const parsed = JSON.parse(savedAuth);
      const user = AUTH_USERS.find(u => u.name === parsed.name);
      if (user) {
        state.currentUser = user.name;
        state.userRole = user.role;
        hideLoginModal();
        applyRolePermissions();
        return;
      }
    } catch (e) {
      console.warn("Auth oturum hatası:", e);
    }
  }

  showLoginModal();
}

function showLoginModal() {
  const overlay = document.getElementById("loginModalOverlay");
  if (overlay) {
    overlay.style.display = "flex";
    const errBox = document.getElementById("loginErrorAlert");
    if (errBox) errBox.style.display = "none";
    const passInput = document.getElementById("loginPasswordInput");
    if (passInput) passInput.value = "";
  }
}

function hideLoginModal() {
  const overlay = document.getElementById("loginModalOverlay");
  if (overlay) overlay.style.display = "none";
}

function logoutUser() {
  const onay = confirm("Oturumu kapatmak istediğinize emin misiniz?");
  if (!onay) return;
  localStorage.removeItem(STORAGE_KEY_AUTH);
  document.documentElement.classList.remove("role-yonetici", "role-admin", "role-user");
  document.body.classList.remove("role-yonetici", "role-admin", "role-user");
  showLoginModal();
  showToast("Oturum kapatıldı. Lütfen tekrar giriş yapın.", "info");
}

function applyRolePermissions() {
  const isYonetici = (state.userRole === "yonetici");
  const isUser = (state.userRole === "user");
  const isAdmin = (state.userRole === "admin");

  document.documentElement.classList.toggle("role-yonetici", isYonetici);
  document.documentElement.classList.toggle("role-admin", isAdmin);
  document.body.classList.toggle("role-yonetici", isYonetici);
  document.body.classList.toggle("role-admin", isAdmin);

  // 1. Üst bar: Yayın Ekle Butonu (Yöneticide gizlenir)
  const addBtn = document.getElementById("openAddModalBtn");
  if (addBtn) addBtn.style.display = (isYonetici || isUser) ? "none" : "";

  // 2. Üst bar: Gemini AI Butonu (Yöneticide gizlenir)
  const geminiBtn = document.getElementById("btnGeminiAiScan");
  if (geminiBtn) geminiBtn.style.display = (isYonetici || isUser) ? "none" : "";

  // 3. Kullanıcı Rozeti & Rol Bilgisi
  const userElem = document.getElementById("activeUserName");
  if (userElem) userElem.textContent = state.currentUser;

  const roleElem = document.getElementById("activeUserRole");
  if (roleElem) {
    if (isAdmin) {
      roleElem.textContent = "Admin";
      roleElem.className = "role-badge badge-admin";
    } else if (isYonetici) {
      roleElem.textContent = "Yönetici";
      roleElem.className = "role-badge badge-yonetici";
    } else {
      roleElem.textContent = "Kullanıcı";
      roleElem.className = "role-badge badge-user";
    }
  }

  // 4. Kullanıcıya özel şehir hava durumunu güncelle
  loadAndDisplayWeather();

  // 4. Chat aktif kullanıcı bilgisi
  const chatLabel = document.getElementById("chatActiveUserLabel");
  if (chatLabel) chatLabel.textContent = state.currentUser;
  const chatInput = document.getElementById("chatInput");
  if (chatInput) chatInput.placeholder = `${state.currentUser} olarak ekip arkadaşlarına mesaj yaz...`;

  // 5. Takvimi ve yayın listesini yeniden render et
  renderCalendar();
  renderMonthCalendar();
}

function initUser() {
  applyRolePermissions();
}

// 2. Takvim Verisi Yükleme & Parse Etme
async function initCalendarData() {
  const localData = localStorage.getItem(STORAGE_KEY_TAKVIM) || localStorage.getItem("tellal_web_takvim");
  if (localData) {
    try {
      state.yayinlar = JSON.parse(localData);
      // Yayın takviminde kalmış olabilecek eski Gemini bot satırlarını ayıkla
      state.yayinlar = state.yayinlar.filter(y => !(y.includes("Gemini AI") || y.includes("[Gemini AI]")));
    } catch (e) {
      state.yayinlar = [];
    }
  }

  // Gemini AI Maçlarını localStorage'dan veya varsayılan fikstürden yükle (Eski mock maçları ayıkla)
  const localMatches = localStorage.getItem("corvus_gemini_matches") || localStorage.getItem("tellal_gemini_matches");
  if (localMatches) {
    try {
      const parsed = JSON.parse(localMatches);
      state.geminiMatches = (parsed || []).filter(m => !MOCK_MATCH_IDS.has(m.id));
      if (state.geminiMatches.length === 0) {
        state.geminiMatches = [...GEMINI_AI_FIXTURES];
      }
    } catch (e) {
      state.geminiMatches = [...GEMINI_AI_FIXTURES];
    }
  } else {
    state.geminiMatches = [...GEMINI_AI_FIXTURES];
  }
  localStorage.setItem("corvus_gemini_matches", JSON.stringify(state.geminiMatches));
  localStorage.setItem("tellal_gemini_matches", JSON.stringify(state.geminiMatches));

  // Karşılaşma filtre tercihlerini localStorage'dan yükle
  const localSports = localStorage.getItem("corvus_selected_sports") || localStorage.getItem("tellal_selected_sports");
  if (localSports) {
    try {
      const parsedSports = JSON.parse(localSports);
      if (Array.isArray(parsedSports)) {
        state.selectedSports = parsedSports;
      }
    } catch (e) {
      console.warn("Spor filtreleri okunamadı:", e);
    }
  }
  updateMatchesFilterUI();

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
        ${state.userRole === "yonetici" ? "" : `<button class="btn btn-primary btn-sm" onclick="openAddModal()">+ Yeni Yayın Ekle</button>`}
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
      <div class="broadcast-card ${statusClass}" data-index="${item.index}" draggable="true">
        <div class="card-left">
          <button class="drag-handle-btn" 
                  type="button" 
                  title="Sıralamak için basılı tutup sürükleyin veya tıklayın" 
                  aria-label="Manuel Sıralama İkonu"
                  onclick="openReorderMenu(event, ${item.index})">
            <svg width="14" height="18" viewBox="0 0 14 18" fill="currentColor">
              <circle cx="4" cy="3" r="1.5" />
              <circle cx="10" cy="3" r="1.5" />
              <circle cx="4" cy="9" r="1.5" />
              <circle cx="10" cy="9" r="1.5" />
              <circle cx="4" cy="15" r="1.5" />
              <circle cx="10" cy="15" r="1.5" />
            </svg>
          </button>
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
            <button class="action-icon-btn gcal-btn" title="Bu yayını Google Takvim'e ekle / aç" onclick="openGoogleCalendarForBroadcast(${item.index})">
              📅
            </button>
            ${state.userRole === "yonetici" ? "" : `
              <button class="action-icon-btn edit-btn" title="Yayını Düzenle (✏️)" onclick="openEditBroadcastModal(${item.index})">
                ✏️
              </button>
              <button class="action-icon-btn delete-btn" title="Yayını Takvimden Sil" onclick="silYayin(${item.index})">
                🗑️
              </button>
            `}
          </div>
        </div>
      </div>
    `;
  }).join("");

  setupBroadcastDragAndDrop();
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

  // Ntfy üzerinden buluta ve masaüstü Corvus'a aktar!
  yayinlariBulutaGonder(`${state.currentUser} webden yeni yayın ekledi: ${program}`);
  showToast(`✓ "${program}" yayını takvime eklendi ve Google Takvim ile otomatik eşitleniyor! 📅`, "success");
}

// 5b. Düzenlenen Yayını Kaydetme (Edit)
function editYayinKaydet(e) {
  e.preventDefault();
  if (state.userRole === "yonetici") {
    showToast("Yayın düzenleme yetkiniz bulunmamaktadır.", "warning");
    return;
  }

  const indexInput = document.getElementById("editBroadcastIndex");
  const index = parseInt(indexInput ? indexInput.value : "-1", 10);
  if (isNaN(index) || index < 0 || index >= state.yayinlar.length) {
    showToast("Geçersiz yayın seçimi.", "danger");
    return;
  }

  const oldItem = parseYayinSatiri(state.yayinlar[index], index);
  const selectElem = document.getElementById("editInputProgramSelect");
  let program = selectElem ? selectElem.value.trim() : "";
  if (program === "__CUSTOM__") {
    const customInput = document.getElementById("editInputCustomProgram");
    program = customInput ? customInput.value.trim() : "";
  }
  const gun = document.getElementById("editInputGun").value.trim();
  const saat = document.getElementById("editInputSaat").value.trim();
  const durum = document.getElementById("editInputDurum").value;
  const bilgi = document.getElementById("editInputBilgi").value.trim();

  if (!program || !gun || !saat) {
    showToast("Lütfen program, gün ve saat alanlarını eksiksiz doldurun.", "warning");
    return;
  }

  // Sıra numarasını koru (örn: 1, 2, 3...)
  const no = oldItem.no || (index + 1);

  // Durum sembolü
  let statusSymbol = "";
  if (durum === "done") {
    statusSymbol = " ✅";
  } else if (durum === "canceled") {
    statusSymbol = " ❌";
  }

  let yeniSatir = `${no}-) ${program} - ${gun} - ${saat}`;
  if (bilgi) {
    yeniSatir += ` | Bilgi: ${bilgi}`;
  }
  yeniSatir += statusSymbol;

  // State'i güncelle
  state.yayinlar[index] = yeniSatir;
  kaydetYerel();
  renderCalendar();
  updateStats();
  closeEditModal();

  // Ntfy & Firebase üzerinden senkronize et
  yayinlariBulutaGonder(`${state.currentUser} webden yayını düzenledi: ${program}`);
  showToast(`✏️ "${program}" yayını başarıyla güncellendi ve Google Takvim ile eşitleniyor!`, "success");
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
  if (state.userRole === "yonetici") {
    showToast("Yayın silme yetkiniz bulunmamaktadır.", "warning");
    return;
  }
  if (index < 0 || index >= state.yayinlar.length) return;
  const onay = confirm("Bu yayını takvimden tamamen silmek istediğinize emin misiniz?");
  if (!onay) return;

  state.yayinlar.splice(index, 1);

  renumberBroadcasts();
  kaydetYerel();
  renderCalendar();
  updateStats();
  yayinlariBulutaGonder(`${state.currentUser} webden bir yayını sildi.`);
  showToast("Yayın takvimden silindi ve liste yeniden numaralandırıldı.", "info");
}

// =====================================================================
// MANUEL SIRALAMA & DRAG AND DROP YÖNETİMİ
// =====================================================================
let draggedBroadcastIndex = null;
let wasDraggingBroadcast = false;

function renumberBroadcasts() {
  state.yayinlar = state.yayinlar.map((satir, i) => {
    const yeniNo = i + 1;
    if (satir.includes("-)")) {
      const rest = satir.split("-)")[1].trim();
      return `${yeniNo}-) ${rest}`;
    }
    return `${yeniNo}-) ${satir}`;
  });
}

function moveBroadcast(fromIndex, toIndex, position = "after") {
  if (state.userRole === "yonetici") {
    showToast("Yayın sıralama yetkiniz bulunmamaktadır.", "warning");
    return;
  }
  if (fromIndex === toIndex || fromIndex < 0 || toIndex < 0 || fromIndex >= state.yayinlar.length || toIndex >= state.yayinlar.length) return;

  const itemToMove = state.yayinlar[fromIndex];
  state.yayinlar.splice(fromIndex, 1);

  let insertAt = toIndex;
  if (fromIndex < toIndex) {
    insertAt = (position === "after") ? toIndex : (toIndex - 1);
  } else {
    insertAt = (position === "after") ? (toIndex + 1) : toIndex;
  }

  if (insertAt < 0) insertAt = 0;
  if (insertAt > state.yayinlar.length) insertAt = state.yayinlar.length;

  state.yayinlar.splice(insertAt, 0, itemToMove);
  renumberBroadcasts();
  kaydetYerel();
  renderCalendar();
  updateStats();
  yayinlariBulutaGonder(`${state.currentUser} web üzerinden yayın sıralamasını değiştirdi.`);
  showToast("✓ Yayın sıralaması güncellendi ve senkronize edildi.", "success");
}

function moveBroadcastStep(index, direction) {
  closeReorderMenu();
  if (state.userRole === "yonetici") {
    showToast("Yayın sıralama yetkiniz bulunmamaktadır.", "warning");
    return;
  }
  if (index < 0 || index >= state.yayinlar.length) return;

  if (direction === "up") {
    if (index === 0) {
      showToast("Yayın zaten en başta.", "info");
      return;
    }
    const temp = state.yayinlar[index];
    state.yayinlar[index] = state.yayinlar[index - 1];
    state.yayinlar[index - 1] = temp;
    showToast("✓ Yayın bir sıra yukarı taşındı.", "success");
  } else if (direction === "down") {
    if (index === state.yayinlar.length - 1) {
      showToast("Yayın zaten en sonda.", "info");
      return;
    }
    const temp = state.yayinlar[index];
    state.yayinlar[index] = state.yayinlar[index + 1];
    state.yayinlar[index + 1] = temp;
    showToast("✓ Yayın bir sıra aşağı taşındı.", "success");
  } else if (direction === "top") {
    if (index === 0) {
      showToast("Yayın zaten en başta.", "info");
      return;
    }
    const [item] = state.yayinlar.splice(index, 1);
    state.yayinlar.unshift(item);
    showToast("✓ Yayın en başa taşındı.", "success");
  } else if (direction === "bottom") {
    if (index === state.yayinlar.length - 1) {
      showToast("Yayın zaten en sonda.", "info");
      return;
    }
    const [item] = state.yayinlar.splice(index, 1);
    state.yayinlar.push(item);
    showToast("✓ Yayın en sona taşındı.", "success");
  }

  renumberBroadcasts();
  kaydetYerel();
  renderCalendar();
  updateStats();
  yayinlariBulutaGonder(`${state.currentUser} yayın sırasını değiştirdi.`);
}

function closeReorderMenu() {
  const existing = document.getElementById("reorderFloatingMenu");
  if (existing) existing.remove();
}

document.addEventListener("click", (e) => {
  if (!e.target.closest(".drag-handle-btn") && !e.target.closest("#reorderFloatingMenu")) {
    closeReorderMenu();
  }
});

function openReorderMenu(e, index) {
  e.preventDefault();
  e.stopPropagation();

  if (wasDraggingBroadcast) return;

  if (state.userRole === "yonetici") {
    showToast("Yayın sıralama yetkiniz bulunmamaktadır.", "warning");
    return;
  }

  const existing = document.getElementById("reorderFloatingMenu");
  if (existing && existing.dataset.index == index) {
    closeReorderMenu();
    return;
  }
  closeReorderMenu();

  const total = state.yayinlar.length;
  if (total <= 1) {
    showToast("Sıralanacak başka yayın bulunmuyor.", "info");
    return;
  }

  const btn = e.currentTarget;
  const rect = btn.getBoundingClientRect();

  const menu = document.createElement("div");
  menu.id = "reorderFloatingMenu";
  menu.className = "reorder-floating-menu";
  menu.dataset.index = index;

  const isFirst = (index === 0);
  const isLast = (index === total - 1);

  menu.innerHTML = `
    <div style="padding: 4px 8px; font-size: 0.72rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px;">
      Sıralama Seçenekleri
    </div>
    ${!isFirst ? `
      <button type="button" class="reorder-menu-item" onclick="moveBroadcastStep(${index}, 'up')">
        <span>⬆️</span> <span>1 Sıra Yukarı Taşı</span>
      </button>
      <button type="button" class="reorder-menu-item" onclick="moveBroadcastStep(${index}, 'top')">
        <span>🔝</span> <span>En Başa Taşı</span>
      </button>
    ` : ""}
    ${!isLast ? `
      <button type="button" class="reorder-menu-item" onclick="moveBroadcastStep(${index}, 'down')">
        <span>⬇️</span> <span>1 Sıra Aşağı Taşı</span>
      </button>
      <button type="button" class="reorder-menu-item" onclick="moveBroadcastStep(${index}, 'bottom')">
        <span>🔚</span> <span>En Sona Taşı</span>
      </button>
    ` : ""}
    <div class="reorder-menu-divider"></div>
    <div style="padding: 4px 8px; font-size: 0.7rem; color: var(--text-muted);">
      💡 <em>İkonu basılı tutup sürükleyerek de sıralayabilirsiniz.</em>
    </div>
  `;

  document.body.appendChild(menu);

  let top = rect.bottom + 6;
  let left = rect.left;

  const menuRect = menu.getBoundingClientRect();
  if (top + menuRect.height > window.innerHeight - 10) {
    top = rect.top - menuRect.height - 6;
  }
  if (left + menuRect.width > window.innerWidth - 10) {
    left = window.innerWidth - menuRect.width - 10;
  }

  menu.style.top = `${Math.max(10, top)}px`;
  menu.style.left = `${Math.max(10, left)}px`;
}

function setupBroadcastDragAndDrop() {
  const container = document.getElementById("broadcastListContainer");
  if (!container) return;

  const cards = container.querySelectorAll(".broadcast-card");

  cards.forEach(card => {
    const handle = card.querySelector(".drag-handle-btn");
    const cardIndex = parseInt(card.dataset.index, 10);

    card.addEventListener("dragstart", (e) => {
      if (state.userRole === "yonetici") {
        e.preventDefault();
        showToast("Yayın sıralama yetkiniz bulunmamaktadır.", "warning");
        return;
      }
      if (e.target.closest("button:not(.drag-handle-btn)") || e.target.closest("a") || e.target.closest("input")) {
        e.preventDefault();
        return;
      }

      closeReorderMenu();
      draggedBroadcastIndex = cardIndex;
      wasDraggingBroadcast = true;
      e.dataTransfer.effectAllowed = "move";
      e.dataTransfer.setData("text/plain", cardIndex);
      setTimeout(() => card.classList.add("is-dragging"), 10);
    });

    card.addEventListener("dragover", (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
      if (draggedBroadcastIndex === null || draggedBroadcastIndex === cardIndex) return;

      const rect = card.getBoundingClientRect();
      const isTop = (e.clientY - rect.top) < (rect.height / 2);
      card.classList.toggle("drop-above", isTop);
      card.classList.toggle("drop-below", !isTop);
    });

    card.addEventListener("dragleave", () => {
      card.classList.remove("drop-above", "drop-below");
    });

    card.addEventListener("drop", (e) => {
      e.preventDefault();
      card.classList.remove("drop-above", "drop-below");
      if (draggedBroadcastIndex === null || draggedBroadcastIndex === cardIndex) return;

      const rect = card.getBoundingClientRect();
      const isTop = (e.clientY - rect.top) < (rect.height / 2);
      const fromIdx = draggedBroadcastIndex;
      draggedBroadcastIndex = null;
      moveBroadcast(fromIdx, cardIndex, isTop ? "before" : "after");
    });

    card.addEventListener("dragend", () => {
      draggedBroadcastIndex = null;
      cards.forEach(c => c.classList.remove("is-dragging", "drop-above", "drop-below"));
      setTimeout(() => { wasDraggingBroadcast = false; }, 150);
    });

    // Dokunmatik Ekranlar (Touch/Tablet) Desteği
    if (handle) {
      let touchStartY = 0;
      let isTouchDragging = false;
      let lastHoveredCard = null;

      handle.addEventListener("touchstart", (e) => {
        if (state.userRole === "yonetici") return;
        touchStartY = e.touches[0].clientY;
        draggedBroadcastIndex = cardIndex;
        isTouchDragging = false;
      }, { passive: true });

      handle.addEventListener("touchmove", (e) => {
        const touch = e.touches[0];
        const diffY = Math.abs(touch.clientY - touchStartY);
        if (diffY > 8) {
          isTouchDragging = true;
          wasDraggingBroadcast = true;
          card.classList.add("is-dragging");
        }
        if (!isTouchDragging) return;

        const el = document.elementFromPoint(touch.clientX, touch.clientY);
        const targetCard = el ? el.closest(".broadcast-card") : null;

        cards.forEach(c => {
          if (c !== targetCard) c.classList.remove("drop-above", "drop-below");
        });

        if (targetCard && targetCard !== card) {
          lastHoveredCard = targetCard;
          const rect = targetCard.getBoundingClientRect();
          const isTop = (touch.clientY - rect.top) < (rect.height / 2);
          targetCard.classList.toggle("drop-above", isTop);
          targetCard.classList.toggle("drop-below", !isTop);
        } else {
          lastHoveredCard = null;
        }
      }, { passive: true });

      handle.addEventListener("touchend", () => {
        card.classList.remove("is-dragging");
        if (isTouchDragging && lastHoveredCard && draggedBroadcastIndex !== null) {
          const targetIndex = parseInt(lastHoveredCard.dataset.index, 10);
          const isTop = lastHoveredCard.classList.contains("drop-above");
          lastHoveredCard.classList.remove("drop-above", "drop-below");
          const fromIdx = draggedBroadcastIndex;
          draggedBroadcastIndex = null;
          isTouchDragging = false;
          lastHoveredCard = null;
          moveBroadcast(fromIdx, targetIndex, isTop ? "before" : "after");
        } else {
          draggedBroadcastIndex = null;
          isTouchDragging = false;
          cards.forEach(c => c.classList.remove("drop-above", "drop-below"));
        }
        setTimeout(() => { wasDraggingBroadcast = false; }, 200);
      });
    }
  });
}

// =====================================================================
// GOOGLE TAKVİM ("YAYIN TAKVİMİ") YARDIMCILARI
// =====================================================================
const GOOGLE_CALENDAR_ID = "c1765f9d421b1821978ac5fabbcd06b0df0b80f212403476b4d39ea7057138b6@group.calendar.google.com";

function calculateBroadcastDate(gunStr, saatStr) {
  const now = new Date();
  let saat = 20;
  let dakika = 0;
  if (saatStr && saatStr.includes(":")) {
    const parts = saatStr.trim().split(":");
    saat = parseInt(parts[0], 10) || 20;
    dakika = parseInt(parts[1], 10) || 0;
  }

  const gunLower = (gunStr || "").toLowerCase().trim();

  // 1. Sayı ve Ay Tespiti (örn: "30 Ekim", "30 Ekim (Cuma)")
  const numMatch = gunLower.match(/\b([1-9]|[12]\d|3[01])\b/);
  if (numMatch) {
    const dayNum = parseInt(numMatch[1], 10);
    let monthIdx = now.getMonth();
    for (let m = 0; m < AY_ISIMLERI.length; m++) {
      if (gunLower.includes(AY_ISIMLERI[m].toLowerCase())) {
        monthIdx = m;
        break;
      }
    }
    const year = now.getFullYear();
    const d = new Date(year, monthIdx, dayNum, saat, dakika);
    return d;
  }

  // 2. Bugün / Yarın
  if (gunLower.includes("bugün")) {
    return new Date(now.getFullYear(), now.getMonth(), now.getDate(), saat, dakika);
  }
  if (gunLower.includes("yarın")) {
    return new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, saat, dakika);
  }

  // 3. Gün Adı (örn: "Çarşamba", "Her Cuma")
  for (let i = 0; i < GUN_ADLARI.length; i++) {
    if (gunLower.includes(GUN_ADLARI[i].toLowerCase())) {
      const curDow = (now.getDay() + 6) % 7; // 0 = Pazartesi
      let diff = (i - curDow + 7) % 7;
      if (diff === 0) {
        if (now.getHours() > saat || (now.getHours() === saat && now.getMinutes() >= dakika)) {
          diff = 7;
        }
      }
      return new Date(now.getFullYear(), now.getMonth(), now.getDate() + diff, saat, dakika);
    }
  }

  return new Date(now.getFullYear(), now.getMonth(), now.getDate(), saat, dakika);
}

function openGoogleCalendarForBroadcast(index) {
  if (index < 0 || index >= state.yayinlar.length) return;
  const item = parseYayinSatiri(state.yayinlar[index], index);

  const startDt = calculateBroadcastDate(item.gun, item.saat);
  const endDt = new Date(startDt.getTime() + 90 * 60 * 1000); // 90 dakika

  const formatGCal = (d) => {
    const pad = (n) => String(n).padStart(2, "0");
    const y = d.getUTCFullYear();
    const m = pad(d.getUTCMonth() + 1);
    const day = pad(d.getUTCDate());
    const h = pad(d.getUTCHours());
    const min = pad(d.getUTCMinutes());
    const s = pad(d.getUTCSeconds());
    return `${y}${m}${day}T${h}${min}${s}Z`;
  };

  let titlePrefix = "📅 ";
  let durumMetni = "Planlanan Canlı Yayın 📅";
  if (item.isCanceled) {
    titlePrefix = "❌ [İPTAL] ";
    durumMetni = "İptal Edildi ❌";
  } else if (item.isDone) {
    titlePrefix = "✅ ";
    durumMetni = "Tamamlandı / Hazır ✅";
  }

  const title = `${titlePrefix}${item.yayinAdi} (${item.kanal})`;
  const descLines = [
    `Kanal: ${item.kanal}`,
    `Program: ${item.yayinAdi}`,
    `Planlanan Zaman: ${item.gun} - ${item.saat}`,
    `Durum: ${durumMetni}`
  ];
  if (item.bilgi) {
    descLines.push(`Ek Not / Maç: ${item.bilgi}`);
  }
  descLines.push("Panel: https://tellal-otomasyon.web.app");

  const details = descLines.join("\n");
  const dates = `${formatGCal(startDt)}/${formatGCal(endDt)}`;

  const url = `https://calendar.google.com/calendar/render?action=TEMPLATE&text=${encodeURIComponent(title)}&dates=${dates}&details=${encodeURIComponent(details)}&add=${encodeURIComponent(GOOGLE_CALENDAR_ID)}`;
  window.open(url, "_blank");
}

// 8. Firebase Realtime Database & Ntfy Çift Yönlü Senkronizasyon (tellal.py ile Anında Konuşma)

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
    title: "Corvus Takvim Güncellemesi (Web)",
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

  // Düzenleme (Edit) Modalı Kontrolleri
  const closeEditModalBtn = document.getElementById("closeEditModalBtn");
  const cancelEditModalBtn = document.getElementById("cancelEditModalBtn");
  const editModalOverlay = document.getElementById("editBroadcastModal");
  const editForm = document.getElementById("editBroadcastForm");

  if (closeEditModalBtn) closeEditModalBtn.addEventListener("click", closeEditModal);
  if (cancelEditModalBtn) cancelEditModalBtn.addEventListener("click", closeEditModal);
  if (editModalOverlay) {
    editModalOverlay.addEventListener("click", (e) => {
      if (e.target === editModalOverlay) closeEditModal();
    });
  }
  if (editForm) {
    editForm.addEventListener("submit", editYayinKaydet);
    editForm.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && e.target.tagName !== "TEXTAREA") {
        e.preventDefault();
        editForm.requestSubmit();
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

  // Gemini AI Maç Tara Butonu & Modal Kontrolleri
  const geminiBtn = document.getElementById("btnGeminiAiScan");
  if (geminiBtn) {
    geminiBtn.addEventListener("click", () => openGeminiAiModal());
  }

  const closeGeminiBtn = document.getElementById("closeGeminiModalBtn");
  if (closeGeminiBtn) {
    closeGeminiBtn.addEventListener("click", () => closeGeminiAiModal());
  }

  const geminiModalOverlay = document.getElementById("geminiAiModalOverlay");
  if (geminiModalOverlay) {
    geminiModalOverlay.addEventListener("click", (e) => {
      if (e.target === geminiModalOverlay) closeGeminiAiModal();
    });
  }

  const btnQuickSync = document.getElementById("btnGeminiQuickSync");
  if (btnQuickSync) {
    btnQuickSync.addEventListener("click", () => handleGeminiQuickSync());
  }

  const btnParseAdd = document.getElementById("btnGeminiParseAdd");
  if (btnParseAdd) {
    btnParseAdd.addEventListener("click", () => handleGeminiParseAdd());
  }

  // Canlı Hava Durumu Rozetine Tıklama (Detay Göster / Yenile)
  const weatherBadge = document.getElementById("btnWeatherBadge");
  if (weatherBadge) {
    weatherBadge.addEventListener("click", () => loadAndDisplayWeather(true));
  }

  // Karşılaşmalar Açılır Filtre Menüsü Kontrolleri
  initMatchesFilterEvents();

  // Kullanıcı Giriş Formu ve Oturum Yönetimi
  const loginForm = document.getElementById("loginForm");
  if (loginForm) {
    loginForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const userSelect = document.getElementById("loginUserSelect");
      const passInput = document.getElementById("loginPasswordInput");
      const rememberCheckbox = document.getElementById("loginRememberMe");
      const errBox = document.getElementById("loginErrorAlert");

      const selectedName = userSelect ? userSelect.value : "";
      const enteredPassword = passInput ? passInput.value.trim() : "";

      const user = AUTH_USERS.find(u => u.name === selectedName);
      if (user && user.password === enteredPassword) {
        state.currentUser = user.name;
        state.userRole = user.role;

        // "Beni hatırla" veya bir kere doğru girildiğinde kalıcı kaydet
        if (!rememberCheckbox || rememberCheckbox.checked) {
          localStorage.setItem(STORAGE_KEY_AUTH, JSON.stringify({ name: user.name, role: user.role }));
        }

        if (errBox) errBox.style.display = "none";
        hideLoginModal();
        applyRolePermissions();
        showToast(`Hoş geldiniz, ${user.name} (${user.roleTitle})! 👋`, "success");
      } else {
        if (errBox) errBox.style.display = "flex";
        if (passInput) {
          passInput.value = "";
          passInput.focus();
        }
      }
    });
  }

  // Şifre Göster / Gizle Butonu
  const togglePassBtn = document.getElementById("btnTogglePassword");
  if (togglePassBtn) {
    togglePassBtn.addEventListener("click", () => {
      const passInput = document.getElementById("loginPasswordInput");
      if (passInput) {
        const isPass = passInput.getAttribute("type") === "password";
        passInput.setAttribute("type", isPass ? "text" : "password");
        togglePassBtn.textContent = isPass ? "🙈" : "👁️";
      }
    });
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

function populateGunOptionsHelper(selectElem) {
  if (!selectElem) return;
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

  selectElem.innerHTML = optionsHtml;
}

function setupGunOptions() {
  const gunSelect = document.getElementById("inputGun");
  const editGunSelect = document.getElementById("editInputGun");
  if (gunSelect) populateGunOptionsHelper(gunSelect);
  if (editGunSelect) populateGunOptionsHelper(editGunSelect);
}

function openAddModal(resetProgram = true) {
  if (state.userRole === "yonetici") {
    showToast("Yayın ekleme yetkiniz bulunmamaktadır.", "warning");
    return;
  }
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

// ---------------------------------------------------------------------
// YAYIN DÜZENLEME (EDIT) MODAL FONKSİYONLARI
// ---------------------------------------------------------------------
function openEditBroadcastModal(index) {
  if (state.userRole === "yonetici") {
    showToast("Yayın düzenleme yetkiniz bulunmamaktadır.", "warning");
    return;
  }
  if (index < 0 || index >= state.yayinlar.length) return;

  const item = parseYayinSatiri(state.yayinlar[index], index);
  const modal = document.getElementById("editBroadcastModal");
  if (!modal) return;

  const indexInput = document.getElementById("editBroadcastIndex");
  const kanalSelect = document.getElementById("editInputKanal");
  const saatInput = document.getElementById("editInputSaat");
  const durumSelect = document.getElementById("editInputDurum");
  const bilgiInput = document.getElementById("editInputBilgi");
  const gunSelect = document.getElementById("editInputGun");

  if (indexInput) indexInput.value = index;
  if (kanalSelect) kanalSelect.value = item.kanal;

  // Program listesini ve seçimini hazırla
  guncelleEditProgramListesi(item.yayinAdi);

  // Gün seçeneklerini hazırla ve seç
  if (gunSelect) {
    if (!gunSelect.options || gunSelect.options.length === 0) {
      populateGunOptionsHelper(gunSelect);
    }
    let exists = false;
    for (let i = 0; i < gunSelect.options.length; i++) {
      if (gunSelect.options[i].value === item.gun) {
        exists = true;
        break;
      }
    }
    if (!exists && item.gun) {
      const customOpt = document.createElement("option");
      customOpt.value = item.gun;
      customOpt.textContent = `📅 ${item.gun}`;
      gunSelect.insertBefore(customOpt, gunSelect.firstChild);
    }
    gunSelect.value = item.gun;
  }

  // Saat
  if (saatInput) saatInput.value = item.saat || "20:00";

  // Durum
  if (durumSelect) {
    if (item.isDone) {
      durumSelect.value = "done";
    } else if (item.isCanceled) {
      durumSelect.value = "canceled";
    } else {
      durumSelect.value = "planned";
    }
  }

  // Bilgi
  if (bilgiInput) bilgiInput.value = item.bilgi || "";

  modal.classList.add("open");
}

function closeEditModal() {
  const modal = document.getElementById("editBroadcastModal");
  if (modal) modal.classList.remove("open");
}

function guncelleEditProgramListesi(targetProgramName = null) {
  const kanalSelect = document.getElementById("editInputKanal");
  const programSelect = document.getElementById("editInputProgramSelect");
  const customGroup = document.getElementById("editCustomProgramGroup");
  const customInput = document.getElementById("editInputCustomProgram");
  const saatInput = document.getElementById("editInputSaat");
  if (!kanalSelect || !programSelect) return;

  const secilenKanal = kanalSelect.value || "Uykusuz Tosba";
  const programlar = KANAL_PROGRAMLARI[secilenKanal] || [];

  let optionsHtml = programlar.map((p, idx) => {
    return `<option value="${escapeHtml(p.ad)}" data-saat="${p.saat}">${idx + 1}. ${escapeHtml(p.ad)}</option>`;
  }).join("");

  optionsHtml += `<option value="__CUSTOM__">✏️ Diğer / Özel Yayın Adı Girin...</option>`;
  programSelect.innerHTML = optionsHtml;

  if (targetProgramName) {
    const match = programlar.find(p => p.ad.toLowerCase() === targetProgramName.toLowerCase());
    if (match) {
      programSelect.value = match.ad;
      if (customGroup) customGroup.style.display = "none";
    } else {
      programSelect.value = "__CUSTOM__";
      if (customGroup) customGroup.style.display = "block";
      if (customInput) customInput.value = targetProgramName;
    }
  } else {
    if (customGroup) customGroup.style.display = "none";
    if (programlar.length > 0 && saatInput && !saatInput.value) {
      saatInput.value = programlar[0].saat || "20:00";
    }
  }
}

function onEditProgramSelectChange() {
  const programSelect = document.getElementById("editInputProgramSelect");
  const customGroup = document.getElementById("editCustomProgramGroup");
  const customInput = document.getElementById("editInputCustomProgram");
  const saatInput = document.getElementById("editInputSaat");
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

const ALL_SPORTS = ["futbol", "voleybol", "nba", "eurolig", "tenis", "f1"];

function updateMatchesFilterUI() {
  const allCheckbox = document.getElementById("filterSportAll");
  const sportCheckboxes = document.querySelectorAll(".sport-checkbox");

  if (!state.selectedSports || !Array.isArray(state.selectedSports)) {
    state.selectedSports = [...ALL_SPORTS];
  }

  sportCheckboxes.forEach(cb => {
    cb.checked = state.selectedSports.includes(cb.value);
  });

  if (allCheckbox) {
    allCheckbox.checked = (state.selectedSports.length === ALL_SPORTS.length);
  }
}

function initMatchesFilterEvents() {
  const filterWrapper = document.getElementById("matchesFilterWrapper");
  const filterBtn = document.getElementById("btnMatchesFilter");
  const filterDropdown = document.getElementById("matchesFilterDropdown");
  const allCheckbox = document.getElementById("filterSportAll");
  const sportCheckboxes = document.querySelectorAll(".sport-checkbox");

  if (!filterWrapper || !filterBtn || !filterDropdown) return;

  // Açılır menüyü aç / kapat
  filterBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    const isShow = filterDropdown.classList.toggle("show");
    filterBtn.classList.toggle("open", isShow);
    filterBtn.setAttribute("aria-expanded", isShow ? "true" : "false");
  });

  // Dropdown içi tıklamaların menüyü kapatmasını engelle
  filterDropdown.addEventListener("click", (e) => {
    e.stopPropagation();
  });

  // Dışarı tıklayınca dropdown'ı kapat
  document.addEventListener("click", (e) => {
    if (!filterWrapper.contains(e.target)) {
      filterDropdown.classList.remove("show");
      filterBtn.classList.remove("open");
      filterBtn.setAttribute("aria-expanded", "false");
    }
  });

  // "Tümü" onay kutusu tıklandığında
  if (allCheckbox) {
    allCheckbox.addEventListener("change", () => {
      if (allCheckbox.checked) {
        state.selectedSports = [...ALL_SPORTS];
      } else {
        state.selectedSports = [];
      }
      sportCheckboxes.forEach(cb => {
        cb.checked = allCheckbox.checked;
      });
      localStorage.setItem("tellal_selected_sports", JSON.stringify(state.selectedSports));
      renderMonthCalendar();
    });
  }

  // Branş bazlı onay kutuları tıklandığında
  sportCheckboxes.forEach(cb => {
    cb.addEventListener("change", () => {
      const checkedBoxes = Array.from(document.querySelectorAll(".sport-checkbox:checked"));
      state.selectedSports = checkedBoxes.map(b => b.value);
      if (allCheckbox) {
        allCheckbox.checked = (state.selectedSports.length === ALL_SPORTS.length);
      }
      localStorage.setItem("tellal_selected_sports", JSON.stringify(state.selectedSports));
      renderMonthCalendar();
    });
  });
}

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
    const prevMatches = (state.geminiMatches || []).filter(m => {
      const brans = m.brans || (m.tip === "milli" ? "futbol" : (m.tip || "futbol"));
      const isSelected = (state.selectedSports || []).includes(brans);
      return isSelected && m.gun === prevDayNum && m.ay === prevMonthIdx && m.yil === prevMonthYear;
    });
    let prevEventsHtml = "";
    if (prevMatches.length > 0) {
      prevEventsHtml = prevMatches.map(m => {
        const brans = m.brans || (m.tip === "milli" ? "futbol" : (m.tip || "futbol"));
        const icon = m.ikon || (brans === "voleybol" ? "🏐" : brans === "nba" ? "🏀" : brans === "eurolig" ? "🏆" : brans === "tenis" ? "🎾" : brans === "f1" ? "🏎️" : "⚽");
        return `
          <div class="cal-event-pill gemini-match ${brans}" 
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

    // B) Bu güne denk gelen GEMINI AI karşılaşmaları (Kullanıcının seçtiği branş filtrelerine göre)
    const matchingMatches = (state.geminiMatches || []).filter(m => {
      const brans = m.brans || (m.tip === "milli" ? "futbol" : (m.tip || "futbol"));
      const isSelected = (state.selectedSports || []).includes(brans);
      return isSelected && m.gun === d && m.ay === state.calendarMonth && m.yil === state.calendarYear;
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

    // 2. Gemini AI karşılaşma pilleri (Futbol, Voleybol, NBA, EuroLig, Tenis, F1)
    if (matchingMatches.length > 0) {
      eventsHtml += matchingMatches.map(m => {
        const brans = m.brans || (m.tip === "milli" ? "futbol" : (m.tip || "futbol"));
        const icon = m.ikon || (brans === "voleybol" ? "🏐" : brans === "nba" ? "🏀" : brans === "eurolig" ? "🏆" : brans === "tenis" ? "🎾" : brans === "f1" ? "🏎️" : "⚽");

        return `
          <div class="cal-event-pill gemini-match ${brans}" 
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

    const nextMatches = (state.geminiMatches || []).filter(m => {
      const brans = m.brans || (m.tip === "milli" ? "futbol" : (m.tip || "futbol"));
      const isSelected = (state.selectedSports || []).includes(brans);
      return isSelected && m.gun === n && m.ay === nextMonthIdx && m.yil === nextMonthYear;
    });
    let nextEventsHtml = "";
    if (nextMatches.length > 0) {
      nextEventsHtml = nextMatches.map(m => {
        const brans = m.brans || (m.tip === "milli" ? "futbol" : (m.tip || "futbol"));
        const icon = m.ikon || (brans === "voleybol" ? "🏐" : brans === "nba" ? "🏀" : brans === "eurolig" ? "🏆" : brans === "tenis" ? "🎾" : brans === "f1" ? "🏎️" : "⚽");
        return `
          <div class="cal-event-pill gemini-match ${brans}" 
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
  if (state.userRole === "yonetici") {
    showToast("Yayın ekleme yetkisi yalnızca Admin rolündedir.", "info");
    return;
  }
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
    "id": "real-uefa-gs-stuttgart",
    "takimlar": "Galatasaray - Stuttgart",
    "kisaAd": "GS - Stuttgart (UEFA)",
    "brans": "futbol",
    "bransAdi": "Futbol",
    "ikon": "⚽",
    "lig": "UEFA Şampiyonlar Ligi",
    "tip": "futbol",
    "gun": 3,
    "ay": 10,
    "yil": 2026,
    "saat": "20:45",
    "aciklama": "⚽ 20:45 Galatasaray vs Stuttgart (UEFA Şampiyonlar Ligi)"
  },
  {
    "id": "real-uefa-fb-liverpool",
    "takimlar": "Fenerbahçe - Liverpool",
    "kisaAd": "FB - Liverpool (UEFA)",
    "brans": "futbol",
    "bransAdi": "Futbol",
    "ikon": "⚽",
    "lig": "UEFA Avrupa Ligi",
    "tip": "futbol",
    "gun": 4,
    "ay": 10,
    "yil": 2026,
    "saat": "20:30",
    "aciklama": "⚽ 20:30 Fenerbahçe vs Liverpool (UEFA Avrupa Ligi)"
  },
  {
    "id": "real-uefa-celtic-bjk",
    "takimlar": "Celtic - Beşiktaş",
    "kisaAd": "Celtic - BJK (UEFA)",
    "brans": "futbol",
    "bransAdi": "Futbol",
    "ikon": "⚽",
    "lig": "UEFA Avrupa Ligi",
    "tip": "futbol",
    "gun": 5,
    "ay": 10,
    "yil": 2026,
    "saat": "22:45",
    "aciklama": "⚽ 22:45 Celtic vs Beşiktaş (UEFA Avrupa Ligi)"
  },
  {
    "id": "real-sl-gs-amed",
    "takimlar": "Galatasaray - Amed SK",
    "kisaAd": "GS - Amed SK",
    "brans": "futbol",
    "bransAdi": "Futbol",
    "ikon": "⚽",
    "lig": "Trendyol Süper Lig",
    "tip": "futbol",
    "gun": 7,
    "ay": 10,
    "yil": 2026,
    "saat": "19:00",
    "aciklama": "⚽ 19:00 Galatasaray vs Amed SK (Süper Lig 11. Hafta)"
  },
  {
    "id": "real-sl-corum-fb",
    "takimlar": "Çorum FK - Fenerbahçe",
    "kisaAd": "Çorum FK - FB",
    "brans": "futbol",
    "bransAdi": "Futbol",
    "ikon": "⚽",
    "lig": "Trendyol Süper Lig",
    "tip": "futbol",
    "gun": 8,
    "ay": 10,
    "yil": 2026,
    "saat": "16:00",
    "aciklama": "⚽ 16:00 Çorum FK vs Fenerbahçe (Süper Lig 11. Hafta)"
  },
  {
    "id": "real-sl-bjk-gencler",
    "takimlar": "Beşiktaş - Gençlerbirliği",
    "kisaAd": "BJK - Gençlerbirliği",
    "brans": "futbol",
    "bransAdi": "Futbol",
    "ikon": "⚽",
    "lig": "Trendyol Süper Lig",
    "tip": "futbol",
    "gun": 8,
    "ay": 10,
    "yil": 2026,
    "saat": "19:00",
    "aciklama": "⚽ 19:00 Beşiktaş vs Gençlerbirliği (Süper Lig 11. Hafta)"
  },
  {
    "id": "real-sl-alanya-ts",
    "takimlar": "Alanyaspor - Trabzonspor",
    "kisaAd": "Alanyaspor - TS",
    "brans": "futbol",
    "bransAdi": "Futbol",
    "ikon": "⚽",
    "lig": "Trendyol Süper Lig",
    "tip": "futbol",
    "gun": 8,
    "ay": 10,
    "yil": 2026,
    "saat": "19:00",
    "aciklama": "⚽ 19:00 Alanyaspor vs Trabzonspor (Süper Lig 11. Hafta)"
  },
  {
    "id": "real-milli-tur-bel",
    "takimlar": "Türkiye - Belçika 🇹🇷",
    "kisaAd": "Türkiye - Belçika 🇹🇷",
    "brans": "futbol",
    "bransAdi": "Futbol",
    "ikon": "⚽",
    "lig": "UEFA Uluslar A Ligi",
    "tip": "futbol",
    "gun": 12,
    "ay": 10,
    "yil": 2026,
    "saat": "20:00",
    "aciklama": "🇹🇷 20:00 Türkiye vs Belçika (UEFA Uluslar A Ligi)"
  },
  {
    "id": "real-milli-fra-tur",
    "takimlar": "Fransa - Türkiye 🇹🇷",
    "kisaAd": "Fransa - Türkiye 🇹🇷",
    "brans": "futbol",
    "bransAdi": "Futbol",
    "ikon": "⚽",
    "lig": "UEFA Uluslar A Ligi",
    "tip": "futbol",
    "gun": 15,
    "ay": 10,
    "yil": 2026,
    "saat": "22:45",
    "aciklama": "🇹🇷 22:45 Fransa vs Türkiye (UEFA Uluslar A Ligi)"
  },
  {
    "id": "real-sl-gs-samsun",
    "takimlar": "Galatasaray - Samsunspor",
    "kisaAd": "GS - Samsunspor",
    "brans": "futbol",
    "bransAdi": "Futbol",
    "ikon": "⚽",
    "lig": "Trendyol Süper Lig",
    "tip": "futbol",
    "gun": 21,
    "ay": 10,
    "yil": 2026,
    "saat": "19:00",
    "aciklama": "⚽ 19:00 Galatasaray vs Samsunspor (Süper Lig 12. Hafta)"
  },
  {
    "id": "real-sl-kocaeli-fb",
    "takimlar": "Kocaelispor - Fenerbahçe",
    "kisaAd": "Kocaelispor - FB",
    "brans": "futbol",
    "bransAdi": "Futbol",
    "ikon": "⚽",
    "lig": "Trendyol Süper Lig",
    "tip": "futbol",
    "gun": 21,
    "ay": 10,
    "yil": 2026,
    "saat": "19:00",
    "aciklama": "⚽ 19:00 Kocaelispor vs Fenerbahçe (Süper Lig 12. Hafta)"
  },
  {
    "id": "real-sl-ts-eyup",
    "takimlar": "Trabzonspor - Eyüpspor",
    "kisaAd": "TS - Eyüpspor",
    "brans": "futbol",
    "bransAdi": "Futbol",
    "ikon": "⚽",
    "lig": "Trendyol Süper Lig",
    "tip": "futbol",
    "gun": 22,
    "ay": 10,
    "yil": 2026,
    "saat": "16:00",
    "aciklama": "⚽ 16:00 Trabzonspor vs Eyüpspor (Süper Lig 12. Hafta)"
  },
  {
    "id": "real-sl-konya-bjk",
    "takimlar": "Konyaspor - Beşiktaş",
    "kisaAd": "Konyaspor - BJK",
    "brans": "futbol",
    "bransAdi": "Futbol",
    "ikon": "⚽",
    "lig": "Trendyol Süper Lig",
    "tip": "futbol",
    "gun": 22,
    "ay": 10,
    "yil": 2026,
    "saat": "19:00",
    "aciklama": "⚽ 19:00 Konyaspor vs Beşiktaş (Süper Lig 12. Hafta)"
  },
  {
    "id": "real-euro-fb-baskonia",
    "takimlar": "Fenerbahçe Beko - Baskonia",
    "kisaAd": "FB Beko - Baskonia 🏆",
    "brans": "eurolig",
    "bransAdi": "EuroLig Basket",
    "ikon": "🏆",
    "lig": "EuroLeague",
    "tip": "eurolig",
    "gun": 4,
    "ay": 10,
    "yil": 2026,
    "saat": "20:45",
    "aciklama": "🏆 20:45 EuroLeague: Fenerbahçe Beko vs Baskonia"
  },
  {
    "id": "real-euro-paris-efes",
    "takimlar": "Paris Basketball - Anadolu Efes",
    "kisaAd": "Paris - Efes 🏆",
    "brans": "eurolig",
    "bransAdi": "EuroLig Basket",
    "ikon": "🏆",
    "lig": "EuroLeague",
    "tip": "eurolig",
    "gun": 5,
    "ay": 10,
    "yil": 2026,
    "saat": "20:30",
    "aciklama": "🏆 20:30 EuroLeague: Paris Basketball vs Anadolu Efes"
  },
  {
    "id": "real-euro-paris-fb",
    "takimlar": "Paris Basketball - Fenerbahçe Beko",
    "kisaAd": "Paris - FB Beko 🏆",
    "brans": "eurolig",
    "bransAdi": "EuroLig Basket",
    "ikon": "🏆",
    "lig": "EuroLeague",
    "tip": "eurolig",
    "gun": 11,
    "ay": 10,
    "yil": 2026,
    "saat": "22:45",
    "aciklama": "🏆 22:45 EuroLeague: Paris Basketball vs Fenerbahçe Beko"
  },
  {
    "id": "real-euro-efes-virtus",
    "takimlar": "Anadolu Efes - Virtus Bologna",
    "kisaAd": "Efes - Virtus Bologna 🏆",
    "brans": "eurolig",
    "bransAdi": "EuroLig Basket",
    "ikon": "🏆",
    "lig": "EuroLeague",
    "tip": "eurolig",
    "gun": 13,
    "ay": 10,
    "yil": 2026,
    "saat": "20:30",
    "aciklama": "🏆 20:30 EuroLeague: Anadolu Efes vs Virtus Bologna"
  },
  {
    "id": "real-euro-fb-asvel",
    "takimlar": "Fenerbahçe Beko - LDLC ASVEL",
    "kisaAd": "FB Beko - ASVEL 🏆",
    "brans": "eurolig",
    "bransAdi": "EuroLig Basket",
    "ikon": "🏆",
    "lig": "EuroLeague",
    "tip": "eurolig",
    "gun": 17,
    "ay": 10,
    "yil": 2026,
    "saat": "20:45",
    "aciklama": "🏆 20:45 EuroLeague: Fenerbahçe Beko vs LDLC ASVEL"
  },
  {
    "id": "real-euro-dubai-efes",
    "takimlar": "Dubai Basketball - Anadolu Efes",
    "kisaAd": "Dubai - Efes 🏆",
    "brans": "eurolig",
    "bransAdi": "EuroLig Basket",
    "ikon": "🏆",
    "lig": "EuroLeague",
    "tip": "eurolig",
    "gun": 17,
    "ay": 10,
    "yil": 2026,
    "saat": "20:00",
    "aciklama": "🏆 20:00 EuroLeague: Dubai Basketball vs Anadolu Efes"
  },
  {
    "id": "real-euro-milano-fb",
    "takimlar": "Olimpia Milano - Fenerbahçe Beko",
    "kisaAd": "Milano - FB Beko 🏆",
    "brans": "eurolig",
    "bransAdi": "EuroLig Basket",
    "ikon": "🏆",
    "lig": "EuroLeague",
    "tip": "eurolig",
    "gun": 19,
    "ay": 10,
    "yil": 2026,
    "saat": "22:30",
    "aciklama": "🏆 22:30 EuroLeague: Olimpia Milano vs Fenerbahçe Beko"
  },
  {
    "id": "real-euro-efes-asvel",
    "takimlar": "Anadolu Efes - LDLC ASVEL",
    "kisaAd": "Efes - ASVEL 🏆",
    "brans": "eurolig",
    "bransAdi": "EuroLig Basket",
    "ikon": "🏆",
    "lig": "EuroLeague",
    "tip": "eurolig",
    "gun": 20,
    "ay": 10,
    "yil": 2026,
    "saat": "20:30",
    "aciklama": "🏆 20:30 EuroLeague: Anadolu Efes vs LDLC ASVEL"
  },
  {
    "id": "real-vol-vakif-thy",
    "takimlar": "VakıfBank - THY",
    "kisaAd": "VakıfBank - THY 🏐",
    "brans": "voleybol",
    "bransAdi": "Voleybol",
    "ikon": "🏐",
    "lig": "Vodafone Sultanlar Ligi",
    "tip": "voleybol",
    "gun": 4,
    "ay": 10,
    "yil": 2026,
    "saat": "19:00",
    "aciklama": "🏐 19:00 Sultanlar Ligi: VakıfBank vs Türk Hava Yolları"
  },
  {
    "id": "real-vol-bjk-eczaci",
    "takimlar": "Beşiktaş - Eczacıbaşı",
    "kisaAd": "BJK - Eczacıbaşı 🏐",
    "brans": "voleybol",
    "bransAdi": "Voleybol",
    "ikon": "🏐",
    "lig": "Vodafone Sultanlar Ligi",
    "tip": "voleybol",
    "gun": 4,
    "ay": 10,
    "yil": 2026,
    "saat": "19:00",
    "aciklama": "🏐 19:00 Sultanlar Ligi: Beşiktaş vs Eczacıbaşı Peron"
  },
  {
    "id": "real-vol-nilufer-vakif",
    "takimlar": "Nilüfer Bld. - VakıfBank",
    "kisaAd": "Nilüfer - VakıfBank 🏐",
    "brans": "voleybol",
    "bransAdi": "Voleybol",
    "ikon": "🏐",
    "lig": "Vodafone Sultanlar Ligi",
    "tip": "voleybol",
    "gun": 8,
    "ay": 10,
    "yil": 2026,
    "saat": "16:00",
    "aciklama": "🏐 16:00 Sultanlar Ligi: Nilüfer Belediyespor vs VakıfBank"
  },
  {
    "id": "real-vol-eczaci-goztepe",
    "takimlar": "Eczacıbaşı - Göztepe",
    "kisaAd": "Eczacıbaşı - Göztepe 🏐",
    "brans": "voleybol",
    "bransAdi": "Voleybol",
    "ikon": "🏐",
    "lig": "Vodafone Sultanlar Ligi",
    "tip": "voleybol",
    "gun": 8,
    "ay": 10,
    "yil": 2026,
    "saat": "18:00",
    "aciklama": "🏐 18:00 Sultanlar Ligi: Eczacıbaşı vs Göztepe"
  },
  {
    "id": "real-vol-vakif-aras",
    "takimlar": "VakıfBank - Aras Kargo",
    "kisaAd": "VakıfBank - Aras Kargo 🏐",
    "brans": "voleybol",
    "bransAdi": "Voleybol",
    "ikon": "🏐",
    "lig": "Vodafone Sultanlar Ligi",
    "tip": "voleybol",
    "gun": 15,
    "ay": 10,
    "yil": 2026,
    "saat": "14:00",
    "aciklama": "🏐 14:00 Sultanlar Ligi: VakıfBank vs Aras Kargo"
  },
  {
    "id": "real-vol-zeren-eczaci",
    "takimlar": "Zeren Spor - Eczacıbaşı",
    "kisaAd": "Zeren Spor - Eczacıbaşı 🏐",
    "brans": "voleybol",
    "bransAdi": "Voleybol",
    "ikon": "🏐",
    "lig": "Vodafone Sultanlar Ligi",
    "tip": "voleybol",
    "gun": 15,
    "ay": 10,
    "yil": 2026,
    "saat": "17:00",
    "aciklama": "🏐 17:00 Sultanlar Ligi: Zeren Spor vs Eczacıbaşı"
  },
  {
    "id": "real-vol-eczaci-kuzey",
    "takimlar": "Eczacıbaşı - Kuzeyboru",
    "kisaAd": "Eczacıbaşı - Kuzeyboru 🏐",
    "brans": "voleybol",
    "bransAdi": "Voleybol",
    "ikon": "🏐",
    "lig": "Vodafone Sultanlar Ligi",
    "tip": "voleybol",
    "gun": 21,
    "ay": 10,
    "yil": 2026,
    "saat": "14:00",
    "aciklama": "🏐 14:00 Sultanlar Ligi: Eczacıbaşı vs Kuzeyboru"
  },
  {
    "id": "real-f1-brazil-sprint",
    "takimlar": "Formula 1 Brezilya GP (Sprint)",
    "kisaAd": "Brezilya GP (Sprint) 🏎️",
    "brans": "f1",
    "bransAdi": "Formula 1",
    "ikon": "🏎️",
    "lig": "Formula 1 Dünya Şampiyonası",
    "tip": "f1",
    "gun": 7,
    "ay": 10,
    "yil": 2026,
    "saat": "17:00",
    "aciklama": "🏎️ 17:00 Formula 1: Brezilya GP Sprint Yarışı"
  },
  {
    "id": "real-f1-brazil-gp",
    "takimlar": "Formula 1 Brezilya GP (Ana Yarış)",
    "kisaAd": "Brezilya GP (Ana Yarış) 🏎️",
    "brans": "f1",
    "bransAdi": "Formula 1",
    "ikon": "🏎️",
    "lig": "Formula 1 Dünya Şampiyonası",
    "tip": "f1",
    "gun": 8,
    "ay": 10,
    "yil": 2026,
    "saat": "20:00",
    "aciklama": "🏎️ 20:00 Formula 1: São Paulo (Brezilya) Grand Prix"
  },
  {
    "id": "real-f1-vegas-gp",
    "takimlar": "Formula 1 Las Vegas GP (Ana Yarış)",
    "kisaAd": "Las Vegas GP 🏎️",
    "brans": "f1",
    "bransAdi": "Formula 1",
    "ikon": "🏎️",
    "lig": "Formula 1 Dünya Şampiyonası",
    "tip": "f1",
    "gun": 22,
    "ay": 10,
    "yil": 2026,
    "saat": "09:00",
    "aciklama": "🏎️ 09:00 Formula 1: Las Vegas Grand Prix Gece Yarışı"
  },
  {
    "id": "real-nba-hou-bos",
    "takimlar": "Rockets (Alperen) - Celtics",
    "kisaAd": "Rockets - Celtics 🏀",
    "brans": "nba",
    "bransAdi": "NBA",
    "ikon": "🏀",
    "lig": "NBA Normal Sezon",
    "tip": "nba",
    "gun": 3,
    "ay": 10,
    "yil": 2026,
    "saat": "04:30",
    "aciklama": "🏀 04:30 NBA: Houston Rockets (Alperen Şengün) vs Boston Celtics"
  },
  {
    "id": "real-nba-hou-min",
    "takimlar": "Rockets (Alperen) - Timberwolves",
    "kisaAd": "Rockets - Wolves 🏀",
    "brans": "nba",
    "bransAdi": "NBA",
    "ikon": "🏀",
    "lig": "NBA Normal Sezon",
    "tip": "nba",
    "gun": 5,
    "ay": 10,
    "yil": 2026,
    "saat": "04:30",
    "aciklama": "🏀 04:30 NBA: Houston Rockets (Alperen Şengün) vs Minnesota Timberwolves"
  },
  {
    "id": "real-nba-phx-hou",
    "takimlar": "Suns - Rockets (Alperen)",
    "kisaAd": "Suns - Rockets 🏀",
    "brans": "nba",
    "bransAdi": "NBA",
    "ikon": "🏀",
    "lig": "NBA Normal Sezon",
    "tip": "nba",
    "gun": 8,
    "ay": 10,
    "yil": 2026,
    "saat": "05:00",
    "aciklama": "🏀 05:00 NBA: Phoenix Suns vs Houston Rockets (Alperen Şengün)"
  },
  {
    "id": "real-nba-hou-den",
    "takimlar": "Rockets (Alperen) - Nuggets (Jokic)",
    "kisaAd": "Rockets - Nuggets 🏀",
    "brans": "nba",
    "bransAdi": "NBA",
    "ikon": "🏀",
    "lig": "NBA Normal Sezon",
    "tip": "nba",
    "gun": 10,
    "ay": 10,
    "yil": 2026,
    "saat": "04:30",
    "aciklama": "🏀 04:30 NBA: Alperen Şengün vs Nikola Jokic (Rockets - Nuggets)"
  },
  {
    "id": "real-nba-hou-gsw",
    "takimlar": "Rockets (Alperen) - Warriors (Curry)",
    "kisaAd": "Rockets - Warriors 🏀",
    "brans": "nba",
    "bransAdi": "NBA",
    "ikon": "🏀",
    "lig": "NBA Normal Sezon",
    "tip": "nba",
    "gun": 12,
    "ay": 10,
    "yil": 2026,
    "saat": "05:30",
    "aciklama": "🏀 05:30 NBA: Rockets (Alperen) vs Golden State Warriors (Curry)"
  },
  {
    "id": "real-nba-hou-uta",
    "takimlar": "Rockets (Alperen) - Jazz",
    "kisaAd": "Rockets - Jazz 🏀",
    "brans": "nba",
    "bransAdi": "NBA",
    "ikon": "🏀",
    "lig": "NBA Cup",
    "tip": "nba",
    "gun": 14,
    "ay": 10,
    "yil": 2026,
    "saat": "04:30",
    "aciklama": "🏀 04:30 NBA Cup: Houston Rockets vs Utah Jazz"
  },
  {
    "id": "real-ten-atp-open",
    "takimlar": "ATP Finalleri (Torino) Açılış Maçları",
    "kisaAd": "ATP Finalleri Açılış 🎾",
    "brans": "tenis",
    "bransAdi": "Tenis",
    "ikon": "🎾",
    "lig": "Nitto ATP Finals (Torino)",
    "tip": "tenis",
    "gun": 15,
    "ay": 10,
    "yil": 2026,
    "saat": "16:00",
    "aciklama": "🎾 16:00 Nitto ATP Finalleri (Torino) Sezon Sonu Zirvesi Açılış Karşılaşmaları"
  },
  {
    "id": "real-ten-atp-semi",
    "takimlar": "ATP Finalleri Yarı Final",
    "kisaAd": "ATP Finalleri Yarı Final 🎾",
    "brans": "tenis",
    "bransAdi": "Tenis",
    "ikon": "🎾",
    "lig": "Nitto ATP Finals (Torino)",
    "tip": "tenis",
    "gun": 21,
    "ay": 10,
    "yil": 2026,
    "saat": "16:30",
    "aciklama": "🎾 16:30 Nitto ATP Finalleri (Torino) Yarı Final Karşılaşmaları"
  },
  {
    "id": "real-ten-atp-final",
    "takimlar": "ATP Finalleri Şampiyonluk Maçı",
    "kisaAd": "ATP Finalleri Final 🎾",
    "brans": "tenis",
    "bransAdi": "Tenis",
    "ikon": "🎾",
    "lig": "Nitto ATP Finals (Torino)",
    "tip": "tenis",
    "gun": 22,
    "ay": 10,
    "yil": 2026,
    "saat": "18:00",
    "aciklama": "🎾 18:00 Nitto ATP Finalleri (Torino) Sezon Sonu Şampiyonluk Maçı"
  }
];

async function senkronizeGeminiMatches() {
  try {
    const res = await fetch(`${FIREBASE_DB_URL}/gemini_matches.json?t=${Date.now()}`);
    if (res.ok) {
      const data = await res.json();
      if (data && Array.isArray(data.matches)) {
        // Eski sahte (mock) maçları anında filtrele
        const filtered = data.matches.filter(m => !MOCK_MATCH_IDS.has(m.id));
        if (JSON.stringify(filtered) !== JSON.stringify(state.geminiMatches)) {
          state.geminiMatches = filtered.length > 0 ? filtered : [...GEMINI_AI_FIXTURES];
          localStorage.setItem("tellal_gemini_matches", JSON.stringify(state.geminiMatches));
          renderMonthCalendar();
        }
      }
    }
  } catch (err) {
    console.warn("Gemini maç senkronizasyon:", err);
  }
}

function openGeminiAiModal() {
  const modal = document.getElementById("geminiAiModalOverlay");
  if (!modal) return;
  modal.style.display = "flex";
  setTimeout(() => modal.classList.add("open"), 10);
  const status = document.getElementById("geminiNlpStatus");
  if (status) status.style.display = "none";
  const input = document.getElementById("geminiNlpInput");
  if (input) input.focus();
}

function closeGeminiAiModal() {
  const modal = document.getElementById("geminiAiModalOverlay");
  if (!modal) return;
  modal.classList.remove("open");
  setTimeout(() => { modal.style.display = "none"; }, 250);
}

async function handleGeminiQuickSync() {
  const btnText = document.getElementById("geminiQuickSyncText");
  if (btnText) btnText.textContent = "⏳ Fikstür Yükleniyor...";
  
  await runGeminiAiMatchScanner(true);
  
  if (btnText) btnText.textContent = "✓ 21 Günlük Fikstür Yüklendi!";
  setTimeout(() => {
    if (btnText) btnText.textContent = "21 Günlük Teyitli Fikstürü Takvime Yükle";
    closeGeminiAiModal();
  }, 900);
}

async function handleGeminiParseAdd() {
  const input = document.getElementById("geminiNlpInput");
  const status = document.getElementById("geminiNlpStatus");
  const btn = document.getElementById("btnGeminiParseAdd");
  const btnText = document.getElementById("geminiParseBtnText");
  if (!input || !status) return;

  const rawText = input.value.trim();
  if (!rawText) {
    status.style.display = "block";
    status.style.background = "rgba(239, 68, 68, 0.15)";
    status.style.color = "#f87171";
    status.style.border = "1px solid rgba(239, 68, 68, 0.3)";
    status.innerHTML = "⚠️ Lütfen bir maç bilgisi veya duyuru metni yazın.";
    return;
  }

  if (btn) btn.disabled = true;
  if (btnText) btnText.textContent = "✨ Gemini Çözümlüyor...";
  status.style.display = "block";
  status.style.background = "rgba(139, 92, 246, 0.15)";
  status.style.color = "#c4b5fd";
  status.style.border = "1px solid rgba(139, 92, 246, 0.3)";
  status.innerHTML = "⏳ Google Gemini 3.5 Flash yapay zekâsı metni analiz ediyor...";

  try {
    const parsedMatch = await callGeminiToParseMatch(rawText);
    if (!parsedMatch || !parsedMatch.takimlar || !parsedMatch.gun) {
      throw new Error("Yapay zekâ maç bilgilerini net olarak çıkaramadı.");
    }

    // Takvime ekle
    state.geminiMatches.push(parsedMatch);
    localStorage.setItem("tellal_gemini_matches", JSON.stringify(state.geminiMatches));
    localStorage.setItem("corvus_gemini_matches", JSON.stringify(state.geminiMatches));

    // Firebase Realtime Database'e kaydet
    await fetch(`${FIREBASE_DB_URL}/gemini_matches.json`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        matches: state.geminiMatches,
        son_guncelleme: Math.floor(Date.now() / 1000),
        kaynak: "Gemini AI Serbest Metin"
      })
    });

    renderMonthCalendar();

    status.style.background = "rgba(16, 185, 129, 0.15)";
    status.style.color = "#34d399";
    status.style.border = "1px solid rgba(16, 185, 129, 0.3)";
    status.innerHTML = `✅ <strong>Eklendi:</strong> ${escapeHtml(parsedMatch.takimlar)} (${parsedMatch.gun} ${AY_ISIMLERI[parsedMatch.ay]} ${parsedMatch.saat})`;

    showToast(`✅ ${parsedMatch.takimlar} takvime eklendi!`, "success");
    input.value = "";

    setTimeout(() => {
      closeGeminiAiModal();
    }, 1500);
  } catch (err) {
    status.style.background = "rgba(239, 68, 68, 0.15)";
    status.style.color = "#f87171";
    status.style.border = "1px solid rgba(239, 68, 68, 0.3)";
    status.innerHTML = `⚠️ Hata: ${escapeHtml(err.message || "Bağlantı hatası")}`;
  } finally {
    if (btn) btn.disabled = false;
    if (btnText) btnText.textContent = "Gemini ile Çözümle ve Takvime Ekle";
  }
}

async function callGeminiToParseMatch(text) {
  const apiKey = await getGeminiApiKey();
  if (!apiKey) {
    throw new Error("Gemini API anahtarı yapılandırılmamış.");
  }
  const now = new Date();
  const prompt = `Aşağıdaki metinden maç / spor karşılaşması bilgilerini çıkarıp tek bir JSON objesi döndür:
Metin: "${text}"
Bugünün referans tarihi: ${now.getDate()} ${AY_ISIMLERI[now.getMonth()]} ${now.getFullYear()}.
Zorunlu JSON Formatı:
{
  "id": "gemini-${Date.now()}",
  "takimlar": "Ev Sahibi - Deplasman (veya F1 için Grand Prix Adı)",
  "kisaAd": "Kısa başlık (örn: FB Beko - ASVEL 🏆)",
  "brans": "futbol" | "voleybol" | "nba" | "eurolig" | "tenis" | "f1",
  "bransAdi": "Futbol" | "Voleybol" | "NBA" | "EuroLig Basket" | "Tenis" | "Formula 1",
  "ikon": "⚽" | "🏐" | "🏀" | "🏆" | "🎾" | "🏎️",
  "lig": "Lig veya Turnuva Adı (örn: Turkish Airlines EuroLeague)",
  "gun": GünSayısı (1-31),
  "ay": AyIndex (0=Ocak, 1=Şubat, 2=Mart, 3=Nisan, 4=Mayıs, 5=Haziran, 6=Temmuz, 7=Ağustos, 8=Eylül, 9=Ekim, 10=Kasım, 11=Aralık),
  "yil": Yıl (örn: 2026),
  "saat": "HH:MM",
  "aciklama": "Detaylı açıklama"
}`;

  const res = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key=${apiKey}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      contents: [{ parts: [{ text: prompt }] }],
      generationConfig: { responseMimeType: "application/json" }
    })
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.error?.message || `HTTP ${res.status}`);
  }

  const data = await res.json();
  const rawJson = data.candidates?.[0]?.content?.parts?.[0]?.text;
  if (!rawJson) throw new Error("Gemini geçerli bir yanıt üretemedi.");
  return JSON.parse(rawJson);
}

async function runGeminiAiMatchScanner(isManual = false) {
  if (isManual && state.userRole === "yonetici") {
    showToast("Gemini AI tarayıcı yetkisi yalnızca Admin rolündedir.", "warning");
    return;
  }

  const now = new Date();
  const todayDay = now.getDate();
  const thisMonth = now.getMonth();
  const thisYear = now.getFullYear();

  // GEMINI_AI_FIXTURES ve mevcut teyitli maçları birleştir
  const mergedMap = new Map();
  GEMINI_AI_FIXTURES.forEach(m => {
    mergedMap.set(m.id, m);
  });
  (state.geminiMatches || []).forEach(m => {
    if (!MOCK_MATCH_IDS.has(m.id)) {
      mergedMap.set(m.id, m);
    }
  });

  // Bugünden önceki geçmiş günlerin maçlarını filtrele
  state.geminiMatches = Array.from(mergedMap.values()).filter(m => {
    if (m.yil < thisYear) return false;
    if (m.yil === thisYear && m.ay < thisMonth) return false;
    if (m.yil === thisYear && m.ay === thisMonth && m.gun < todayDay) return false;
    return true;
  });

  localStorage.setItem("tellal_gemini_matches", JSON.stringify(state.geminiMatches));
  localStorage.setItem("corvus_gemini_matches", JSON.stringify(state.geminiMatches));

  // Normal takvimi yeniden render et
  renderMonthCalendar();

  // Firebase RTDB gemini_matches.json tablosuna kaydet
  try {
    await fetch(`${FIREBASE_DB_URL}/gemini_matches.json`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        matches: state.geminiMatches,
        son_guncelleme: Math.floor(Date.now() / 1000),
        kaynak: "Gemini AI (Doğrulanmış 21 Günlük Fikstür)"
      })
    });
  } catch (e) {
    console.warn("Gemini matches bulut kaydı hatası:", e);
  }

  if (isManual) {
    showToast(`✨ Gemini AI: 21 günlük ${state.geminiMatches.length} karşılaşma takvime başarıyla işlendi!`, "success");
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

// 1. Gemini AI Karşılaşma Etkinliği Detay Modalı (Futbol, Voleybol, NBA, EuroLig, Tenis, F1)
function openGeminiMatchModal(matchId) {
  const match = (state.geminiMatches || []).find(m => m.id === matchId);
  if (!match) return;

  const modal = document.getElementById("eventActionModal");
  const modalTitleText = document.getElementById("eventModalTitleText");
  const modalIcon = document.getElementById("eventModalIcon");
  const modalBody = document.getElementById("eventModalBody");
  const modalFooter = document.getElementById("eventModalFooter");

  if (!modal || !modalBody || !modalFooter) return;

  const brans = match.brans || (match.tip === "milli" ? "futbol" : (match.tip || "futbol"));
  const icon = match.ikon || (brans === "voleybol" ? "🏐" : brans === "nba" ? "🏀" : brans === "eurolig" ? "🏆" : brans === "tenis" ? "🎾" : brans === "f1" ? "🏎️" : "⚽");
  const bransAdi = match.bransAdi || (brans === "voleybol" ? "Voleybol" : brans === "nba" ? "NBA" : brans === "eurolig" ? "EuroLig Basket" : brans === "tenis" ? "Tenis" : brans === "f1" ? "Formula 1" : "Futbol");

  const isF1 = brans === "f1";
  const [evSahibi, deplasman] = (!isF1 && match.takimlar.includes(" - "))
    ? match.takimlar.split(" - ")
    : [match.takimlar, ""];

  const ayAdi = AY_ISIMLERI[match.ay] || "";
  const gunDate = new Date(match.yil, match.ay, match.gun);
  const gunAdi = GUN_ADLARI[(gunDate.getDay() + 6) % 7] || "";
  const formattedTarih = `${match.gun} ${ayAdi} ${match.yil} (${gunAdi})`;

  if (modalIcon) modalIcon.textContent = icon;
  if (modalTitleText) modalTitleText.textContent = `${bransAdi} Karşılaşması`;

  modalBody.innerHTML = `
    <div class="event-detail-card">
      <div class="event-detail-header-card">
        <div class="event-detail-teams">${escapeHtml(evSahibi)} ${deplasman ? `<span style="color:var(--text-muted);font-weight:400;font-size:0.95rem;margin:0 6px;">vs</span> ${escapeHtml(deplasman)}` : ""}</div>
        <div class="event-detail-sub">
          <span class="ai-badge">${icon} ${escapeHtml(match.lig || bransAdi)}</span>
          <span class="stat-badge primary">${escapeHtml(match.saat)}</span>
        </div>
      </div>

      <div class="event-detail-grid">
        <div class="event-detail-row">
          <span class="event-detail-label">${isF1 ? "Grand Prix / Yarış" : "Ev Sahibi / 1. Taraf"}</span>
          <span class="event-detail-value">${escapeHtml(evSahibi)}</span>
        </div>
        <div class="event-detail-row">
          <span class="event-detail-label">${isF1 ? "Şampiyona" : "Deplasman / 2. Taraf"}</span>
          <span class="event-detail-value">${escapeHtml(deplasman || (isF1 ? "F1 Dünya Şampiyonası" : "-"))}</span>
        </div>
        <div class="event-detail-row">
          <span class="event-detail-label">Lig / Turnuva</span>
          <span class="event-detail-value">${escapeHtml(match.lig || bransAdi)}</span>
        </div>
        <div class="event-detail-row">
          <span class="event-detail-label">Başlama Saati</span>
          <span class="event-detail-value">⏰ ${escapeHtml(match.saat)}</span>
        </div>
      </div>

      <div class="event-detail-row" style="grid-column: 1 / -1;">
        <span class="event-detail-label">Tarih</span>
        <span class="event-detail-value">📅 ${escapeHtml(formattedTarih)}</span>
      </div>
    </div>
  `;

  const isYonetici = (state.userRole === "yonetici");
  modalFooter.innerHTML = `
    <button type="button" class="btn btn-secondary" onclick="closeEventModal()">Kapat</button>
    ${isYonetici ? "" : `
      <button type="button" class="btn btn-danger" onclick="removeGeminiMatch('${escapeHtml(match.id)}')">
        <span>🗑️</span>
        <span>Takvimden Kaldır</span>
      </button>
      <button type="button" class="btn btn-primary" onclick="geminiMacaYayinEkle('${escapeHtml(match.id)}')">
        <span>➕</span>
        <span>Bu Karşılaşma İçin Yayın Ekle</span>
      </button>
    `}
  `;

  modal.classList.add("open");
}

// 2. Maçı Takvimden Kaldırma (state, localStorage ve Firebase RTDB gemini_matches.json tablosundan silinir)
async function removeGeminiMatch(matchId) {
  if (state.userRole === "yonetici") {
    showToast("Maç kaldırma yetkiniz bulunmamaktadır.", "warning");
    return;
  }
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

  const isYonetici = (state.userRole === "yonetici");
  modalFooter.innerHTML = `
    <button type="button" class="btn btn-secondary" onclick="closeEventModal()">Kapat</button>
    ${isYonetici ? "" : `
      <button type="button" class="btn btn-warning" onclick="closeEventModal(); openEditBroadcastModal(${item.index})">
        <span>✏️</span>
        <span>Yayını Düzenle</span>
      </button>
      <button type="button" class="btn btn-danger" onclick="silYayinFromModal(${item.index})">
        <span>🗑️</span>
        <span>Yayını Takvimden Kaldır / Sil</span>
      </button>
    `}
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
  if (state.userRole === "yonetici") {
    showToast("Yayın ekleme yetkiniz bulunmamaktadır.", "warning");
    return;
  }
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

  // 6. Ek not bilgi bölümüne "X - Y takımı maçı" veya "X Yarışı" yaz
  const bilgiInput = document.getElementById("inputBilgi");
  if (bilgiInput) {
    if (match && match.brans === "f1") {
      bilgiInput.value = `${takimlar} Yarışı`;
    } else {
      bilgiInput.value = `${takimlar} maçı`;
    }
  }

  // 7. Modalı aç (seçilen program ve saati koruyarak)
  openAddModal(false);
  const bransIkon = match ? (match.ikon || "🏆") : "⚽";
  showToast(`${bransIkon} "${takimlar}" için Canlı Maç Sohbeti yayını 15 dk öncesine (${yayinSaati}) planlandı.`, "info");
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

    // 2. İkincil: Ntfy Kanalına Bildir (Corvus'ta ses çalması ve senkronize olması için)
    await fetch("https://ntfy.sh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        topic: "tellal_chat_sync_u_y_8832",
        title: "Corvus Chat Güncellemesi",
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

// 9.5. CANLİ HAVA DURUMU (WEATHERSTACK) YÖNETİMİ
function getWeatherEmoji(desc) {
  if (!desc) return "🌤️";
  const d = desc.toLowerCase().trim();
  if (d.includes("sun") || d.includes("clear") || d.includes("açık") || d.includes("güneş")) return "☀️";
  if (d.includes("partly") || d.includes("parçalı")) return "⛅";
  if (d.includes("overcast") || d.includes("cloud") || d.includes("bulut") || d.includes("kapalı")) return "☁️";
  if (d.includes("thunder") || d.includes("fırtına")) return "⛈️";
  if (d.includes("snow") || d.includes("kar")) return "❄️";
  if (d.includes("fog") || d.includes("mist") || d.includes("sis") || d.includes("pus")) return "🌫️";
  if (d.includes("rain") || d.includes("drizzle") || d.includes("yağmur")) return "🌧️";
  return "🌤️";
}

async function loadAndDisplayWeather(showToastOnClick = false) {
  const iconElem = document.getElementById("weatherIcon");
  const cityElem = document.getElementById("weatherCity");
  const tempElem = document.getElementById("weatherTemp");
  const badgeElem = document.getElementById("btnWeatherBadge");
  if (!badgeElem) return;

  const userName = state.currentUser || "Ufuk Çelen";
  const userCity = USER_CITY_MAP[userName] || { cityKey: "Istanbul", displayName: "İstanbul", lat: 41.0082, lon: 28.9784 };

  let weatherData = null;

  // 1. Birincil Kaynak: Firebase Realtime Database
  try {
    const res = await fetch(`${FIREBASE_DB_URL}/weather/${encodeURIComponent(userName)}.json?t=${Date.now()}`);
    if (res.ok) {
      const data = await res.json();
      // Veri varsa ve son 4 saatten eskiyse veya geçersizse doğrudan Open-Meteo'ya geç
      const nowSec = Math.floor(Date.now() / 1000);
      const isFresh = data && data.son_guncelleme && (nowSec - data.son_guncelleme < 14400);

      if (data && data.sicaklik !== undefined && isFresh) {
        weatherData = data;
      }
    }
  } catch (err) {
    console.warn("Firebase hava durumu okuma uyarısı:", err);
  }

  // 2. Yedek & Kendi Kendini Onarma Kaynağı: Open-Meteo API (Doğrudan istemci üzerinden sınırsız & canlı)
  if (!weatherData && userCity.lat && userCity.lon) {
    try {
      const omUrl = `https://api.open-meteo.com/v1/forecast?latitude=${userCity.lat}&longitude=${userCity.lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m&timezone=auto`;
      const omRes = await fetch(omUrl);
      if (omRes.ok) {
        const omJson = await omRes.json();
        const curr = omJson.current;
        if (curr) {
          const wcode = curr.weather_code || 0;
          let durumText = "Açık";
          if (wcode === 1 || wcode === 2) durumText = "Parçalı Bulutlu";
          else if (wcode === 3) durumText = "Bulutlu";
          else if (wcode === 45 || wcode === 48) durumText = "Sisli";
          else if (wcode >= 51 && wcode <= 55) durumText = "Çisenti";
          else if (wcode >= 61 && wcode <= 65) durumText = "Yağmurlu";
          else if (wcode >= 71 && wcode <= 77) durumText = "Karlı";
          else if (wcode >= 80 && wcode <= 82) durumText = "Sağanak Yağışlı";
          else if (wcode >= 95) durumText = "Gök Gürültülü Fırtına";

          weatherData = {
            sehir: userCity.displayName,
            sicaklik: Math.round(curr.temperature_2m),
            hissedilen: Math.round(curr.apparent_temperature ?? curr.temperature_2m),
            durum: durumText,
            nem: Math.round(curr.relative_humidity_2m),
            ruzgar: Math.round(curr.wind_speed_10m),
            son_guncelleme: Math.floor(Date.now() / 1000),
            kaynak: "Open-Meteo"
          };
        }
      }
    } catch (omErr) {
      console.warn("Open-Meteo canlı çekme uyarısı:", omErr);
    }
  }

  // Arayüzü Güncelle
  if (weatherData) {
    currentWeatherCache = weatherData;
    const durumRaw = (weatherData.durum || "").trim();
    const durumTr = WEATHER_DESC_TR[durumRaw.toLowerCase()] || durumRaw || "Açık";
    const emoji = getWeatherEmoji(durumRaw);

    if (iconElem) iconElem.textContent = emoji;
    if (cityElem) cityElem.textContent = weatherData.sehir || userCity.displayName;
    if (tempElem) tempElem.textContent = `${weatherData.sicaklik}°C`;

    const tooltip = `${weatherData.sehir}: ${weatherData.sicaklik}°C (${durumTr}) • Hissedilen: ${weatherData.hissedilen ?? weatherData.sicaklik}°C • Nem: %${weatherData.nem ?? "-"} • Rüzgar: ${weatherData.ruzgar ?? "-"} km/s`;
    badgeElem.title = `${tooltip} (Detay için tıklayın)`;

    if (showToastOnClick) {
      showToast(`🌤️ ${weatherData.sehir}: ${weatherData.sicaklik}°C (${durumTr}) • Hissedilen: ${weatherData.hissedilen}°C • Nem: %${weatherData.nem} • Rüzgar: ${weatherData.ruzgar} km/s`, "info");
    }
  } else {
    if (cityElem) cityElem.textContent = userCity.displayName;
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
