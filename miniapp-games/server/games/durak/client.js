(() => {
  const SU = ["♠", "♥", "♦", "♣"], RK = { 11: "J", 12: "Q", 13: "K", 14: "A" };
  const st = document.createElement("style");
  st.textContent =
    ".dk{display:flex;flex-direction:column;gap:10px;align-items:center;--w:clamp(46px,12.5vw,64px)}" +
    ".dk-felt{width:100%;background:radial-gradient(ellipse at 50% 40%,#7a1523,#3a0912 85%);border:2px solid #d4a73a;border-radius:20px;padding:12px;box-shadow:inset 0 0 30px rgba(0,0,0,.5)}" +
    ".dk-opps{display:flex;gap:8px;justify-content:center;flex-wrap:wrap}" +
    ".dk-opp{display:flex;flex-direction:column;align-items:center;gap:3px;background:rgba(0,0,0,.3);border-radius:12px;padding:6px 10px;min-width:84px;font-size:13px;color:#f6ecd2;border:2px solid transparent}" +
    ".dk-opp.on{border-color:#ecc96a}.dk-opp.out{opacity:.5}" +
    ".dk-backs{display:flex;min-height:34px}.dk-backs .dk-c{--w:24px;margin-left:-13px}.dk-backs .dk-c:first-child{margin-left:0}" +
    ".dk-mid{display:flex;gap:14px;align-items:center;margin:10px 0;min-height:calc(var(--w)*1.8)}" +
    ".dk-pile{position:relative;flex:none;width:calc(var(--w)*1.6);height:calc(var(--w)*1.4);color:#f6ecd2;font-size:12px}" +
    ".dk-pile .tr{position:absolute;left:0;top:0}.dk-pile .dk-c.back{position:absolute;left:calc(var(--w)*.55);top:0}" +
    ".dk-pile i{position:absolute;right:-4px;bottom:-8px;background:#d4a73a;color:#2b1c00;font-style:normal;font-weight:700;border-radius:999px;padding:1px 7px}" +
    ".dk-trump{width:var(--w);height:calc(var(--w)*1.4);display:flex;align-items:center;justify-content:center;font-size:calc(var(--w)*.7);background:#fffaf0;border-radius:10px;border:2px dashed #d4a73a}" +
    ".dk-table{flex:1;display:flex;flex-wrap:wrap;gap:10px 12px;justify-content:center}" +
    ".dk-pair{position:relative;width:calc(var(--w)*1.3);height:calc(var(--w)*1.7)}" +
    ".dk-pair .dk-c{position:absolute;left:0;top:0}.dk-pair .dk-c.d{left:calc(var(--w)*.3);top:calc(var(--w)*.25);transform:rotate(8deg)}" +
    ".dk-c{width:var(--w);height:calc(var(--w)*1.4);background:#fffaf0;border-radius:calc(var(--w)*.12);position:relative;color:#1a1210;font-weight:800;font-family:Georgia,serif;box-shadow:0 2px 6px rgba(0,0,0,.55);flex:none;user-select:none;transition:transform .12s,opacity .12s}" +
    ".dk-c.r{color:#b3141f}" +
    ".dk-c .tl{position:absolute;top:calc(var(--w)*.05);left:calc(var(--w)*.09);line-height:1;font-size:calc(var(--w)*.27);text-align:center}.dk-c .tl b,.dk-c .tl i{display:block;font-style:normal}" +
    ".dk-c .md{position:absolute;right:calc(var(--w)*.1);bottom:calc(var(--w)*.05);font-size:calc(var(--w)*.5);line-height:1}" +
    ".dk-c.back{background:repeating-linear-gradient(45deg,transparent 0 5px,rgba(236,201,106,.3) 5px 6px),repeating-linear-gradient(-45deg,#5a0f1a 0 5px,#8a1e2e 5px 6px);border:3px solid #fffaf0}" +
    ".dk-c.ok{cursor:pointer;transform:translateY(-10px);outline:2px solid #d4a73a}.dk-c.sel{transform:translateY(-18px);outline:3px solid #fff}" +
    ".dk-c.dim{opacity:.55}.dk-c.tgt{cursor:pointer;outline:3px solid #ecc96a}" +
    ".dk-hand{display:flex;flex-wrap:wrap;gap:6px;justify-content:center;padding-top:16px}" +
    ".dk-acts{display:flex;gap:10px;justify-content:center;flex-wrap:wrap}" +
    ".dk-prev{display:flex;align-items:center;gap:6px;font-size:12px;color:#f6ecd2;opacity:.85;justify-content:center;flex-wrap:wrap}.dk-prev .dk-c{--w:22px}";
  document.head.append(st);

  const el = (t, cls, txt) => { const e = document.createElement(t); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; };
  const red = s => s === 1 || s === 2;
  const key = c => c[0] + "-" + c[1];
  const cardEl = (c, cls) => {
    const e = el("div", "dk-c" + (red(c[0]) ? " r" : "") + (cls ? " " + cls : ""));
    const tl = el("span", "tl"); tl.append(el("b", "", RK[c[1]] || String(c[1])), el("i", "", SU[c[0]] + "\uFE0E"));
    e.append(tl, el("span", "md", SU[c[0]] + "\uFE0E"));
    return e;
  };
  let sel = null, lastView = null;

  GamePlugins.durak = {
    render(root, c) {
      const v = c.view, me = v.me, you = c.seat, nm = i => ((c.seats[i] || {}).name || "?");
      if (v !== lastView) { lastView = v; sel = null; }
      const again = () => GamePlugins.durak.render(root, c);
      const done = !!c.result;
      const clickHand = card => {
        if (done) return;
        const k = key(card), ps = me.canDefend[k];
        if (ps) {
          if (ps.length === 1) { sel = null; return c.send({ defend: card, pair: ps[0] }); }
          sel = sel && key(sel) === k ? null : card; return again();
        }
        if (me.canPlay.some(x => key(x) === k)) { sel = null; c.send({ play: card }); }
      };
      const clickPair = i => {
        if (sel && (me.canDefend[key(sel)] || []).includes(i)) { const s = sel; sel = null; c.send({ defend: s, pair: i }); }
      };

      // ---- raqiblar
      const opps = el("div", "dk-opps");
      for (let i = 0; i < v.n; i++) {
        if (i === you) continue;
        const role = i === v.att ? "⚔️ hujum" : i === v.def ? "🛡 himoya" : "";
        const o = el("div", "dk-opp" + (c.turn === i ? " on" : "") + (v.out.includes(i) ? " out" : ""));
        const backs = el("div", "dk-backs");
        for (let k = 0; k < Math.min(v.counts[i], 8); k++) backs.append(el("div", "dk-c back"));
        o.append(el("b", "", nm(i)), backs, el("span", "", v.out.includes(i) ? "✅ chiqdi" : `${v.counts[i]} ta ${role}`));
        opps.append(o);
      }
      // ---- zaxira va stol
      const pile = el("div", "dk-pile");
      if (v.tc) {
        const tr = el("div", "tr"); tr.append(cardEl(v.tc)); pile.append(tr);
        if (v.deck > 1) { const bk = el("div", "dk-c back"); pile.append(bk, el("i", "", String(v.deck))); }
      } else {
        const t = el("div", "dk-trump", SU[v.trump] + "\uFE0E"); t.style.color = red(v.trump) ? "#b3141f" : "#1a1210"; pile.append(t);
      }
      const table = el("div", "dk-table");
      v.t.forEach((p, i) => {
        const pr = el("div", "dk-pair"); pr.dataset.pair = i;
        const target = sel && !p[1] && (me.canDefend[key(sel)] || []).includes(i);
        pr.append(cardEl(p[0], target ? "tgt" : ""));
        if (p[1]) pr.append(cardEl(p[1], "d"));
        pr.onclick = () => clickPair(i);
        table.append(pr);
      });
      const mid = el("div", "dk-mid"); mid.append(pile, table);
      const felt = el("div", "dk-felt"); felt.append(opps, mid);
      if (v.prev && !v.t.length) {
        const pv = el("div", "dk-prev", `Oldingi raund: ${v.prev.took ? nm(v.prev.def) + " oldi" : "bito"} ·`);
        v.prev.t.forEach(p => { pv.append(cardEl(p[0])); if (p[1]) pv.append(cardEl(p[1])); });
        felt.append(pv);
      }
      // ---- holat matni
      let hint = "";
      if (!done) {
        if (v.phase === "defend") hint = you === v.def ? "Himoyalaning: kartani tanlang yoki «Olaman»" : `${nm(v.def)} himoyalanmoqda` + (me.canPlay.length ? " · siz ham qo'shishingiz mumkin" : "");
        else if (!v.t.length) hint = you === v.att ? "Hujum qiling: karta tashlang" : `${nm(v.att)} hujum qilmoqda`;
        else if (v.phase === "take") hint = you === v.def ? "Siz kartalarni olasiz…" : me.canPass ? "Qo'shing yoki «Tayyor» bosing" : "Kutilmoqda…";
        else hint = me.canPass ? "Qo'shing yoki «Bito» bosing" : "Boshqalar qo'shishi mumkin…";
      }
      // ---- mening qo'lim
      const tr = v.trump, order = x => (x[0] === tr ? 4 : x[0]) * 20 + x[1];
      const hand = el("div", "dk-hand");
      const acting = !done && (me.canPlay.length || Object.keys(me.canDefend).length);
      [...v.hand].sort((a, b) => order(a) - order(b)).forEach(card => {
        const k = key(card), can = me.canDefend[k] || me.canPlay.some(x => key(x) === k);
        const e = cardEl(card, (can ? "ok" : acting ? "dim" : "") + (sel && key(sel) === k ? " sel" : ""));
        e.dataset.card = k;
        e.onclick = () => clickHand(card);
        hand.append(e);
      });
      const acts = el("div", "dk-acts");
      if (me.canTake) { const b = el("button", "btn", "🤲 Olaman"); b.dataset.act = "take"; b.onclick = () => c.send({ take: true }); acts.append(b); }
      if (me.canPass) { const b = el("button", "btn", v.phase === "take" ? "✅ Tayyor" : "✅ Bito"); b.dataset.act = "pass"; b.onclick = () => c.send({ pass: true }); acts.append(b); }
      if (!done) {
        const r = el("button", "btn ghost", "🏳️ Taslim bo'lish");
        r.onclick = () => { if (confirm("Taslim bo'lasizmi? (siz durak bo'lasiz)")) c.send({ resign: true }); };
        acts.append(r);
      }
      const role = you === v.att ? "⚔️ hujum" : you === v.def ? "🛡 himoya" : "";
      const root2 = el("div", "dk");
      root2.append(felt, el("p", "status", hint), acts, hand,
        el("p", "muted", `Siz: ${v.out.includes(you) ? "✅ chiqdingiz" : role} · kozir ${SU[v.trump]}\uFE0E · zaxira ${v.deck} · bito ${v.disc}`));
      root.replaceChildren(root2);
    },
  };
})();
