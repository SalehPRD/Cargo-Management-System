# Cargo Management System
## سامانه آنلاین اعلام بار کارخانه‌جات

سیستم هوشمند مدیریت بارگیری و ناوگان کارخانه با امکان اعلام بار لحظه‌ای، صف‌بندی خودکار رانندگان و پیگیری زنده وضعیت بارگیری.

---

## نصب و اجرا

پیش‌نیازها: Python 3.11+ و uv

مراحل نصب:

1- کلون کردن پروژه:
git clone https://github.com/SalehPRD/Cargo-Management-System.git
cd Cargo-Management-System

2- ساخت محیط مجازی:
uv venv
source .venv/bin/activate

3- نصب پکیج‌ها:
uv add fastapi uvicorn python-jose[cryptography] passlib[bcrypt] jinja2 python-multipart

4- اجرای سرور:
uvicorn main:app --reload --port 8001

5- باز کردن مرورگر:
http://127.0.0.1:8001

---

## نقش‌ها

- ادمین اصلی: مدیریت کامل سیستم
- ادمین زیرشاخه: مدیریت بار و راننده  
- راننده: نوبت‌گیری و انتخاب بار

---

## تکنولوژی‌ها

- Backend: FastAPI + Python
- Frontend: Jinja2 + HTML + CSS
- Storage: JSON Files
- Auth: JWT
