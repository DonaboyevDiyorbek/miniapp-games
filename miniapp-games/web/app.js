"use strict";
const tg = window.Telegram && Telegram.WebApp;
if (tg) { tg.ready(); tg.expand(); }
const Q = new URLSearchParams(location.search);
const INIT = (tg && tg.initData) || (Q.get("dev") ? `dev:${Q.get("dev")}:${Q.get("name") || "Dev" + Q.get("dev")}` : "");
const root = document.getElementById("app");
window.GamePlugins = {};
const S = { games: [], me: null, room: null, queued: null, screen: "home", pick: null, toast: "", admin: null };
let ws;

const h = (t, a, ...k) => {
  const e = document.createElement(t);
  for (const [x, v] of Object.entries(a || {})) {
    if (x === "onclick" || x === "onchange") e[x] = v;
    else if (x === "class") e.className = v;
    else e.setAttribute(x, v);
  }
  e.append(...k.flat(Infinity).filter(c => c != null && c !== false));
  return e;
};
const api = async (p, o = {}) => {
  const r = await fetch(p, { ...o, headers: { ...(o.headers || {}), "X-Init-Data": INIT } });
  if (!r.ok) { let m = r.statusText; try { m = (await r.json()).detail || m; } catch (e) {} throw new Error(m); }
  return r.json();
};
const send = m => ws && ws.readyState === 1 && ws.send(JSON.stringify(m));
const toast = m => { S.toast = m; render(); setTimeout(() => { if (S.toast === m) { S.toast = ""; render(); } }, 2500); };
const plugin = id => window.GamePlugins[id] ? Promise.resolve() : new Promise((ok, no) => {
  const s = h("script", { src: `/plugins/${id}/client.js` }); s.onload = ok; s.onerror = no; document.head.append(s);
});
const refreshGames = async () => { S.games = await api("/api/games"); };

function connect() {
  ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws?init=${encodeURIComponent(INIT)}`);
  ws.onmessage = async e => {
    const m = JSON.parse(e.data);
    if (m.t === "idle") {
      S.room = null; S.queued = null; S.screen = "home"; if (m.msg) S.toast = m.msg;
      api("/api/me").then(x => { S.me = x; render(); }).catch(() => {});
    }
    else if (m.t === "queued") S.queued = m.game;
    else if (m.t === "err") return toast(m.msg);
    else if (m.t === "room") { S.queued = null; S.room = m; await plugin(m.game).catch(() => toast("O'yin yuklanmadi")); }
    render();
  };
  ws.onclose = () => setTimeout(connect, 2000);
}

const TOP = ["#f2c230", "#c9d1d9", "#cd8b4a", "#ef6f6c", "#e9953f", "#58b368", "#38a3a5", "#6c8cff", "#9b7be0", "#d65db1"];
async function openBoard(gid) {
  try { S.board = { game: gid, ...(await api("/api/leaderboard?game=" + encodeURIComponent(gid))) }; S.screen = "board"; render(); }
  catch (e) { toast(e.message); }
}
function boardView() {
  const B = S.board, me = B.me;
  return [
    h("button", { class: "back", onclick: () => { S.screen = "home"; render(); } }, "← Orqaga"),
    h("h1", {}, "🏆 Reyting"),
    S.games.length > 1 ? h("div", { class: "row" }, S.games.map(g => h("button", { class: "btn" + (g.id === B.game ? "" : " ghost"), onclick: () => openBoard(g.id) }, g.icon + " " + g.title))) : null,
    h("p", { class: "status" }, me.rank ? `Sizning o'rningiz: #${me.rank} · ⭐ ${me.rating}` : `⭐ ${me.rating} · reytingli o'yin o'ynang`),
    B.top.length ? h("div", { class: "lb" }, B.top.map(p => h("div", { class: "lbrow" + (S.me && p.id === S.me.id ? " mine" : ""),
      ...(p.rank <= 10 ? { style: `background:${TOP[p.rank - 1]};color:#1b1300` } : {}) },
      h("b", {}, "#" + p.rank), h("span", { class: "nm" }, p.name), h("small", {}, `${p.wins}-${p.draws}-${p.losses}`), h("b", {}, "⭐ " + p.rating))))
      : h("p", { class: "muted" }, "Hali hech kim reytingli o'yin o'ynamagan"),
  ];
}

