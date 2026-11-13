# Telegram Mini App — o'yinlar to'plami (shaxmat, durak)

Hozir: **shaxmat**, **durak** va **reyting (Elo)**. Boshqa o'yinlar plagin sifatida qo'shiladi (pastda).
Rejimlar: tasodifiy raqib (matchmaking), do'st bilan (kod), robot bilan.

## Serverga joylash (bepul)
Oracle Cloud Always Free + GitHub + avtomatik HTTPS: qadamlar `deploy/ORACLE.md` da, bir buyruqli sozlash `deploy/setup.sh`.

## Ishga tushirish (kompyuterda)
```bash
pip install -r requirements.txt
cp .env.example .env        # BOT_TOKEN, WEBAPP_URL, ADMIN_IDS ni to'ldiring
uvicorn server.main:app --host 0.0.0.0 --port 8000
python -m server.bot        # alohida terminalda
```
1. Mini App HTTPS talab qiladi: sinash uchun `cloudflared tunnel --url http://localhost:8000` yoki ngrok, chiqqan manzilni `WEBAPP_URL` ga yozing.
2. Brauzerda tezkor sinash: `.env` da `DEV=1`, keyin `http://localhost:8000/?dev=1&name=Ali` va ikkinchi oynada `?dev=2&name=Vali`.
3. Testlar: `python -m unittest discover -s tests -t .` (Telegram va FastAPI shart emas; brauzer testi uchun Node kerak, bo'lmasa o'tkazib yuboriladi).

## Reyting
- Elo, har bir o'yin uchun alohida. Yangi o'yinchi 1000 dan boshlaydi (birinchi 30 o'yinda K=40, keyin K=20, pastki chegara 100).
- **Tasodifiy raqib** bilan o'yin har doim reytingga hisoblanadi. **Robot** bilan o'yin hisoblanmaydi.
- **Do'st bilan** o'yin har bir o'yinchining faqat har 5-do'st o'yinida hisoblanadi; hisoblagich umumiy (barcha do'stlar bo'yicha, bitta do'st bilan emas) va har bir o'yinchida alohida yuritiladi. Hisoblanmagan o'yin natijasida ekranda "yana N ta o'yindan keyin" yoziladi.
- Chiqib ketish yoki 15 daqiqa yurmaslik mag'lubiyat hisoblanadi.
- Reyting jadvali: eng yaxshi 500 o'yinchi (🏆 Reyting tugmasi). Birinchi 10 tasi har xil rangda, o'yin ekranida ham shu rangda va `#o'rin` bilan ko'rinadi.
- Hali yo'q (keyingi qadam): turnirlar, to'lov, turnir g'oliblari uchun nishon/fon/harbiy unvon.

## Yangi o'yin qo'shish (plagin)
`server/games/<id>/` papkasi, ichida 3 fayl:
- `manifest.json` — `{"id":"<id>","name":"Nomi","icon":"🎲","min_players":2,"max_players":2}` (id papka nomiga teng). `"default_enabled": false` qo'shsangiz, o'yin admin yoqmaguncha ko'rinmaydi.
- `game.py` — `Game` dan meros olgan klass va oxirida `GAME = MeningOyinim()` (`server/games/base.py`; namunalar: `shaxmat/game.py`, `xo/game.py`)
- `client.js` — `GamePlugins["<id>"] = { render(root, ctx) {...} }`; `ctx.view`, `ctx.myTurn`, `ctx.send(yurish)` (namuna: `shaxmat/client.js`)

Server qayta ishga tushganda plagin avtomatik katalogga qo'shiladi, 2 kishilik o'yin uchun reyting va reyting jadvali o'z-o'zidan ishlaydi. Admin (Mini App → ⚙️ Admin panel) o'yinni yoqish/o'chirish, tartibini va nomini o'zgartira oladi. `xo` namuna sifatida turibdi, sukut bo'yicha o'chiq.

**ZIP orqali yuklash** (`ALLOW_PLUGIN_UPLOAD=1`): admin panelda shu 3 fayllik ZIP yuklanadi. Diqqat: `game.py` serverda to'liq huquq bilan ishlaydi, shuning uchun bu yoqilsa admin akkaunti buzilishi serverni to'liq egallashga teng. Faqat ishonchli adminlar bo'lsa yoqing, aks holda o'chirib qo'ying va papkani git orqali qo'shing.

## Shaxmat haqida
Qoidalar: rokirovka, en passant, piyodani almashtirish, mat/pat, 50 yurish, 3 marta takrorlanish, material yetarli emasligi; taslim bo'lish tugmasi. Robot oddiy darajada (2 yurish oldinga). Qoidalar taniqli perft sonlari bilan tekshirilgan. Durang taklif qilish va soat (vaqt nazorati) hali yo'q.

## Durak haqida
- 36 karta, **2–6 o'yinchi** (do'stlar xonasida host «Boshlash»ni bosadi; tasodifiy raqib va robot bilan 2 kishilik). Podkidnoy: hujumchidan tashqari hamma o'yinchi daraja mos kelsa karta qo'sha oladi; himoyalanuvchi «Olaman» desa, qo'shib tashlash davom etadi.
- Birinchi hujumchi: eng kichik kozir egasi. Hujumchi birinchi bo'lib tortadi, himoyalanuvchi oxirida. Oxirgi qolgan o'yinchi — durak; hamma birga tugatsa durrang.
- Reyting faqat **2 kishilik** o'yinda hisoblanadi (3+ kishilik o'yin reytingga ta'sir qilmaydi). Ko'p o'yinchili o'yinda kimdir chiqib ketsa yoki taslim bo'lsa, o'yin hamma uchun tugaydi (taslim bo'lgan durak hisoblanadi).
- Yo'q: perevodnoy (o'tkazma durak), kartalarni sanash/chat. Robot oddiy darajada.
- Hozir qo'lda kartalar rangi/qiymati bo'yicha saralanadi (kozir oxirida).

## Cheklovlar
- Xonalar xotirada saqlanadi: server qayta ishga tushsa, davom etayotgan o'yinlar yo'qoladi (reyting va natijalar bazada saqlanadi).
- Uzilgan o'yinchi qayta kirsa o'yin davom etadi; 15 daqiqa yurilmasa vaqt tugashi bilan yakunlanadi.
