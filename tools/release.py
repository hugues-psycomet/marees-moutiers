#!/usr/bin/env python3
"""Horodate une nouvelle version : APP_VERSION (index.html) = version.json = sw.js.
Le dépôt contient désormais la SOURCE (index.html édité directement) ; plus de build.py/app_template.html.
Usage : python3 tools/release.py   (depuis la racine du dépôt)"""
import re, json, datetime, zoneinfo, pathlib
root = pathlib.Path(__file__).resolve().parent.parent
v = datetime.datetime.now(zoneinfo.ZoneInfo('Europe/Paris')).strftime('%Y.%m.%d-%H%M')
idx = root/'index.html'; s = idx.read_text(encoding='utf-8')
s, n = re.subn(r"const APP_VERSION = '[^']*';", f"const APP_VERSION = '{v}';", s); assert n == 1
idx.write_text(s, encoding='utf-8')
(root/'version.json').write_text(json.dumps({'v': v}))
sw = root/'sw.js'; t = sw.read_text(encoding='utf-8')
t, n = re.subn(r"const V = '[^']*';", f"const V = '{v}';", t); assert n == 1
sw.write_text(t, encoding='utf-8')
print('version', v)
