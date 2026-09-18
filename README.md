# CryptoSignalScanner

سیستم خودکار **هشدار/سیگنال** بازار کریپتو برای BTCUSDT، ETHUSDT و SOLUSDT.

هر ۵ دقیقه (هم‌زمان با بسته شدن کندل 5m):
1. داده واقعی بازار را از **Toobit** می‌گیرد (5m + تأیید 15m/1h).
2. اندیکاتورهای تکنیکال (EMA/RSI/MACD/Stochastic/ATR/Volume) و Price Action (ساختار بازار، حمایت/مقاومت، breakout/retest) را محاسبه می‌کند.
3. خلاصه اخبار مهم بازار را (با جستجوی وب از طریق Gemini) می‌گیرد.
4. تمام داده خام + محاسبه‌شده را به **Gemini** می‌دهد تا تصمیم نهایی (`LONG` / `SHORT` / `WAIT`) را به‌صورت JSON معتبر برگرداند.
5. اگر سیگنال نسبت به اجرای قبلی تغییر معناداری داشته باشد، **یک پیام واحد** به **Telegram** ارسال می‌کند.

> ⚠️ **این پروژه فقط ابزار تحلیل و هشدار است.**
> هیچ سفارش خرید/فروش، هیچ Position، هیچ Leverage و هیچ اتصال معاملاتی در این کد وجود ندارد
> و هیچ API Key معاملاتی (Trading/Order) هم لازم نیست.

---

## ساختار پروژه

```
CryptoSignalScanner/
├── main.py                  # نقطه ورود + Scheduler
├── config.py                 # تنظیمات (از .env خوانده می‌شود)
├── requirements.txt
├── .env.example
├── .gitignore
├── market/
│   └── toobit.py              # دریافت کندل از API عمومی Toobit
├── indicators/
│   └── technical.py           # EMA/RSI/MACD/Stoch/ATR + Price Action + S/R
├── analysis/
│   ├── signal_engine.py       # امتیازدهی داخلی + Entry/SL/TP + فیلتر Multi-timeframe
│   └── gemini.py               # تصمیم نهایی Gemini + اعتبارسنجی JSON
├── news/
│   └── news_engine.py          # خلاصه اخبار مهم (Gemini + Google Search grounding)
├── telegram/
│   └── bot.py                  # ساخت و ارسال پیام تلگرام
├── storage/
│   └── state.py                 # فیلتر سیگنال تکراری (JSON state)
├── logs/                        # فایل لاگ (app.log)
└── tests/                        # Unit testها
```

---

## پیش‌نیازها

