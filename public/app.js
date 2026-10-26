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

// Başlangıç Mock / Fallback Verileri (İlk açılışta boş kalmaması için)
const DEFAULT_YAYINLAR = [
  "1-) Haftalık Program - Pazartesi - 20:00 | Bilgi: Canlı Yayın Planı ✅",
  "2-) Canlı Maç (Fenerbahçe - Galatasaray) - Çarşamba - 20:30 | Bilgi: Derbi Özel Yayını",
  "3-) Filtresiz Memleket Havası - Perşembe - 21:00 | Bilgi: Gündem ve Sohbet",
  "4-) Albert ve Cem - Cuma - 21:30 | Bilgi: Yeni Bölüm",
  "5-) FC 27 Kariyer - Pazar - 18:00 | Bilgi: 12. Bölüm"
];

// DOM Yüklendiğinde Başlat
document.addEventListener("DOMContentLoaded", () => {
  initUser();
  initCalendarData();
  setupEventListeners();
  startNtfyPolling();
  initMonthCalendar();
  initChat();
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
    } catch (e) {
      state.yayinlar = [];
    }
  }
  renderCalendar();
  updateStats();

  // Doğrudan Firebase Bulut Veritabanından en güncel veriyi çek ve eşitle
  await senkronizeEtUzak(false);
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
    yayinAdi = segmentler[0].trim();
    if (segmentler.length > 1) gun = segmentler[1].trim();
    if (segmentler.length > 2) saat = segmentler[2].trim();
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
  const program = document.getElementById("inputProgram").value.trim();
  const kanal = document.getElementById("inputKanal").value;
  const gun = document.getElementById("inputGun").value.trim();
  const saat = document.getElementById("inputSaat").value.trim();
  const bilgi = document.getElementById("inputBilgi").value.trim();

  if (!program || !gun || !saat) {
    showToast("Lütfen program adı, gün ve saat alanlarını doldurun.", "warning");
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

  // Ntfy üzerinden buluta ve masaüstü tellal.py'ye aktar!
  yayinlariBulutaGonder(`${state.currentUser} webden yeni yayın ekledi: ${program}`);
  showToast(`✓ "${program}" yayını başarıyla takvime eklendi ve Tellal Cloud'a senkronize edildi!`, "success");
}

