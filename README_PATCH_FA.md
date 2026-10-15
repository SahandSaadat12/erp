# اعمال پچ

1. محتوای این پوشه را روی ریشه پروژه (کنار main.py) کپی کن و Replace بزن.
   فایل‌های جدید/تغییرکرده: main.py ، main.spec ، build_exe.bat ، installer.iss ،
   utils/restart.py ، utils/app_icon.py ، tools/make_icons.py ، icons/app*.ico|png
2. پوشه‌های قدیمی `build` و `dist` و فایل `ERP.spec` را پاک کن (دیگر لازم نیستند).
3. `build_exe.bat` را اجرا کن. خروجی: `dist\ERP\ERP.exe`
   (اگر Inno Setup 6 نصب باشد: `installer\ERP_Setup.exe` هم ساخته می‌شود.)
4. برای تحویل: کل پوشه `dist\ERP` را zip کن، یا فقط `ERP_Setup.exe` را بده.
   روی لپتاپ مقصد پایتون/کتابخانه لازم نیست.