- Windows 10 یا 11
- یک ربات تلگرام (از [@BotFather](https://t.me/BotFather)) و Chat ID شما
- یک Gemini API Key (از [Google AI Studio](https://aistudio.google.com/))

---

## راهنمای گام‌به‌گام اجرا روی Windows

### ۱) نصب Python

اگر Python نصب نیست، از [python.org](https://www.python.org/downloads/) نسخه ۳.۱۰ یا بالاتر را نصب کنید.
هنگام نصب، تیک **Add Python to PATH** را حتماً بزنید.

بررسی نصب، در PowerShell:

```powershell
python --version
```

### ۲) ساخت محیط مجازی (venv)

در PowerShell، داخل پوشه پروژه:

```powershell
cd CryptoSignalScanner
python -m venv venv
.\venv\Scripts\Activate.ps1
```

اگر خطای اجرای اسکریپت گرفتید، یک‌بار این را اجرا کنید و دوباره تلاش کنید:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### ۳) نصب وابستگی‌ها (pip install)

```powershell
pip install -r requirements.txt
```

### ۴) ساخت فایل .env

```powershell
copy .env.example .env
notepad .env
```

### ۵) قرار دادن API Keyها

داخل `.env` مقادیر زیر را پر کنید:

```
GEMINI_API_KEY=کلید_واقعی_شما
TELEGRAM_BOT_TOKEN=توکن_ربات_شما
TELEGRAM_CHAT_ID=آیدی_چت_شما
```

برای گرفتن `TELEGRAM_CHAT_ID` می‌توانید یک پیام به ربات‌تان بفرستید و سپس این URL را در مرورگر باز کنید (به‌جای `<TOKEN>` توکن واقعی را بگذارید):

```
https://api.telegram.org/bot<TOKEN>/getUpdates
```

مقدار `chat.id` در پاسخ JSON همان Chat ID شماست.

### ۶) اجرای تست‌ها (Unit Tests)

```powershell
pytest tests/ -v
```

همه‌ی تست‌ها باید سبز (`PASSED`) شوند.

### ۷) اجرای DRY RUN (بدون ارسال واقعی به تلگرام)

مطمئن شوید در `.env` مقدار زیر تنظیم است:

```
DRY_RUN=true
```

سپس اجرا کنید:

```powershell
python main.py
```

در این حالت، خروجی تحلیل فقط در ترمینال و در `logs/app.log` نمایش داده می‌شود و **هیچ پیامی به تلگرام ارسال نمی‌شود**.
چند چرخه (هر ۵ دقیقه یک‌بار) صبر کنید و خروجی را بررسی کنید.

### ۸) اجرای واقعی

وقتی از رفتار برنامه مطمئن شدید، در `.env`:

```
DRY_RUN=false
```

و دوباره اجرا کنید:

```powershell
python main.py
```

از این پس، فقط زمانی که سیگنال معتبر و تغییر معناداری وجود داشته باشد، یک پیام تلگرام دریافت می‌کنید.

### ۹) اجرای دائمی روی Windows (در پس‌زمینه)

**روش ساده (پنجره باز بماند):**

```powershell
python main.py
```
و پنجره PowerShell را باز نگه دارید (یا آن را minimize کنید).

**روش پیشرفته‌تر (اجرا در پس‌زمینه با NSSM):**

1. [NSSM](https://nssm.cc/download) را دانلود و از حالت zip خارج کنید.
2. در PowerShell (به‌عنوان Administrator):

```powershell
nssm install CryptoSignalScanner
```

3. در پنجره باز شده:
   - **Path**: مسیر کامل `venv\Scripts\python.exe`
   - **Startup directory**: مسیر پوشه پروژه
   - **Arguments**: `main.py`
4. روی **Install service** کلیک کنید.
5. سرویس را استارت کنید:

```powershell
nssm start CryptoSignalScanner
```

با این روش، برنامه حتی بعد از ری‌استارت ویندوز هم به‌صورت خودکار اجرا می‌شود.

---

## تنظیمات مهم (`.env`)

| متغیر | توضیح | پیش‌فرض |
|---|---|---|
| `SYMBOLS` | نمادهای بررسی‌شونده | `BTCUSDT,ETHUSDT,SOLUSDT` |
| `TIMEFRAME` | تایم‌فریم اصلی سیگنال | `5m` |
| `ANALYSIS_INTERVAL` | فاصله زمانی هر اجرا (ثانیه) | `300` |
| `MIN_CONFIDENCE` | حداقل امتیاز داخلی برای در نظر گرفتن سیگنال (فقط فیلتر داخلی) | `70` |
| `MIN_RISK_REWARD` | حداقل نسبت ریسک به ریوارد قابل قبول | `1.5` |
| `DRY_RUN` | اگر `true` باشد، پیامی به تلگرام ارسال نمی‌شود | `true` |

---

## نکات امنیتی

- هیچ API Key در کد هاردکد نشده؛ همه از `.env` خوانده می‌شوند.
- فایل `.env` در `.gitignore` قرار دارد و نباید در گیت‌هاب push شود.
- در فایل لاگ (`logs/app.log`) هیچ‌گاه API Key/Token ذخیره نمی‌شود.
- هیچ اتصال معاملاتی (Order/Trading API Key) در این پروژه استفاده یا لازم نیست.

---

## مشکلات احتمالی و راه‌حل

| مشکل | راه‌حل |
|---|---|
| خطای اتصال به Toobit | اتصال اینترنت و در دسترس بودن `https://api.toobit.com` را بررسی کنید. اگر Toobit endpoint را تغییر داده، فقط کافیست `market/toobit.py` (مقدار `KLINES_PATH`) به‌روزرسانی شود. |
| Gemini پاسخ JSON نامعتبر می‌دهد | سیستم به‌صورت خودکار آن نماد را `WAIT` در نظر می‌گیرد و crash نمی‌کند (به `analysis/gemini.py` نگاه کنید). |
| پیام تلگرام ارسال نمی‌شود | بررسی کنید `DRY_RUN=false` باشد و `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` صحیح باشند؛ خطاها در `logs/app.log` ثبت می‌شوند. |
| سیگنال تکراری هر ۵ دقیقه ارسال می‌شود | فایل `storage/state.json` را بررسی کنید؛ اگر پاک/خراب شده، سیستم دوباره از صفر شروع به یادگیری تغییرات می‌کند (طبیعی است که اولین اجرا بعد از پاک شدن state پیام بفرستد). |

---

## آنلاین‌کردن پروژه (اجرای دائمی بدون روشن بودن PC شما)

دو روش اصلی وجود دارد. **روش GitHub Actions** رایگان است و ساده‌تر راه‌اندازی می‌شود؛
**روش VPS** دقیق‌تر (تایمینگ واقعی هر ۵ دقیقه) است ولی نیاز به یک سرور دارد.

### روش ۱: GitHub Actions (رایگان، پیشنهادی)

پروژه از قبل شامل `run_once.py` و `.github/workflows/scan.yml` است که برای همین کار ساخته شده‌اند.
تفاوت با `main.py`: `main.py` خودش زمان‌بندی می‌کند و برای اجرای دائمی روی یک PC/VPS
همیشه‌روشن است؛ ولی در GitHub Actions هر اجرا جدا و کوتاه‌مدت است، پس `run_once.py`
فقط **یک چرخه** تحلیل را اجرا می‌کند و GitHub خودش هر ۵ دقیقه صدایش می‌زند.

**مراحل:**

1. **ساخت ریپازیتوری روی GitHub**
   یک ریپازیتوری جدید (خصوصی یا عمومی) بسازید، مثلاً `CryptoSignalScanner`.

2. **آپلود کد**
   در PowerShell داخل پوشه پروژه:
   ```powershell
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/USERNAME/CryptoSignalScanner.git
   git push -u origin main
   ```
   (فایل `.env` به‌خاطر `.gitignore` هرگز push نمی‌شود — همان‌طور که باید باشد.)

3. **افزودن Secrets**
   در گیت‌هاب بروید به:
   `Settings → Secrets and variables → Actions → New repository secret`
   و سه مورد زیر را یکی‌یکی اضافه کنید:
   - `GEMINI_API_KEY`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`

4. **فعال‌سازی Actions**
   به تب **Actions** بروید؛ اگر پیامی برای فعال‌سازی Workflow دیدید، تأیید کنید.
   Workflow با نام **Crypto Signal Scan** باید نمایش داده شود.

5. **تست دستی**
   روی workflow کلیک کنید → **Run workflow** (دکمه سمت راست) → یک بار به‌صورت دستی اجرا کنید
   و لاگ آن را بررسی کنید که خطا نداشته باشد.

6. **اجرای خودکار**
   از این پس، GitHub هر ۵ دقیقه خودش این workflow را اجرا می‌کند — بدون نیاز به روشن بودن PC شما.
   هر بار که سیگنال تغییر معناداری داشته باشد، پیام تلگرام دریافت می‌کنید.

   > نکته: GitHub Actions cron را «حداکثر هر ۵ دقیقه» تضمین می‌کند، نه دقیقاً سر هر ۵ دقیقه؛
   > در بارهای بالای سرورهای گیت‌هاب ممکن است چند دقیقه تأخیر پیش بیاید. برای این نوع
   > سیگنال (نه اسکالپینگ لحظه‌ای) این تأخیر معمولاً بی‌اهمیت است.

   > نکته دیگر: workflow بعد از هر اجرا فایل `storage/state.json` را خودش commit می‌کند
   > تا فیلتر سیگنال تکراری بین اجراهای مختلف حفظ شود؛ در نتیجه در تاریخچه ریپازیتوری شما
   > تعداد زیادی commit خودکار کوچک خواهید دید — این طبیعی و بی‌خطر است.

7. **توقف/خاموش‌کردن موقت**
   کافیست در تب Actions روی workflow کلیک کنید و گزینه **Disable workflow** را بزنید.

### روش ۲: VPS همیشه‌روشن (Linux + systemd)

اگر تایمینگ دقیق‌تر هر ۵ دقیقه یا اجرای مداوم بدون وابستگی به GitHub می‌خواهید:

1. یک VPS اوبونتو (مثلاً Hetzner/Contabo/هر ارائه‌دهنده‌ای که در دسترس‌تان است) تهیه کنید.
2. با SSH وارد شوید و Python + git نصب کنید:
   ```bash
   sudo apt update && sudo apt install -y python3 python3-venv python3-pip git
   ```
3. پروژه را کلون و راه‌اندازی کنید:
   ```bash
   git clone https://github.com/USERNAME/CryptoSignalScanner.git
   cd CryptoSignalScanner
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   nano .env   # مقادیر واقعی را وارد کنید، DRY_RUN=false
   ```
4. یک systemd service بسازید تا `main.py` (نسخه‌ی حلقه دائمی، نه `run_once.py`) همیشه در پس‌زمینه اجرا بماند و در صورت ری‌استارت سرور هم خودکار بالا بیاید:
   ```bash
   sudo nano /etc/systemd/system/cryptosignalscanner.service
   ```
   محتوای فایل:
   ```ini
   [Unit]
   Description=CryptoSignalScanner
   After=network.target

   [Service]
   WorkingDirectory=/root/CryptoSignalScanner
   ExecStart=/root/CryptoSignalScanner/venv/bin/python main.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```
5. فعال‌سازی و اجرا:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable cryptosignalscanner
   sudo systemctl start cryptosignalscanner
   ```
6. بررسی وضعیت و لاگ:
   ```bash
   sudo systemctl status cryptosignalscanner
   tail -f logs/app.log
   ```

با این روش نیازی به `run_once.py` یا workflow گیت‌هاب نیست؛ همان `main.py` معمولی که در بخش Windows توضیح داده شد، این‌بار روی سرور به‌جای PC شما همیشه روشن می‌ماند.

---

## سلب مسئولیت

خروجی این سیستم صرفاً یک **ابزار تحلیل تکنیکال خودکار** است و **توصیه مالی قطعی** محسوب نمی‌شود.
تصمیم نهایی هر معامله بر عهده خود کاربر است.
