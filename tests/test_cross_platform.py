"""محافظ‌های بین‌پلتفرمی: تفاوت ویندوز و لینوکس نباید تست‌ها را بشکند.

چه اتفاقی افتاد (و چرا این فایل ساخته شد): روی ``windows-latest`` پیش‌فرض
رمزگشایی متن برای زیرفروندها cp1252 است. ``subprocess.run(text=True)``
خروجی فارسیِ node را با cp1252 رمزگشایی می‌کرد، در رشتهٔ خواننده
``UnicodeDecodeError`` می‌داد و ``result.stdout`` برابر ``None`` می‌ماند؛
آنگاه ``assert "FAIL" not in result.stdout`` با ``TypeError`` می‌شکست.
روی لینوکس همین کد سبز است، پس این دسته خطا فقط در CI ویندوز پیدا می‌شود.

این تست‌ها تفاوت‌های پلتفرمی را به شکست قطعیِ قابل‌تشخیص تبدیل می‌کنند.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: توابع ``subprocess`` که می‌توانند خروجی متنی بدهند.
_TEXT_SUBPROCESS_FUNCS = {
    "run", "call", "check_call", "check_output", "Popen",
}

#: ماژول‌هایی که نباید مسیر مطلق یونیکسی در کد محصول داشته باشند.
_POSIX_ONLY_PREFIXES = ("/tmp/", "/home/", "/var/", "/dev/", "/etc/")


def _python_files() -> list[Path]:
    """همهٔ فایل‌های پایتون پروژه (تست‌ها و کد محصول)."""
    files: list[Path] = []
    for folder in ("tests", "src"):
        files.extend(sorted((ROOT / folder).rglob("*.py")))
    return files


def _keyword_value(call: ast.Call, name: str) -> ast.expr | None:
    for keyword in call.keywords:
        if keyword.arg == name:
            return keyword.value
    return None


def _is_true(node: ast.expr | None) -> bool:
    return isinstance(node, ast.Constant) and node.value is True


def _has_star_kwargs(call: ast.Call) -> bool:
    return any(keyword.arg is None for keyword in call.keywords)


def _is_subprocess_text_call(call: ast.Call) -> bool:
    func = call.func
    if not isinstance(func, ast.Attribute) or not isinstance(func.value, ast.Name):
        return False
    if func.value.id != "subprocess" or func.attr not in _TEXT_SUBPROCESS_FUNCS:
        return False
    return _is_true(_keyword_value(call, "text"))


# ---------------------------------------------------------------------------
# ۱) خروجی متنی زیرفروندها باید UTF-8 صریح داشته باشد
# ---------------------------------------------------------------------------


def test_every_text_subprocess_call_pins_utf8_encoding() -> None:
    """``text=True`` بدون ``encoding`` روی ویندوز خروجی فارسی را خراب می‌کند.

    ``encoding="utf-8"`` باید صریح پاس داده شود؛ وگرنه ویندوز از cp1252
    استفاده می‌کند و رشتهٔ خوانندهٔ ``subprocess`` با
    ``UnicodeDecodeError`` می‌شکند.
    """
    offenders: list[str] = []
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or _has_star_kwargs(node):
                continue
            if not _is_subprocess_text_call(node):
                continue
            encoding = _keyword_value(node, "encoding")
            if encoding is None:
                offenders.append(f"{path.relative_to(ROOT)}:{node.lineno} بدون encoding")
            elif isinstance(encoding, ast.Constant) and encoding.value != "utf-8":
                offenders.append(
                    f"{path.relative_to(ROOT)}:{node.lineno} encoding={encoding.value!r}"
                )
    assert not offenders, (
        "خروجی متنی زیرفروند باید UTF-8 صریح داشته باشد: " + "; ".join(offenders)
    )


def test_subprocess_error_messages_do_not_assume_text_output() -> None:
    """پیام خطای زیرفروند نباید ``stdout + stderr`` کورکورانه جمع شود.

    اگر رمزگشایی شکست بخورد، ``subprocess`` مقدار ``stdout``/``stderr`` را
    ``None`` می‌گذارد؛ ``None + None`` خطای واقعی را پنهان می‌کند.
    """
    offenders: list[str] = []
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assert) or not isinstance(node.test, ast.Compare):
                continue
            for comparator in node.test.comparators:
                if not isinstance(comparator, ast.BinOp) or not isinstance(comparator.op, ast.Add):
                    continue
                names = {
                    operand.id
                    for operand in (comparator.left, comparator.right)
                    if isinstance(operand, ast.Name)
                }
                if {"stdout", "stderr"} <= names:
                    offenders.append(f"{path.relative_to(ROOT)}:{node.lineno}")
    assert not offenders, (
        "به‌جای stdout + stderr از مقدار پیش‌فرض رشته‌ای استفاده کنید: "
        + "; ".join(offenders)
    )


# ---------------------------------------------------------------------------
# ۲) خواندن/نوشتن فایل متنی باید رمزگذاری صریح داشته باشد
# ---------------------------------------------------------------------------


def test_every_text_file_access_pins_an_encoding() -> None:
    """``open()``/``read_text()``/``write_text()`` بدون ``encoding`` پلتفرمی است.

    پیش‌فرض ویندوز cp1252 است و لینوکس UTF-8؛ همین اختلاف، خواندن یا
    نوشتن فارسی را روی یکی از دو پلتفرم می‌شکند.
    """
    offenders: list[str] = []
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or _has_star_kwargs(node):
                continue
            func = node.func
            is_path_method = isinstance(func, ast.Attribute) and func.attr in {
                "read_text", "write_text",
            }
            is_builtin_open = isinstance(func, ast.Name) and func.id == "open"
            if not (is_path_method or is_builtin_open):
                continue
            if _keyword_value(node, "encoding") is None:
                offenders.append(f"{path.relative_to(ROOT)}:{node.lineno}")
    assert not offenders, (
        "دسترسی متنی به فایل باید encoding صریح داشته باشد: " + "; ".join(offenders)
    )


# ---------------------------------------------------------------------------
# ۳) کد محصول نباید به مسیرهای مطلق یونیکسی تکیه کند
# ---------------------------------------------------------------------------


def test_product_code_has_no_posix_only_absolute_paths() -> None:
    """مسیر مطلق یونیکسی روی ویندوز به درایو جاری translate می‌شود."""
    offenders: list[str] = []
    for path in sorted((ROOT / "src").rglob("*.py")):
        for number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for prefix in _POSIX_ONLY_PREFIXES:
                if prefix in line:
                    offenders.append(f"{path.relative_to(ROOT)}:{number}")
                    break
    assert not offenders, (
        "مسیر مطلق یونیکسی در کد محصول: " + "; ".join(offenders)
    )


# ---------------------------------------------------------------------------
# ۴) اسکریپت‌های ساخت artifact باید خروجی قطعی و مستقل از پلتفرم بدهند
# ---------------------------------------------------------------------------

#: اسکریپت‌هایی که خروجی‌شان در مخزن کامیت و بایت‌به‌بایت مقایسه می‌شود.
_ARTIFACT_SCRIPTS = ("preview", "packaging")


def test_artifact_scripts_pin_newline_on_every_write() -> None:
    """خروجی artifact‌ها باید روی همهٔ پلتفرم یکسان باشد.

    ``Path.write_text`` با ``newline=None`` روی ویندوز CRLF می‌نویسد و روی
    لینوکس LF. چون این فایل‌ها در مخزن کامیت شده و بازتولیدپذیری‌شان تست
    می‌شود، پایان‌خط باید صریح تثبیت شود.
    """
    offenders: list[str] = []
    for folder in _ARTIFACT_SCRIPTS:
        for path in sorted((ROOT / folder).rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or _has_star_kwargs(node):
                    continue
                func = node.func
                if not (isinstance(func, ast.Attribute) and func.attr == "write_text"):
                    continue
                newline = _keyword_value(node, "newline")
                if not (isinstance(newline, ast.Constant) and newline.value == "\n"):
                    offenders.append(f"{path.relative_to(ROOT)}:{node.lineno}")
    assert not offenders, (
        'نوشتن artifact باید newline="\\n" صریح داشته باشد: ' + "; ".join(offenders)
    )
