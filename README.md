# ⚡ AI Harness - Autonomous Software Engineering Agent

یک سیستم کامل و خودکار (Autonomous Agent Harness) بر پایه پایتون، الهام گرفته شده از ابزارهایی مانند **Google Antigravity** و **Claude Code**.
این ابزار به شما اجازه می‌دهد تنها با دادن یک پرامپت کلی، یک پروژه نرم‌افزاری را در یک پوشه مشخص به صورت صفر تا صد بسازید، نیازمندی‌ها و پکیج‌ها را نصب کند، کدهای لازم را بنویسد، تست‌های خودکار بنویسد و اجرا کند، خطاها را خودش برطرف کند و در نهایت پروژه آماده را تحویل دهد.

---

## 🚀 ویژگی‌های کلیدی

1. **اتصال منعطف به DeepSeek**:
   - پشتیبانی از ۳ متغیر اصلی:
     - `DEEPSEEK_API_KEY`
     - `DEEPSEEK_URL` (مثلاً `https://api.deepseek.com` یا سرور پروکسی/لوکال)
     - `MODEL_NAME` (مانند `deepseek-chat` یا `deepseek-reasoner`)
2. **مدیریت کانتکست و فشرده‌سازی خودکار (Context Management & Compaction)**:
   - تخمین توکن‌ها و جلوگیری از سرریز شدن سقف کانتکست مدل (Context Overflow).
   - فشرده‌سازی خروجی‌های طولانی دستورات و ابزارها در مراحل قبلی (Compacting old tool outputs) و حفظ تاریخچه حیاتی.
3. **حافظه پایدار (Persistent Memory & Scratchpad)**:
   - نگهداری برنامه کاری، چک‌لیست مراحل، و وضعیت پروژه در فایل `.agent_memory/memory.json` در مسیر پروژه.
4. **جعبه ابزار کامل مهندسی نرم‌افزار**:
   - `write_file`: ایجاد فایل‌ها با ساخت خودکار پوشه‌های والد.
   - `read_file`: خواندن خطوط مشخص همراه با شماره خط.
   - `replace_in_file`: ویرایش دقیق و جراحی خطوط کد (بدون نیاز به بازنویسی کل فایل).
   - `execute_command`: اجرای دستورات در ترمینال (نصب پکیج‌ها، تست‌ها، لینتر، بیلد و...).
   - `list_directory` و `get_project_tree`: بررسی ساختار پروژه.
   - `search_in_files`: جستجوی Regex و متنی در کل پروژه.
   - `update_plan` و `view_plan`: مدیریت نقشه راه و وضعیت پیشرفت.
   - `finish_task`: اتمام کار و گزارش جامع پروژه.
5. **پشتیبانی کامل از متن فارسی در ترمینال (Persian BiDi & Reshaping)**:
   - حل مشکل برعکس نشان دادن کلمات فارسی و حروف ناپیوسته در ترمینال ویندوز/لینوکس.
   - چسباندن صحیح حروف فارسی و مرتب‌سازی راست‌به‌چپ با حفظ ساختار بلوک‌های کد انگلیسی و مارک‌داون.
6. **حلقه تست و خودترمیمی خودکار (Autonomous Self-Correction)**:
   - ایجنت ملزم است برای کدهایی که می‌نویسد تست اجرا کند؛ اگر تست یا کامندی با خطا مواجه شود، خطا را تحلیل کرده و کد را اصلاح می‌کند تا تست‌ها پاس شوند.
7. **محیط خط فرمان (CLI) حرفه‌ای و زیبا بدون UI اضافه**:
   - بدون نیاز به سرور وب یا رابط کاربری گرافیکی، مستقیماً در ترمینال با خروجی‌های ساختاریافته (Rich Panels, Step Counters, Tool Logs).
   - قابلیت مکالمه تعاملی (REPL) برای درخواست کارهای بعدی یا تغییرات روی پروژه.

---

## 📦 پیش‌نیازها و نصب

پکیج‌های مورد نیاز:
```bash
pip install -r requirements.txt
```

محتوای `requirements.txt`:
- `openai>=1.40.0`
- `python-dotenv>=1.0.0`
- `rich>=13.0.0`
- `pydantic>=2.0.0`
- `arabic-reshaper>=3.0.0`
- `python-bidi>=0.4.2`

---

## ⚙ پیکربندی (تنظیم ۳ مقدار درخواستی)

