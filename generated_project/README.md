# سامانه مدیریت از راه دور (Remote Command Management System)

سروری که می‌تواند به چند سیستم (کلاینت/عامل) متصل شود، به آن‌ها **کامند شل** بفرستد و **نتیجه اجرا** را برگشت بگیرد. مناسب برای مدیریت چند سیستم از یک نقطه مرکزی.

## معماری

- `server.py` — مرکز فرماندهی؛ به کلاینت‌ها گوش می‌دهد، لیست آن‌ها را نگه می‌دارد و به شما اجازه می‌دهد کامند بفرستید.
- `client.py` — عامل روی هر سیستم؛ به سرور متصل می‌شود، منتظر کامند می‌ماند و نتیجه را برمی‌گرداند.
- `protocol.py` — پروتکل مشترک شبکه (پیام JSON با هدر طول ۴ بایتی).

> **💻 کلاینت به‌طور پیش‌فرض با PowerShell کار می‌کند.** روی ویندوز، دستورهایی که از سرور می‌فرستید در PowerShell اجرا می‌شوند (نه cmd)، پس می‌توانید از دستورهایی مانند `Get-ChildItem`، `Get-Process`، `Write-Output` و… استفاده کنید. اگر PowerShell پیدا نشد، به‌صورت خودکار به شل پیش‌فرض سیستم برمی‌گردد.

## نصب

```bash
pip install -r requirements.txt
```

## اجرا

روی سیستم مرکزی (سرور):

```bash
python server.py --host 0.0.0.0 --port 5555
```

روی هر سیستم هدف (کلاینت):

```bash
python client.py --host <IP-سرور> --port 5555
```

گزینه‌های شل کلاینت:

| گزینه | توضیح |
|-------|-------|
| `--shell powershell` | اجرا با PowerShell (پیش‌فرض روی ویندوز) |
| `--shell cmd` | اجرا با cmd.exe (ویندوز) |
| `--shell auto` | اگر PowerShell موجود بود از آن، وگرنه شل پیش‌فرض سیستم |

مثال اجرای کلاینت با PowerShell:

```bash
python client.py --host 192.168.1.50 --port 5555 --shell powershell
```

## دستورهای کنسول سرور

| دستور | توضیح |
|-------|-------|
| `LIST` | نمایش کلاینت‌های متصل (با cid آن‌ها) |
| `SEND <cid> <command...>` | ارسال کامند به یک کلاینت خاص |
| `BROADCAST <command...>` | ارسال کامند به همه کلاینت‌ها |
| `EXIT` | خروج از سرور |

مثال (با کلاینت PowerShell):

```
server> LIST
server> SEND a1b2c3d4 Write-Output 'hello from server'
server> SEND a1b2c3d4 Get-ChildItem
server> BROADCAST Get-Process -Name explorer
```

## تست

```bash
python -m pytest
```
