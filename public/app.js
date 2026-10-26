/**
 * Tellal Cloud Web Portal - JavaScript Logic
 * Firebase Hosting & Ntfy Realtime Sync Desteği
 */

// Global State
const NTFY_TOPIC_TAKVIM = "tellal_takvim_sync_u_y_8832";
const STORAGE_KEY_TAKVIM = "tellal_web_takvim";
const STORAGE_KEY_USER = "tellal_web_user";

let state = {
  currentUser: localStorage.getItem(STORAGE_KEY_USER) || "3. Kullanıcı (Editör)",
  yayinlar: [],
  activeFilter: "all",
  searchQuery: "",
  isSyncing: false,
  lastSyncTime: 0
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
  updateClock();
  setInterval(updateClock, 1000);
});

// 1. Kullanıcı Yönetimi
function initUser() {
  const userElem = document.getElementById("activeUserName");
  if (userElem) userElem.textContent = state.currentUser;
}

function switchUser() {
  const current = state.currentUser;
  const yeniAd = prompt("Aktif Kullanıcı İsminizi Girin (Örn: Editör, Ayşe, 3. Kullanıcı):", current);
  if (yeniAd && yeniAd.trim()) {
    state.currentUser = yeniAd.trim();
    localStorage.setItem(STORAGE_KEY_USER, state.currentUser);
    initUser();
    showToast(`Aktif kullanıcı "${state.currentUser}" olarak güncellendi.`, "info");
  }
}

// 2. Takvim Verisi Yükleme & Parse Etme
async function initCalendarData() {
  // Önce doğrudan Firebase Bulut Veritabanından çekmeyi dene
  await senkronizeEtUzak(false);

  // Eğer buluttan henüz gelmediyse veya boşsa yerel depolamaya bak
  if (state.yayinlar.length === 0) {
    const localData = localStorage.getItem(STORAGE_KEY_TAKVIM);
    if (localData) {
      try {
        state.yayinlar = JSON.parse(localData);
      } catch (e) {
        state.yayinlar = [...DEFAULT_YAYINLAR];
      }
    } else {
      state.yayinlar = [...DEFAULT_YAYINLAR];
      kaydetYerel();
    }
  }

  renderCalendar();
  updateStats();
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

  let guncellendi = false;

  // 1. Önce Firebase Realtime Database'den en güncel takvimi çek
  try {
    const res = await fetch(`${FIREBASE_DB_URL}/takvim.json?t=${Date.now()}`);
    if (res.ok) {
      const data = await res.json();
      if (data && Array.isArray(data.satirlar)) {
        if (JSON.stringify(data.satirlar) !== JSON.stringify(state.yayinlar)) {
          state.yayinlar = data.satirlar;
          kaydetYerel();
          renderCalendar();
          updateStats();
          guncellendi = true;
          if (bildirimVer) {
            const kimden = data.guncelleyen ? `(${data.guncelleyen})` : "";
            showToast(`✓ Firebase Buluttan en güncel takvim eşitlendi! ${kimden}`, "success");
          }
        } else if (bildirimVer) {
          showToast("Takvim güncel.", "info");
        }
      }
    }
  } catch (err) {
    console.warn("Firebase RTDB okunamadı, Ntfy deneniyor:", err);
  }

  // 2. Eğer Firebase'den alınamadıysa fallback olarak Ntfy'yi dene
  if (!guncellendi) {
    try {
      const url = `https://ntfy.sh/${NTFY_TOPIC_TAKVIM}/json?poll=1&since=all`;
      const res = await fetch(url);
      if (res.ok) {
        const text = await res.text();
        const lines = text.trim().split("\n");
        let enYeniMesaj = null;

        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const d = JSON.parse(line);
            if (d.event === "message" && d.time >= state.lastSyncTime) {
              enYeniMesaj = d;
              state.lastSyncTime = d.time;
            }
          } catch (e) {}
        }

        if (enYeniMesaj && enYeniMesaj.message) {
          let msg = enYeniMesaj.message;
          if (msg === "__BOS_TAKVIM__") msg = "";
          const gelenSatirlar = msg.split("\n").map(s => s.trim()).filter(s => s.length > 0);
          
          if (JSON.stringify(gelenSatirlar) !== JSON.stringify(state.yayinlar)) {
            state.yayinlar = gelenSatirlar;
            kaydetYerel();
            renderCalendar();
            updateStats();
            if (bildirimVer) showToast("✓ Buluttan en güncel yayın takvimi eşitlendi!", "success");
          }
        }
      }
    } catch (err) {
      if (bildirimVer && !guncellendi) showToast("Bağlantı hatası: Sunucuya ulaşılamadı.", "error");
    }
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
