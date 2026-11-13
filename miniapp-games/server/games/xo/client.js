(() => {
  const st = document.createElement("style");
  st.textContent = ".xo{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;width:min(86vw,340px);margin:12px auto}" +
    ".xo button{aspect-ratio:1;font-size:min(15vw,60px);border-radius:14px;border:0;background:var(--card);color:var(--fg)}" +
    ".xo button.w{outline:3px solid var(--accent)}";
  document.head.append(st);
  GamePlugins.xo = {
    render(root, c) {
      const line = (c.result && c.result.line) || [];
      const grid = document.createElement("div");
      grid.className = "xo";
      c.view.b.forEach((v, i) => {
        const b = document.createElement("button");
        b.textContent = v === null ? "" : v === 0 ? "❌" : "⭕";
        if (line.includes(i)) b.className = "w";
        b.disabled = v !== null || !c.myTurn;
        b.onclick = () => c.send({ cell: i });
        grid.append(b);
      });
      const you = document.createElement("p");
      you.className = "muted";
      you.textContent = "Siz: " + (c.seat === 0 ? "❌" : "⭕");
      root.replaceChildren(you, grid);
    },
  };
})();
