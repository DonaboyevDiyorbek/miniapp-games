(() => {
  const GL = { K: "♚", Q: "♛", R: "♜", B: "♝", N: "♞", P: "♟" };
  const st = document.createElement("style");
  st.textContent =
    ".bd{display:grid;grid-template-columns:repeat(8,1fr);width:min(96vw,480px);margin:8px auto;border-radius:8px;overflow:hidden;user-select:none;touch-action:manipulation}" +
    ".sq{aspect-ratio:1;position:relative;display:flex;align-items:center;justify-content:center;font-size:min(10.5vw,52px);line-height:1;cursor:pointer}" +
    ".sq.l{background:#f0d9b5}.sq.d{background:#b58863}" +
    ".sq.last{box-shadow:inset 0 0 0 100px rgba(255,235,59,.35)}.sq.sel{box-shadow:inset 0 0 0 100px rgba(80,200,120,.55)}" +
    ".sq.chk{box-shadow:inset 0 0 0 100px rgba(230,50,50,.6)}" +
    ".sq.mv::after{content:'';position:absolute;width:28%;height:28%;border-radius:50%;background:rgba(0,0,0,.3)}" +
    ".sq.mv.cp::after{width:86%;height:86%;background:none;border:4px solid rgba(0,0,0,.3);box-sizing:border-box}" +
    ".pw{color:#fff;text-shadow:0 0 2px #000,0 0 2px #000,0 1px 3px #000}.pb{color:#111}" +
    ".pro{display:flex;gap:8px;justify-content:center;margin:8px}.pro button{font-size:36px;width:60px;height:60px;border-radius:12px;border:0;background:#8a6a3d}";
  document.head.append(st);

  const el = (t, cls, txt) => { const e = document.createElement(t); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; };
  let sel = null, pend = null, lastView = null;

  GamePlugins.shaxmat = {
    render(root, c) {
      if (c.view !== lastView) { lastView = c.view; sel = null; pend = null; }
      const v = c.view, mv = v.moves || {}, flip = c.seat === 1;
      const again = () => GamePlugins.shaxmat.render(root, c);
      const click = sq => {
        if (!c.myTurn) return;
        if (sel != null && (mv[sel] || []).includes(sq)) {
          const p = v.b[sel];
          if ((p === "P" && sq < 8) || (p === "p" && sq > 55)) { pend = { from: sel, to: sq }; return again(); }
          const m = { from: sel, to: sq }; sel = null; return c.send(m);
        }
        pend = null;
        sel = mv[sq] ? sq : null;
        again();
      };
      const targets = new Set(sel != null ? mv[sel] || [] : []);
      const board = el("div", "bd");
      for (let i = 0; i < 64; i++) {
        const sq = flip ? 63 - i : i, p = v.b[sq];
        let cls = "sq " + (((sq >> 3) + (sq & 7)) % 2 ? "d" : "l");
        if (v.last && (v.last[0] === sq || v.last[1] === sq)) cls += " last";
        if (sq === sel) cls += " sel";
        if (sq === v.check) cls += " chk";
        if (targets.has(sq)) cls += " mv" + (p ? " cp" : "");
        const e = el("div", cls);
        e.dataset.sq = sq;
        if (p) e.append(el("span", p === p.toUpperCase() ? "pw" : "pb", GL[p.toUpperCase()] + "\uFE0E"));
        e.onclick = () => click(sq);
        board.append(e);
      }
      const bits = [el("p", "muted", "Siz: " + (c.seat === 0 ? "oq ⚪" : "qora ⚫"))];
      if (v.check >= 0 && !c.result) bits.push(el("p", "status", "⚠️ Shoh hujum ostida!"));
      bits.push(board);
      if (pend) {
        const row = el("div", "pro");
        for (const k of ["q", "r", "b", "n"]) {
          const b = el("button", "pw", GL[k.toUpperCase()] + "\uFE0E");
          b.dataset.promo = k;
          b.onclick = () => { const m = { ...pend, promo: k }; pend = null; sel = null; c.send(m); };
          row.append(b);
        }
        bits.push(row);
      }
      if (!c.result) {
        const r = el("button", "btn ghost", "🏳️ Taslim bo'lish");
        r.onclick = () => { if (confirm("Taslim bo'lasizmi?")) c.send({ resign: true }); };
        bits.push(r);
      }
      root.replaceChildren(...bits);
    },
  };
})();
