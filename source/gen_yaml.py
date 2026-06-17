#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-off: convert predefined.json -> human-readable questions.yaml + presets.yaml."""
import json, os, yaml
HERE = os.path.dirname(os.path.abspath(__file__))
data = json.load(open(os.path.join(HERE, "predefined.json"), encoding="utf-8"))

group_order = ["CORE", "MEDIUM", "SPECIFIC"]
cats_by_group = {g: [c["name"] for c in data["categories"] if c["group"] == g] for g in group_order}

# questions grouped by category, preserving first-appearance order (keeps ids stable)
qby = {}
for q in data["questions"]:
    item = {"level": q["difficulty"], "q": q["question"]}
    keys = [k for k in q["keyPoints"] if k and k.strip()]
    item["keys"] = keys
    qby.setdefault(q["category"], []).append(item)

hdr = [
 "# Банк вопросов и категории для опросника собеседований.",
 "# Файл редактируется руками; build.py собирает из него index.html.",
 "#",
 "# categories — технологии по группам важности:",
 "#   CORE — обязательно для всех инженеров; MEDIUM — желательно; SPECIFIC — под конкретный проект.",
 "categories:",
]
for g in group_order:
    hdr.append("  %s: [%s]" % (g, ", ".join(cats_by_group[g])))
hdr += [
 "",
 "# questions — банк вопросов. Ключ = категория (должна присутствовать в categories выше).",
 "#   level: Low | Medium | High",
 "#   q:     текст вопроса",
 "#   keys:  ключевые точки — подсказки интервьюеру (0–3 шт.)",
]
qyaml = yaml.safe_dump({"questions": qby}, sort_keys=False, allow_unicode=True,
                       default_flow_style=False, width=4096)
open(os.path.join(HERE, "questions.yaml"), "w", encoding="utf-8").write("\n".join(hdr) + "\n" + qyaml)

# presets: group each preset's questions by category (human-readable, references by text)
qid2 = {q["id"]: q for q in data["questions"]}
presets_out = []
for p in data["presets"]:
    grouped = {}
    for qid in p["questionIds"]:
        q = qid2[qid]
        grouped.setdefault(q["category"], []).append(q["question"])
    po = {"id": p["id"], "name": p["name"]}
    if p.get("builtin"):
        po["builtin"] = True
    po["questions"] = grouped
    presets_out.append(po)

phdr = [
 "# Готовые наборы вопросов (пресеты).",
 "# questions сгруппированы по категории; значения — точные тексты вопросов из questions.yaml.",
 "# build.py сопоставляет их с банком по паре (категория, текст вопроса).",
]
pyaml = yaml.safe_dump({"presets": presets_out}, sort_keys=False, allow_unicode=True,
                       default_flow_style=False, width=4096)
open(os.path.join(HERE, "presets.yaml"), "w", encoding="utf-8").write("\n".join(phdr) + "\n" + pyaml)
print("wrote questions.yaml (%d categories) and presets.yaml (%d presets)" % (len(qby), len(presets_out)))