// 6. Yayın Durumu Değiştirme (Tamamla / İptal)
function toggleYayinDurumu(index, action) {
  if (index < 0 || index >= state.yayinlar.length) return;
  let satir = state.yayinlar[index];

  if (action === "done") {
    if (satir.includes("✅")) {
      satir = satir.replace(" ✅", "");
      showToast("Duyuru işareti kaldırıldı.", "info");
    } else {
      satir = satir.replace(" ❌", "");
      if (satir.includes(" - ")) {
        const parcalar = satir.split(" - ", 2);
        satir = `${parcalar[0]} ✅ - ${satir.substring(parcalar[0].length + 3)}`;
      } else {
        satir += " ✅";
      }
      showToast("✓ Yayın duyurusu tamamlandı olarak işaretlendi!", "success");
    }
  } else if (action === "cancel") {
    if (satir.includes("❌")) {
      satir = satir.replace(" ❌", "");
      showToast("İptal işareti kaldırıldı.", "info");
    } else {
      satir = satir.replace(" ✅", "");
      if (satir.includes(" - ")) {
        const parcalar = satir.split(" - ", 2);
        satir = `${parcalar[0]} ❌ - ${satir.substring(parcalar[0].length + 3)}`;
      } else {
        satir += " ❌";
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
        } else if (Array.isArray(data.satirlar)) {
          gelenSatirlar = data.satirlar.filter(s => s && s.trim());
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

  if (modalOverlay) {
    modalOverlay.addEventListener("click", (e) => {
      if (e.target === modalOverlay) closeAddModal();
    });
  }

  // Form submit
  const form = document.getElementById("addBroadcastForm");
  if (form) form.addEventListener("submit", yeniYayinKaydet);

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

  // Hızlı Gün Seçimi için Dinamik Doldurma
  setupGunOptions();
}

function setupGunOptions() {
  const gunSelect = document.getElementById("inputGun");
  if (!gunSelect) return;

  const gunler = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"];
  const d = new Date();
  const bugunIdx = (d.getDay() + 6) % 7; // Pazartesi = 0

  gunSelect.innerHTML = `
    <option value="Bugün">Bugün (${gunler[bugunIdx]})</option>
    <option value="Yarın">Yarın (${gunler[(bugunIdx + 1) % 7]})</option>
    ${gunler.map(g => `<option value="${g}">${g}</option>`).join("")}
  `;
}

function openAddModal() {
  const modal = document.getElementById("addBroadcastModal");
  if (modal) {
    modal.classList.add("open");
    document.getElementById("inputProgram").focus();
  }
}

function closeAddModal() {
  const modal = document.getElementById("addBroadcastModal");
  if (modal) modal.classList.remove("open");
}

// =====================================================================
// AYLIK TAKVİM FONKSİYONLARI
// =====================================================================
const AY_ISIMLERI = [
  "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
  "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"
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

  title.innerHTML = `<span>🗓️</span> <span>${AY_ISIMLERI[state.calendarMonth]} ${state.calendarYear} Yayın Takvimi</span>`;

  const now = new Date();
  const isThisMonth = (now.getFullYear() === state.calendarYear && now.getMonth() === state.calendarMonth);
  const todayDate = now.getDate();

  const firstDay = new Date(state.calendarYear, state.calendarMonth, 1);
  const firstDayIndex = (firstDay.getDay() + 6) % 7; // 0 = Pazartesi, 6 = Pazar
  const daysInMonth = new Date(state.calendarYear, state.calendarMonth + 1, 0).getDate();
  const prevMonthDays = new Date(state.calendarYear, state.calendarMonth, 0).getDate();

  const parsedItems = state.yayinlar.map((s, i) => parseYayinSatiri(s, i));

  let html = "";

  // 1. Önceki aydan kalan günler
  for (let i = firstDayIndex - 1; i >= 0; i--) {
    const prevDayNum = prevMonthDays - i;
    html += `
      <div class="calendar-day-cell other-month">
        <div class="day-header-row">
          <span class="day-number">${prevDayNum}</span>
        </div>
      </div>
    `;
  }

  // 2. Bu ayın günleri
  for (let d = 1; d <= daysInMonth; d++) {
    const isToday = isThisMonth && (d === todayDate);
    const dayDate = new Date(state.calendarYear, state.calendarMonth, d);
    const dayOfWeek = (dayDate.getDay() + 6) % 7;
    const dayName = GUN_ADLARI[dayOfWeek];

    const matchingBroadcasts = parsedItems.filter(item => {
      const g = item.gun.toLowerCase().trim();
      const targetName = dayName.toLowerCase();

      if (g.includes(targetName)) return true;
      if (g.includes("bugün") && isToday) return true;
      if (g.includes("yarın") && isThisMonth && d === (todayDate + 1)) return true;

      const monthNameLower = AY_ISIMLERI[state.calendarMonth].toLowerCase();
      if (g.includes(`${d} ${monthNameLower}`) || g === `${d}`) return true;

      return false;
    });

    let badgesHtml = "";
    if (matchingBroadcasts.length > 0) {
      badgesHtml = `
        <div class="day-events-container">
          ${matchingBroadcasts.map(b => {
            const badgeClass = b.isDone ? "done" : (b.isCanceled ? "canceled" : "");
            return `
              <div class="day-broadcast-badge ${badgeClass}" 
                   title="${escapeHtml(b.saat)} - ${escapeHtml(b.yayinAdi)} (${escapeHtml(b.kanal)})"
                   onclick="filterByCalendarBroadcast('${escapeHtml(b.yayinAdi)}')">
                ${escapeHtml(b.saat)} ${escapeHtml(b.yayinAdi)}
              </div>
            `;
          }).join("")}
        </div>
      `;
    }

    html += `
      <div class="calendar-day-cell ${isToday ? "today-cell" : ""}" data-day="${d}" onclick="selectCalendarDay(${d}, '${dayName}')">
        <div class="day-header-row">
          <span class="day-number">${d}</span>
          ${isToday ? `<span class="today-badge-dot">Bugün</span>` : ""}
        </div>
        ${badgesHtml}
      </div>
    `;
  }

  // 3. Gelecek aydan kalan günler (grid'i tamamlamak için)
  const totalCells = firstDayIndex + daysInMonth;
  const remainingCells = (totalCells % 7 === 0) ? 0 : 7 - (totalCells % 7);
  for (let n = 1; n <= remainingCells; n++) {
    html += `
      <div class="calendar-day-cell other-month">
        <div class="day-header-row">
          <span class="day-number">${n}</span>
        </div>
      </div>
    `;
  }

  grid.innerHTML = html;
}

function selectCalendarDay(day, dayName) {
  const gunSelect = document.getElementById("inputGun");
  if (gunSelect) {
    for (let opt of gunSelect.options) {
      if (opt.value === dayName) {
        gunSelect.value = dayName;
        break;
      }
    }
  }
  showToast(`🗓️ ${day} ${AY_ISIMLERI[state.calendarMonth]} (${dayName}) seçildi. Yeni yayın ekleyebilirsiniz.`, "info");
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
      let rawList = [];
      if (data && Array.isArray(data.mesajlar)) {
        rawList = data.mesajlar.filter(m => m && m.trim());
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

    if (sLower.includes("ufuk")) {
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
