"""
Hindi translations without installing GNU gettext (handy on Windows).

    python scripts/translations.py extract   # add new English strings to locale/hi/.../django.po
    python scripts/translations.py compile   # build django.mo from django.po

Edit Hindi text in locale/hi/LC_MESSAGES/django.po (the msgstr lines), then run compile
and restart the server.
"""
import re
import sys
from pathlib import Path

import polib

ROOT = Path(__file__).resolve().parent.parent
PO = ROOT / "locale" / "hi" / "LC_MESSAGES" / "django.po"

TRANS = re.compile(r"""{%\s*translate\s+(?P<q>["'])(?P<s>.+?)(?P=q)""")
BLOCK = re.compile(r"{%\s*blocktranslate\b(?P<args>[^%]*)%}(?P<body>.*?){%\s*endblocktranslate\s*%}", re.S)
PY = re.compile(r"""(?<![\w.])_\(\s*(?P<q>["'])(?P<s>.+?)(?P=q)\s*[,)]""")


def _norm_block(body):
    # Django turns {{ var }} into %(var)s inside blocktranslate.
    return re.sub(r"{{\s*(\w+)\s*}}", r"%(\1)s", body)


def extract():
    found = {}  # msgid -> plural or None
    for path in list((ROOT / "templates").rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        for m in TRANS.finditer(text):
            found.setdefault(m.group("s"), None)
        for m in BLOCK.finditer(text):
            body = m.group("body")
            if "{% plural %}" in body:
                single, plural = body.split("{% plural %}")
                found[_norm_block(single)] = _norm_block(plural)
            else:
                found.setdefault(_norm_block(body), None)
    for path in (ROOT / "apps").rglob("*.py"):
        if "migrations" in path.parts:
            continue
        for m in PY.finditer(path.read_text(encoding="utf-8")):
            found.setdefault(m.group("s"), None)
    return found


def cmd_extract():
    po = polib.pofile(str(PO)) if PO.exists() else polib.POFile()
    po.metadata = {
        "Content-Type": "text/plain; charset=UTF-8",
        "Language": "hi",
        "Plural-Forms": "nplurals=2; plural=(n != 1);",
    }
    have = {e.msgid for e in po}
    added = 0
    for msgid, plural in sorted(extract().items()):
        if msgid in have:
            continue
        if plural:
            po.append(polib.POEntry(msgid=msgid, msgid_plural=plural, msgstr_plural={0: "", 1: ""}))
        else:
            po.append(polib.POEntry(msgid=msgid, msgstr=""))
        added += 1
    PO.parent.mkdir(parents=True, exist_ok=True)
    po.save(str(PO))
    missing = [e.msgid for e in po if not (e.msgstr or any(e.msgstr_plural.values()))]
    print(f"{added} new strings. {len(missing)} still need Hindi.")
    for m in missing:
        print("  -", m)


def cmd_compile():
    po = polib.pofile(str(PO))
    po.save_as_mofile(str(PO.with_suffix(".mo")))
    print(f"Compiled {len(po.translated_entries())} Hindi strings.")


if __name__ == "__main__":
    {"extract": cmd_extract, "compile": cmd_compile}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: print(__doc__))()
