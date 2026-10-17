"""نقطهٔ ورود بسته‌بندی‌شده (PyInstaller).

فایل ``src/k2/__main__.py`` از «نسبی» ایمپورت می‌کند و وقتی به‌عنوان
اسکریپت ریشه بسته‌بندی شود کار نمی‌کند (``attempted relative import with
no known parent package``). این فایل یک اسکریپت ریشهٔ مستقل است و بسته‌بندی
همیشه از آن شروع می‌شود.
"""

from __future__ import annotations

import sys

from k2.app import main

if __name__ == "__main__":
    sys.exit(main())