شما می‌توانید مقادیر را به سه روش تنظیم کنید:

### روش اول: فایل `.env` (توصیه شده)
یک فایل به نام `.env` در کنار `main.py` بسازید (می‌توانید از روی `.env.example` کپی کنید):
```env
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DEEPSEEK_URL=https://api.deepseek.com
MODEL_NAME=deepseek-chat
```

### روش دوم: آرگومان‌های خط فرمان (CLI Flags)
```bash
python main.py --api-key "sk-xxxx" --url "https://api.deepseek.com" --model "deepseek-chat" -w ./my_project -p "Build a FastAPI app"
```

### روش سوم: جادوگر تعاملی ترمینال (Interactive Wizard)
اگر هیچ مقداری وارد نکنید، به سادگی دستور زیر را اجرا کنید:
```bash
python main.py
```
برنامه در همان ابتدا مقادیر لازم را از شما می‌پرسد.

---

## 💻 نحوه استفاده

### ۱. اجرای مستقیم تک‌دستوری (One-shot Mode)

ساخت یک پروژه بک‌اند با جنگو یا فست‌اِی‌پی‌آی در مسیر مشخص:
```bash
python main.py -w ./my_fastapi_app -p "Create a full FastAPI REST API for task management with SQLite, Pydantic models, CRUD routes, and write pytest tests to verify all endpoints"
```

ایجنت به صورت خودکار:
1. وارد مسیر `./my_fastapi_app` می‌شود.
2. ساختار پروژه را طرح‌ریزی می‌کند.
3. فایل‌های `main.py`, `models.py`, `database.py`, `requirements.txt` را می‌سازد.
4. پکیج‌های لازم را نصب می‌کند (`pip install fastapi uvicorn pytest ...`).
5. فایل `test_main.py` را می‌سازد و با `pytest` اجرا می‌کند.
6. در صورت خطا، با بررسی خطاها آن‌ها را برطرف می‌کند.
7. در انتها گزارش نهایی و دستور اجرای سرور را ارائه می‌دهد.

### ۲. حالت تعاملی (Interactive REPL Mode)
```bash
python main.py
```
پس از پاسخ به سوالات اولیه و اجرای درخواست اول، می‌توانید در همان محیط به کار ادامه دهید:
```text
Next task > Add JWT authentication and login endpoint
```
ایجنت تغییرات را با حفظ حافظه و کانتکست قبلی پیاده می‌کند.

---

## 🏗 ساختار پروژه

```text
ai-harness/
├── .env.example              # نمونه فایل تنظیمات محیطی
├── requirements.txt          # وابستگی‌های پروژه
├── README.md                 # راهنمای جامع فارسی و انگلیسی
├── main.py                   # نقطه ورودی اصلی برنامه
├── harness/
│   ├── __init__.py
│   ├── config.py             # مدیریت تنظیمات و اعتبارسنجی
│   ├── llm_client.py         # کلاینت سازگار با DeepSeek و OpenAI
│   ├── prompts.py            # پرامپت سیستمی مهندس نرم‌افزار خودکار
│   ├── context_manager.py    # مدیریت کانتکست، توکن و حافظه پایدار
│   ├── agent.py              # حلقه اصلی ایجنت (ReAct Engine)
│   ├── ui.py                 # فرمت‌بندی خروجی‌های ترمینال با Rich
│   └── tools/                # جعبه ابزارهای ایجنت
│       ├── __init__.py       # رجیستری ابزارها
│       ├── base.py           # کلاس پایه و تبدیل به OpenAI Tools Schema
│       ├── filesystem.py     # خواندن، نوشتن و جایگزینی جراحی فایل‌ها
│       ├── terminal.py       # اجرای دستورات ترمینال با مهار خروجی
│       └── memory.py         # مدیریت اسکرچ‌پد و اعلام پایان کار
└── tests/                    # تست‌های واحد و یکپارچگی
    ├── test_harness.py       # تست تمام ابزارها و ماژول‌ها
    └── test_agent_mock.py    # شبیه‌سازی چرخه کامل عملکرد ایجنت
```

---

## 🧪 اجرای تست‌ها

برای اطمینان از سلامت تمام ابزارها و ماژول‌های سیستم:
```bash
python -m unittest discover tests
```
تمام تست‌ها به صورت ایزوله اجرا شده و صحت عملکرد ابزارهای فایل، ترمینال، حافظه و حلقه ایجنت را می‌سنجند.
