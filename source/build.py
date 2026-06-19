#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сборка index.html.

Источники данных (редактируются руками):
  questions.yaml — категории (с группами) и банк вопросов
  presets.yaml   — готовые наборы вопросов
Матрицы оценок заданы ниже в коде (редко меняются; правятся ещё и в самом приложении).

Запуск:  python3 build.py            -> пишет ../index.html (или $OUT_DIR/index.html)
         python3 build.py --data-only -> пишет predefined.json (для отладки)

Зависимость: PyYAML  (pip install pyyaml  /  pip install pyyaml --break-system-packages)
"""
import json, os, sys

try:
    import yaml
except ImportError:
    sys.exit("Нужен PyYAML:  pip install pyyaml   (или: pip install pyyaml --break-system-packages)")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.environ.get("OUT_DIR") or os.path.dirname(HERE)

def load_yaml(name):
    path = os.path.join(HERE, name)
    if not os.path.exists(path):
        sys.exit("Не найден файл данных: %s" % path)
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)

# ---------- матрицы и константы ----------
DIFFICULTIES = ["Low", "Medium", "High"]
GRADES = ["jun", "mid", "mid+", "senior", "senior+"]
QUALITIES = ["Не знает", "Что-то слышал", "Что-то знает", "Уверенно знает"]

SCORE_MATRIX = {
    "Уверенно знает": {"Low": 1,    "Medium": 3,   "High": 5},
    "Что-то знает":   {"Low": 0.5,  "Medium": 2,   "High": 3},
    "Что-то слышал":  {"Low": 0.25, "Medium": 0.5, "High": 1},
    "Не знает":       {"Low": 0,    "Medium": 0,   "High": 0},
}
EXPECTATIONS = {
    "jun":     {"Low": "Что-то знает",   "Medium": "Что-то слышал",  "High": "Не знает"},
    "mid":     {"Low": "Уверенно знает", "Medium": "Что-то знает",   "High": "Что-то слышал"},
    "mid+":    {"Low": "Уверенно знает", "Medium": "Уверенно знает", "High": "Что-то слышал"},
    "senior":  {"Low": "Уверенно знает", "Medium": "Уверенно знает", "High": "Что-то знает"},
    "senior+": {"Low": "Уверенно знает", "Medium": "Уверенно знает", "High": "Уверенно знает"},
}

# ---------- категории ----------
GROUP_ORDER = ["CORE", "MEDIUM", "SPECIFIC"]
qdoc = load_yaml("questions.yaml")
cats_raw = qdoc.get("categories") or {}
categories = []
for g in GROUP_ORDER:
    for name in (cats_raw.get(g) or []):
        categories.append({"name": str(name), "group": g})
cat_names = {c["name"] for c in categories}
if not categories:
    sys.exit("questions.yaml: пустой список categories")

# ---------- вопросы ----------
questions = []
i = 0
for cat, qlist in (qdoc.get("questions") or {}).items():
    if cat not in cat_names:
        sys.exit("questions.yaml: категория '%s' отсутствует в списке categories" % cat)
    for item in (qlist or []):
        i += 1
        lvl = item.get("level")
        if lvl not in DIFFICULTIES:
            sys.exit("questions.yaml: неверный level '%s' у вопроса: %s" % (lvl, item.get("q")))
        if not item.get("q"):
            sys.exit("questions.yaml: пустой текст вопроса в категории %s" % cat)
        keys = [str(k) for k in (item.get("keys") or [])]
        keys = (keys + ["", "", ""])[:3]
        questions.append({"id": "q%d" % i, "category": cat, "difficulty": lvl,
                          "question": str(item["q"]), "keyPoints": keys})

# ---------- пресеты ----------
qindex = {(q["category"], q["question"]): q["id"] for q in questions}
pdoc = load_yaml("presets.yaml")
presets = []
for p in (pdoc.get("presets") or []):
    ids, missing = [], []
    for cat, texts in (p.get("questions") or {}).items():
        for t in (texts or []):
            key = (cat, str(t))
            (ids.append(qindex[key]) if key in qindex else missing.append(key))
    if missing:
        sys.exit("presets.yaml: пресет '%s' — вопросы не найдены в банке: %s" % (p.get("name"), missing))
    pr = {"id": p["id"], "name": p["name"], "questionIds": ids}
    if p.get("builtin"):
        pr["builtin"] = True
    presets.append(pr)

data = {
    "version": 1,
    "categories": categories,
    "grades": GRADES,
    "difficulties": DIFFICULTIES,
    "qualities": QUALITIES,
    "scoreMatrix": SCORE_MATRIX,
    "expectations": EXPECTATIONS,
    "questions": questions,
    "presets": presets,
}

# ---------- версия и changelog (источник правды: CHANGELOG.md) ----------
import re as _re
def _read_changelog():
    for p in (os.path.join(OUT_DIR, "CHANGELOG.md"), os.path.join(HERE, "CHANGELOG.md"), os.path.join(os.path.dirname(HERE), "CHANGELOG.md")):
        if os.path.exists(p):
            return open(p, encoding="utf-8").read()
    return ""
CHANGELOG = _read_changelog()
_m = _re.search(r"^##\s*\[([0-9]+\.[0-9]+\.[0-9]+)\]", CHANGELOG, _re.M)
APP_VERSION = _m.group(1) if _m else "0.0.0"
print("Version:", APP_VERSION, "| changelog:", "found" if CHANGELOG else "MISSING")

# ---------- проверка математики порогов (как в исходной таблице) ----------
def threshold(grade, nLow, nMed, nHigh):
    e = EXPECTATIONS[grade]
    return (nLow * SCORE_MATRIX[e["Low"]]["Low"]
            + nMed * SCORE_MATRIX[e["Medium"]]["Medium"]
            + nHigh * SCORE_MATRIX[e["High"]]["High"])

expected = {"jun": 12.5, "mid": 44, "mid+": 59, "senior": 67, "senior+": 75}
got = {g: threshold(g, 10, 15, 4) for g in GRADES}
assert got == expected, "Scoring mismatch: %s != %s" % (got, expected)
print("Scoring check OK:", got)
print("Categories:", len(categories), "| Questions:", len(questions))
by_diff = {d: sum(1 for x in questions if x["difficulty"] == d) for d in DIFFICULTIES}
print("By difficulty:", by_diff)
for p in presets:
    pdiff = {d: sum(1 for qid in p["questionIds"]
                    if next(q for q in questions if q["id"] == qid)["difficulty"] == d) for d in DIFFICULTIES}
    print("Preset '%s':" % p["name"], len(p["questionIds"]), "вопр. | по сложности:", pdiff)

# ---------- запись ----------
TEMPLATE = os.path.join(HERE, "template.html")
OUT = os.path.join(OUT_DIR, "index.html")

if "--data-only" in sys.argv or not os.path.exists(TEMPLATE):
    with open(os.path.join(HERE, "predefined.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("Wrote predefined.json" + ("" if os.path.exists(TEMPLATE) else " (template not found yet)"))
    sys.exit(0)

with open(TEMPLATE, encoding="utf-8") as f:
    tpl = f.read()
needle = "/*__PREDEFINED_DATA__*/ null"
assert needle in tpl, "placeholder not found in template"
tpl = tpl.replace(needle, json.dumps(data, ensure_ascii=False))
tpl = tpl.replace('/*__APP_VERSION__*/ "0.0.0"', json.dumps(APP_VERSION))
tpl = tpl.replace('/*__APP_CHANGELOG__*/ ""', json.dumps(CHANGELOG, ensure_ascii=False))
os.makedirs(OUT_DIR, exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(tpl)
print("Wrote", OUT, "(%d bytes)" % len(tpl))
