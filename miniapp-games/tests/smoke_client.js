// Brauzersiz tekshiruv: DOM o'rniga oddiy imitatsiya bilan shaxmat plagini va asosiy ilovani ishga tushiradi.
const fs = require("fs"), vm = require("vm"), assert = require("assert");
const fx = JSON.parse(fs.readFileSync(__dirname + "/fixtures.json", "utf8"));
class El {
  constructor(t) { this.tag = t; this.children = []; this.className = ""; this.dataset = {}; this.attrs = {}; this.style = {}; this.textContent = ""; }
  append(...k) { this.children.push(...k); }
  replaceChildren(...k) { this.children = k; }
  setAttribute(a, v) { this.attrs[a] = v; }
}
const text = e => typeof e === "string" ? e : (e.textContent || "") + e.children.map(text).join("");
const find = (root, pred, out = []) => { if (pred(root)) out.push(root); for (const c of root.children) if (typeof c !== "string") find(c, pred, out); return out; };
const appRoot = new El("div");
global.window = global;
global.document = { createElement: t => new El(t), head: new El("head"), getElementById: () => appRoot };
global.GamePlugins = {};
global.confirm = () => true;
setTimeout(() => { console.error("TIMEOUT: test qotib qoldi"); process.exit(1); }, 8000);
const tick = (ms = 15) => new Promise(r => setTimeout(r, ms));

