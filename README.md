# 🤖 Telegram AI Kanal Agenti (24/7 Avtopilot)

Ushbu agent Telegramdagi 2 ta manba kanaldan kelgan rasm va videolarni real vaqtda kuzatib, Sun'iy Intellekt (**Google Gemini Vision**) yordamida sifatini tahlil qiladi, qiziqarli va tiniq kontentlarni saralab, mukammal o'zbekcha izoh (caption) bilan sizning asosiy kanalingizga avtomatik joylab boradi.

---

## 🚀 Qisqa imkoniyatlar
* 👁 **Vision AI Tahlili**: Rasm va videolarni tiniqlik, qiziqarlilik va vizual sifatini (1 dan 10 gacha) baholaydi.
* 🛡 **Spam & Reklama filtri**: Noo'rin reklama, kazino va past sifatli postlarni avtomatik chetlab o'tadi.
* ✍️ **Professional Copywriting**: 
  * Agar postda izoh bo'lsa, uni mukammal, jozibador qilib qayta yozadi.
  * Agar izoh bo'lmasa, tasvir mazmunidan kelib chiqib noldan chiroyli post yaratadi.
* ⚡️ **Real-vaqtda ishlash**: Manba kanalda yangi post chiqqan zahoti uni ushlab oladi.
* ☁️ **24/7 Bulutda ishlash**: Kompyuteringiz o'chiq bo'lsa ham serverda to'xtovsiz ishlaydi.

---

## 🛠 Kerakli ma'lumotlar va Sozlash

Loyihada `.env` faylini yarating (`.env.example` dan nusxa olib) va quyidagi 3 ta asosiy narsani kiriting:

### 1. Telegram API (1 daqiqada olinadi)
1. [my.telegram.org](https://my.telegram.org) saytiga kiring.
2. Telefon raqamingiz orqali Telegramga kelgan kod bilan kiring.
3. **API development tools** bo'limiga o'ting.
4. `App title` va `Short name` ga ixtiyoriy nom yozing (masalan: `my_agent`).
5. Ekranda chiqqan **`api_id`** (raqam) va **`api_hash`** (harfli kod) ni nusxalab oling.

### 2. Google Gemini API Kaliti (Bepul)
1. [aistudio.google.com](https://aistudio.google.com) saytiga kiring.
2. **"Get API key"** -> **"Create API key"** tugmasini bosing.
3. Hosil bo'lgan kalitni nusxalab oling.

### 3. Kanallaringiz
* `SOURCE_CHANNELS`: Kuzatmoqchi bo'lgan 2 ta kanalingiz linki yoki usernamelari (masalan: `@kanal1, @kanal2`)
* `TARGET_CHANNEL`: Postlar joylanishi kerak bo'lgan sizning asosiy kanalingiz (masalan: `@mening_kanalim`)
* *Eslatma: O'z akkauntingiz yoki botingiz maqsadli kanalda **Administrator** bo'lishi kerak.*

---

## 💻 Kompyuterda ishga tushirish

1. Bog'liqliklarni o'rnatish:
   ```bash
   pip install -r requirements.txt
   ```

2. Sun'iy intellektni sinab ko'rish:
   ```bash
   python test_ai.py
   ```

3. Asosiy agentni ishga tushirish:
   ```bash
   python agent.py
   ```
   *(Birinchi marta ishga tushganda Telegram raqamingiz va tasdiqlash kodi so'raladi, shundan so'ng sessiya eslab qolinadi).*

---

## 🌐 Kompyuterni o'chirganda ham 24/7 ishlashi (Serverga o'rnatish)

### Variant 1: Bepul Cloud Server (Render / Railway / Koyeb)
1. Ushbu loyihani shaxsiy GitHub akkauntingizga yuklang (repo sifatida).
2. [Render.com](https://render.com) yoki [Railway.app](https://railway.app) ga kiring.
3. "New Background Worker" (yoki Service) yarating va GitHub repongizni ulang.
4. `.env` dagi barcha o'zgaruvchilarni "Environment Variables" bo'limiga kiriting.
5. Ishga tushiring — u endi 24/7 bulutda uzluksiz ishlaydi!

### Variant 2: VPS / Linux Serverda (Docker orqali)
1. Loyihani serverga yuklang.
2. Docker orqali ishga tushiring:
   ```bash
   docker compose up -d --build
   ```
3. Loglarni ko'rish:
   ```bash
   docker compose logs -f
   ```