const home = () => [
  h("h1", {}, "🎮 O'yinlar"),
  h("div", { class: "grid" }, S.games.map(g => h("button", { class: "card", onclick: () => { S.pick = g; S.screen = "mode"; render(); } },
    h("span", { class: "ic" }, g.icon), h("b", {}, g.title), h("small", {}, `⭐ ${((S.me && S.me.ratings && S.me.ratings[g.id]) || { rating: 1000 }).rating}` +
      (S.me && S.me.ratings && S.me.ratings[g.id] && S.me.ratings[g.id].rank ? ` · #${S.me.ratings[g.id].rank}` : ""))))),
  S.games.length ? h("button", { class: "btn ghost", onclick: () => openBoard(S.games[0].id) }, "🏆 Reyting") : h("p", { class: "muted" }, "Hozircha o'yin yo'q"),
  S.me && S.me.admin ? h("button", { class: "btn ghost", onclick: openAdmin }, "⚙️ Admin panel") : null,
];

function mode() {
  const g = S.pick, code = h("input", { placeholder: "KOD", maxlength: "5", autocapitalize: "characters" });
  return [
    h("button", { class: "back", onclick: () => { S.screen = "home"; render(); } }, "← Orqaga"),
    h("h1", {}, g.icon + " " + g.title),
    S.queued === g.id
      ? [h("p", { class: "muted" }, "Raqib qidirilmoqda…"), h("button", { class: "btn ghost", onclick: () => { send({ t: "cancel" }); S.queued = null; render(); } }, "Bekor qilish")]
      : [h("button", { class: "btn", onclick: () => send({ t: "queue", game: g.id }) }, "🎲 Tasodifiy raqib"),
         h("button", { class: "btn", onclick: () => send({ t: "create", game: g.id }) }, "👥 Do'st bilan (kod)"),
         g.bot ? h("button", { class: "btn", onclick: () => send({ t: "bot", game: g.id }) }, "🤖 Robot bilan") : null,
         h("div", { class: "row" }, code, h("button", { class: "btn", onclick: () => send({ t: "join", code: code.value }) }, "Kodga qo'shilish"))],
  ];
}

const status = r => {
  let t;
  if (r.status === "over") {
    const w = r.result.winner, L = r.result.loser;
    if (L !== undefined) {   // durak: ko'p o'yinchida faqat yutqazuvchi (durak) aniq
      t = L === r.you ? "😔 Siz durak bo'ldingiz" : L == null ? "🤝 Durrang" : "🏆 Siz yutdingiz! Durak: " + ((r.seats[L] || {}).name || "");
    } else t = w === r.you ? "🏆 Siz yutdingiz!" : w == null ? "🤝 Durrang" : "😔 Siz yutqazdingiz";
    const RS = { leave: "o'yinchi chiqib ketdi", timeout: "vaqt tugadi", mate: "mat", stalemate: "pat", resign: "taslim bo'ldi",
      material: "material yetarli emas", fifty: "50 yurish qoidasi", repetition: "3 marta takrorlandi", no_moves: "yurish qolmadi" };
    if (RS[r.result.reason]) t += ` (${RS[r.result.reason]})`;
  } else t = r.turn === r.you ? "✅ Sizning yurishingiz" : "⏳ " + ((r.seats[r.turn] || {}).name || "") + " yuradi";
  return [h("p", { class: "status" }, t), r.status === "over" ? ratingLine(r) : null];
};
const ratingLine = r => {
  const x = r.result.rating && r.result.rating[r.you];
  if (!x) return h("p", { class: "muted" }, r.mode === "bot" ? "Robot bilan o'yin reytingga ta'sir qilmaydi" : "");
  if (!x.counted) return h("p", { class: "muted" }, `Do'st bilan o'yin: reytingga yana ${x.next} ta o'yindan keyin hisoblanadi`);
  const d = x.after - x.before;
  return h("p", { class: "muted" }, `⭐ ${x.before} → ${x.after} (${d >= 0 ? "+" : ""}${d})`);
};

