# Oracle Cloud (bepul) ga joylash — qadamlar

Natija: `https://sizning-nom.duckdns.org` manzilda o'yin serveri 24/7 ishlaydi, GitHub'ga kod yuklasangiz bir buyruq bilan yangilanadi.
(Oracle saytidagi tugma nomlari vaqt o'tishi bilan o'zgarishi mumkin, ma'nosiga qarab toping.)

## 1. Kodni GitHub'ga yuklash (kompyuteringizda)
1. github.com da **Private** repo yarating (masalan `miniapp-games`), README/gitignore qo'shmang.
2. Loyiha papkasida PowerShell:
```
git init
git add .
git commit -m "birinchi versiya"
git branch -M main
git remote add origin https://github.com/SIZNING-LOGIN/miniapp-games.git
git push -u origin main
```
3. GitHub sahifasida **`.env` fayli ko'rinmasligini** tekshiring (token sirli qolishi kerak; `.gitignore` buni o'zi qiladi).

## 2. Telegram bot va ID
- @BotFather → `/newbot` → bot nomi va username → **token** (uzun matn) ni saqlang.
- @userinfobot ga yozing → u sizning **ID** raqamingizni aytadi (admin uchun).

## 3. Oracle akkaunt va server
1. cloud.oracle.com/free dan ro'yxatdan o'ting (bank kartasi so'raladi; to'lov olinmaydi, shaxsni tekshirish uchun). **Home region**ni keyin o'zgartirib bo'lmaydi.
2. Menyu → **Compute → Instances → Create instance**:
   - Image: **Canonical Ubuntu 22.04** (yoki 24.04)
   - Shape: **Ampere A1.Flex**, **1 OCPU / 6 GB** yetarli. "Out of capacity" xatosi chiqsa, bir necha soatdan keyin qayta urinib ko'ring yoki **VM.Standard.E2.1.Micro** (AMD) ni tanlang.
   - Public IP: **Assign** (yoqilgan bo'lsin). **SSH kalit**: "Save private key" ni bosib yuklab oling (yo'qotmang).
3. Server yaratilgach, **Public IP** manzilini yozib oling.
4. Portlarni oching: instance sahifasi → **Subnet** → **Default Security List** → **Add Ingress Rules**: Source CIDR `0.0.0.0/0`, IP Protocol **TCP**, Destination Port **80**. Xuddi shunday **443** uchun ham.

## 4. Bepul domen (DuckDNS)
duckdns.org → Google/GitHub bilan kiring → domen nomini yozing (masalan `shaxmat-oyin`) → **add domain** → "current ip" ga serverning Public IP sini yozib **update ip**. Domeningiz: `shaxmat-oyin.duckdns.org`.

## 5. Serverga ulanish (PowerShell)
```
ssh -i C:\yuklangan\kalit.key ubuntu@SERVER-IP
```
(Birinchi marta "yes" deb javob bering. Kalit fayliga ruxsat xatosi chiqsa, faylni boshqa papkaga ko'chiring.)

## 6. Kodni serverga olish (serverda)
Private repo uchun "deploy key" (faqat o'qish) ishlatamiz:
```
ssh-keygen -t ed25519 -N "" -f ~/.ssh/github_deploy
cat ~/.ssh/github_deploy.pub
```
Chiqqan satrni nusxalab, GitHub repo → **Settings → Deploy keys → Add deploy key** (Allow write access **belgilanmasin**). Keyin:
```
printf "Host github.com\n  IdentityFile ~/.ssh/github_deploy\n  IdentitiesOnly yes\n" >> ~/.ssh/config
sudo mkdir -p /opt/miniapp-games && sudo chown $USER: /opt/miniapp-games
git clone git@github.com:SIZNING-LOGIN/miniapp-games.git /opt/miniapp-games
```

## 7. Sozlash va ishga tushirish (serverda)
```
cd /opt/miniapp-games
cp .env.example .env
nano .env
```
`.env` da faqat **BOT_TOKEN** va **ADMIN_IDS** ni to'ldiring (saqlash: Ctrl+O, Enter, chiqish: Ctrl+X). Qolganini skript o'zi yozadi. Keyin:
```
sudo bash deploy/setup.sh shaxmat-oyin.duckdns.org
```
Skript Python, HTTPS (Caddy), devor, xizmatlar va kunlik zaxirani sozlaydi, oxirida "OK: server ishlayapti" deydi. Xato chiqsa, matnini o'qing: odatda token yoki domen xatosi; tuzatib qayta ishga tushiraverasiz.

## 8. Tekshirish
- Brauzerda `https://shaxmat-oyin.duckdns.org` — "Telegram ichida ochilishi kerak" yozuvi chiqsa, server va HTTPS ishlayapti.
- Telegramda botga `/start` → "🎮 O'ynash" tugmasi (yoki chap pastdagi menyu tugmasi).
- Loglar: `journalctl -u miniapp-api -f` va `journalctl -u miniapp-bot -f`.

## Yangilash (kod o'zgarganda)
Kompyuterda `git add . && git commit -m "..." && git push`, keyin serverda:
```
bash /opt/miniapp-games/deploy/update.sh
```
Bu server va botni qayta ishga tushiradi: **davom etayotgan o'yinlar uziladi**, shuning uchun odamlar kam vaqtda qiling.

## MUHIM ogohlantirishlar
1. **Bo'sh turgan server o'chirilishi mumkin.** Oracle hujjatlariga ko'ra, 7 kun davomida CPU (95-persentil), tarmoq (va A1 da xotira) 20% dan past bo'lsa, bepul server "bo'sh" hisoblanib to'xtatilishi mumkin. Kam foydalanuvchili o'yin serveri aynan shunday ko'rinadi. Foydalanuvchilar yozishicha, akkauntni **Pay As You Go** ga o'tkazish bunga chek qo'yadi (bepul limit ichida pul olinmaydi, lekin kartaga bog'lanadi, shartlarni Oracle saytidan tekshiring). Server to'xtab qolsa, Oracle panelida "Start" bosib qayta yoqasiz.
2. **Zaxira:** reyting bazasi `/opt/miniapp-games/data/games.db`, zaxiralari `data/backup/` da (har kuni 04:00, 14 kun saqlanadi). Bu bir xil diskda, shuning uchun vaqti-vaqti bilan o'zingizga ko'chirib oling: `scp -i kalit.key ubuntu@SERVER-IP:/opt/miniapp-games/data/backup/*.db .`
3. **ZIP orqali o'yin yuklash** (`ALLOW_PLUGIN_UPLOAD=1`) bu tuzilmada ishlamaydi (xizmat faqat `data/` ga yoza oladi), va u xavfli. Yangi o'yinni git orqali qo'shing: papka → `git push` → `update.sh`.
4. `DEV` har doim `0` bo'lsin: `1` da istalgan odam boshqa birovning nomidan kira oladi.
5. Serverni bitta jarayonda ishlating (`--workers` qo'shmang), aks holda raqib topish buziladi.