(async () => {
  // ---------- shaxmat plagini
  vm.runInThisContext(fs.readFileSync("server/games/shaxmat/client.js", "utf8"));
  const P = GamePlugins.shaxmat, sent = [], root = new El("div");
  const ctx = (view, seat, myTurn) => ({ view, seat, turn: view.turn, seats: [{}, {}], result: null, myTurn, send: m => sent.push(m) });
  const sqEl = n => find(root, e => e.dataset.sq == n)[0];

  P.render(root, ctx(fx.start0, 0, true));
  assert.equal(find(root, e => e.dataset.sq !== undefined).length, 64);
  sqEl(52).onclick();                                                    // e2 ni tanlash
  assert.equal(find(root, e => /\bmv\b/.test(e.className)).length, 2);   // e3, e4
  sqEl(36).onclick();                                                    // e4
  assert.deepEqual(sent.pop(), { from: 52, to: 36 });

  P.render(root, ctx(fx.start1, 1, false));                              // qora: taxta aylantirilgan, navbat emas
  assert.equal(find(root, e => e.dataset.sq !== undefined)[0].dataset.sq, "63");
  sqEl(12).onclick();
  assert.equal(find(root, e => /\bmv\b/.test(e.className)).length, 0);
  assert.equal(sent.length, 0);

  P.render(root, ctx(fx.promo, 0, true));                                // piyoda almashtirish
  sqEl(8).onclick(); sqEl(0).onclick();
  assert.equal(sent.length, 0);
  const promo = find(root, e => e.dataset.promo);
  assert.equal(promo.length, 4);
  promo.find(e => e.dataset.promo === "n").onclick();
  assert.deepEqual(sent.pop(), { from: 8, to: 0, promo: "n" });
  console.log("shaxmat client OK");

  // ---------- durak plagini
  vm.runInThisContext(fs.readFileSync("server/games/durak/client.js", "utf8"));
  const D = GamePlugins.durak, dsent = [], droot = new El("div"), seats2 = [{ name: "Ali" }, { name: "Vali" }];
  const dctx = (view, seat, turn) => ({ view, seat, turn, seats: seats2, result: null, myTurn: turn === seat, send: m => dsent.push(m) });
  const byCard = k => find(droot, e => e.dataset.card === k)[0];
  const byAct = k => find(droot, e => e.dataset.act === k)[0];

  D.render(droot, dctx(fx.dk_att, 0, 0));                                  // hujumchi: karta tashlaydi
  assert.equal(find(droot, e => e.dataset.card !== undefined).length, 3);
  assert.ok(/ok/.test(byCard("1-7").className) && !byAct("take") && !byAct("pass"));
  byCard("2-9").onclick();
  assert.deepEqual(dsent.pop(), { play: [2, 9] });

  D.render(droot, dctx(fx.dk_def, 1, 1));                                  // himoyalanuvchi
  assert.ok(byAct("take") && !byAct("pass"));
  assert.ok(/dim/.test(byCard("3-6").className));                          // urmaydigan karta xiralashgan
  byCard("3-6").onclick();
  assert.equal(dsent.length, 0);
  byCard("1-8").onclick();                                                 // faqat bitta nishon: darhol yuboriladi
  assert.deepEqual(dsent.pop(), { defend: [1, 8], pair: 0 });
  byCard("0-9").onclick();                                                 // kozir ikkala kartani uradi: nishon tanlanadi
  assert.equal(dsent.length, 0);
  assert.equal(find(droot, e => /tgt/.test(e.className)).length, 2);
  find(droot, e => e.dataset.pair == 1)[0].onclick();
  assert.deepEqual(dsent.pop(), { defend: [0, 9], pair: 1 });
  byAct("take").onclick();
  assert.deepEqual(dsent.pop(), { take: true });

  D.render(droot, dctx(fx.dk_pass, 0, 0));                                 // hamma urilgan: qo'shish yoki bito
  assert.ok(/Bito/.test(text(byAct("pass"))));
  byAct("pass").onclick();
  assert.deepEqual(dsent.pop(), { pass: true });
  byCard("2-7").onclick();                                                 // daraja mos: qo'shib tashlaydi
  assert.deepEqual(dsent.pop(), { play: [2, 7] });
  assert.ok(/dim/.test(byCard("3-12").className));
  console.log("durak client OK");

  // ---------- asosiy ilova
  const json = {
    "/api/games": [{ id: "shaxmat", title: "Shaxmat", icon: "♟️", min: 2, max: 2, bot: true }],
    "/api/me": { id: 1, name: "Ali", admin: false, ratings: { shaxmat: { rating: 1042, rank: 7 } } },
    "/api/leaderboard?game=shaxmat": { me: { rating: 1042, rank: 7 }, top: [
      { rank: 1, id: 5, name: "Zoir", rating: 1500, played: 10, wins: 8, draws: 1, losses: 1 },
      { rank: 11, id: 1, name: "Ali", rating: 1042, played: 3, wins: 2, draws: 0, losses: 1 }] },
  };
  global.fetch = async u => ({ ok: u in json, statusText: "yo'q", json: async () => json[u] });
  global.location = { search: "?dev=1&name=Ali", protocol: "http:", host: "x" };
  let ws;
  global.WebSocket = class { constructor() { ws = this; this.sent = []; this.readyState = 1; } send(m) { this.sent.push(JSON.parse(m)); } };
  vm.runInThisContext(fs.readFileSync("web/app.js", "utf8"));
  vm.runInThisContext(fs.readFileSync("server/games/shaxmat/client.js", "utf8"));   // app.js GamePlugins ni yangilaydi; brauzerda <script> qayta yuklaydi
  await tick();
  assert.ok(/Shaxmat/.test(text(appRoot)) && /⭐ 1042 · #7/.test(text(appRoot)), text(appRoot));
  const btn = label => find(appRoot, e => e.tag === "button" && text(e).includes(label))[0];

  btn("Reyting").onclick(); await tick();
  assert.ok(/Sizning o'rningiz: #7 · ⭐ 1042/.test(text(appRoot)) && /Zoir/.test(text(appRoot)));
  assert.ok(/background:#f2c230/.test(find(appRoot, e => /lbrow/.test(e.className))[0].attrs.style));   // 1-o'rin: oltin
  assert.ok(!find(appRoot, e => /lbrow/.test(e.className))[1].attrs.style);                              // 11-o'rin: oddiy
  btn("Orqaga").onclick();
  btn("Shaxmat").onclick();
  btn("Tasodifiy raqib").onclick();
  assert.deepEqual(ws.sent.pop(), { t: "queue", game: "shaxmat" });

  const room = (status, result, extra = {}) => ({ t: "room", id: "r1", game: "shaxmat", status, mode: "queue", you: 0, host: null,
    min: 2, max: 2, code: null, turn: result ? null : 0, result, view: fx.start0,
    seats: [{ name: "Ali", bot: false, rating: 1042, rank: 7 }, { name: "Zoir", bot: false, rating: 1500, rank: 1 }], ...extra });
  await ws.onmessage({ data: JSON.stringify(room("playing", null)) });
  const t1 = text(appRoot);
  assert.ok(/#1 Zoir · ⭐1500/.test(t1) && /Ali · ⭐1042/.test(t1) && /Sizning yurishingiz/.test(t1), t1);
  const chip = n => find(appRoot, e => /(^| )seat( |$)/.test(e.className) && text(e).includes(n))[0];
  assert.ok(chip("Zoir").attrs.style.includes("#f2c230"));          // 1-o'rin: oltin
  assert.ok(chip("Ali").attrs.style.includes("#38a3a5"));           // 7-o'rin: o'z rangi
  assert.equal(find(appRoot, e => e.dataset.sq !== undefined).length, 64);

  const done = (rating, extra) => room("over", { winner: 0, reason: "mate", rating }, extra);
  await ws.onmessage({ data: JSON.stringify(done([{ before: 1042, after: 1058, counted: true, next: 0 }, null])) });
  assert.ok(/mat/.test(text(appRoot)) && /⭐ 1042 → 1058 \(\+16\)/.test(text(appRoot)), text(appRoot));
  await ws.onmessage({ data: JSON.stringify(done([{ before: 1042, after: 1042, counted: false, next: 3 }, null], { mode: "friend" })) });
  assert.ok(/yana 3 ta o'yindan keyin/.test(text(appRoot)));
  await ws.onmessage({ data: JSON.stringify(done(null, { mode: "bot" })) });
  assert.ok(/Robot bilan o'yin reytingga ta'sir qilmaydi/.test(text(appRoot)));
  vm.runInThisContext(fs.readFileSync("server/games/durak/client.js", "utf8"));
  const dk = loser => ({ t: "room", id: "r2", game: "durak", status: "over", mode: "friend", you: 0, host: 1, min: 2, max: 6, code: "ABCDE", turn: null,
    view: fx.dk_att, seats: [{ name: "Ali", bot: false }, { name: "Zoir", bot: false }, { name: "Sami", bot: false }],
    result: { loser, winner: null, reason: "durak" } });
  await ws.onmessage({ data: JSON.stringify(dk(0)) });
  assert.ok(/Siz durak bo'ldingiz/.test(text(appRoot)), text(appRoot));
  await ws.onmessage({ data: JSON.stringify(dk(1)) });
  assert.ok(/Siz yutdingiz! Durak: Zoir/.test(text(appRoot)), text(appRoot));
  console.log("app OK");
  process.exit(0);
})().catch(e => { console.error(e); process.exit(1); });