function roomView() {
  const r = S.room, P = window.GamePlugins[r.game], g = S.games.find(x => x.id === r.game) || { title: r.game, icon: "🎮" };
  const head = h("div", { class: "head" }, h("b", {}, g.icon + " " + g.title), h("button", { class: "back", onclick: () => send({ t: "leave" }) }, "🚪 Chiqish"));
  const seats = h("div", { class: "seats" }, r.seats.map((p, i) => {
    const top = p.rank && p.rank <= 10;
    return h("span", { class: "seat" + (r.turn === i ? " on" : "") + (i === r.you ? " me" : "") + (top ? " top" : ""),
      ...(top ? { style: `background:${TOP[p.rank - 1]};color:#1b1300` } : {}) },
      (top ? `#${p.rank} ` : "") + p.name + (p.rating ? ` · ⭐${p.rating}` : ""));
  }));
  if (r.status === "waiting") {
    return [head, seats, h("div", { class: "wait" }, h("p", {}, "Do'stingizga kodni yuboring:"), h("div", { class: "code" }, r.code),
      h("p", { class: "muted" }, `${r.seats.length}/${r.max} o'yinchi`),
      r.host === (S.me && S.me.id) && r.seats.length >= r.min ? h("button", { class: "btn", onclick: () => send({ t: "start" }) }, "▶️ Boshlash") : null)];
  }
  const box = h("div", { class: "play" });
  try {
    P.render(box, { view: r.view, seat: r.you, turn: r.turn, seats: r.seats, result: r.result,
      myTurn: r.status === "playing" && r.turn === r.you, send: mv => send({ t: "move", move: mv }) });
  } catch (e) { box.textContent = "Xato: " + e.message; }
  return [head, seats, status(r), box];
}

async function openAdmin() { try { S.admin = await api("/api/admin/games"); S.screen = "admin"; render(); } catch (e) { toast(e.message); } }
const upd = async (id, b) => {
  try {
    await api("/api/admin/games/" + id, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(b) });
    await refreshGames(); S.admin = await api("/api/admin/games"); render();
  } catch (e) { toast(e.message); }
};
const swap = async (a, b) => { await upd(a.id, { sort: b.sort }); await upd(b.id, { sort: a.sort }); };
async function upload(e) {
  const f = e.target.files[0]; if (!f) return;
  const fd = new FormData(); fd.append("file", f);
  try { await api("/api/admin/plugins", { method: "POST", body: fd }); await refreshGames(); S.admin = await api("/api/admin/games"); toast("✅ Qo'shildi"); }
  catch (err) { toast(err.message); }
}
function adminView() {
  const L = S.admin.games;
  return [
    h("button", { class: "back", onclick: () => { S.screen = "home"; render(); } }, "← Orqaga"),
    h("h1", {}, "⚙️ Admin"),
    L.map((g, i) => h("div", { class: "arow" },
      h("span", {}, g.icon + " " + g.title + (g.loaded ? "" : " ⚠️ (kod yo'q)")),
      h("label", {}, h("input", { type: "checkbox", ...(g.enabled ? { checked: "" } : {}), onchange: e => upd(g.id, { enabled: e.target.checked }) }), " yoqilgan"),
      h("button", { class: "mini", onclick: () => i && swap(L[i - 1], g) }, "▲"),
      h("button", { class: "mini", onclick: () => i < L.length - 1 && swap(g, L[i + 1]) }, "▼"),
      h("button", { class: "mini", onclick: () => { const t = prompt("Yangi nom", g.title); if (t) upd(g.id, { title: t }); } }, "✏️"))),
    S.admin.can_upload
      ? h("div", {}, h("p", {}, "Yangi o'yin (ZIP: manifest.json, game.py, client.js):"), h("input", { type: "file", accept: ".zip", onchange: upload }))
      : h("p", { class: "muted" }, "Yangi o'yin qo'shish: server/games/ ga papka qo'shing (README)."),
  ];
}

function render() {
  const body = S.room ? roomView() : S.screen === "admin" ? adminView() : S.screen === "board" ? boardView() : S.screen === "mode" ? mode() : home();
  root.replaceChildren(...[body].flat(Infinity).filter(Boolean), ...(S.toast ? [h("div", { class: "toast" }, S.toast)] : []));
}

(async () => {
  if (!INIT) { root.append(h("p", { class: "muted" }, "Bu sahifa Telegram ichida ochilishi kerak.")); return; }
  try { [S.games, S.me] = await Promise.all([api("/api/games"), api("/api/me")]); }
  catch (e) { root.append(h("p", { class: "muted" }, "Server xatosi: " + e.message)); return; }
  connect(); render();
})();
