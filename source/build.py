#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Builds the predefined dataset from the original Google Sheet and injects it
into template.html to produce the final single-file index.html."""
import json, os, re, sys

# ---------- Categories with groups (from "Questions" tab, right column) ----------
GROUPS = [
    ("CORE", ["Linux", "Helm", "Ansible", "Kubernetes", "Docker", "CI/CD",
              "Postgresql", "ELK", "Virtualization", "Nginx", "Git"]),
    ("MEDIUM", ["Networking", "Terraform", "S3", "Kafka", "Rabbitmq", "Consul",
                "Cloud", "Redis", "Sentry", "Artifactory", "Victoriametrics", "Gitlab"]),
    ("SPECIFIC", ["Allure", "Service Mesh", "Keycloak", "Openshift", "Windows",
                  "Packer", "Hashicorp Vault", "Clickhouse", "Ignite", "Cassandra", "Jenkins"]),
]
categories = []
for grp, names in GROUPS:
    for n in names:
        categories.append({"name": n, "group": grp})

# ---------- Score matrix: quality x difficulty ----------
score_matrix = {
    "Уверенно знает": {"Low": 1,    "Medium": 3,   "High": 5},
    "Что-то знает":   {"Low": 0.5,  "Medium": 2,   "High": 3},
    "Что-то слышал":  {"Low": 0.25, "Medium": 0.5, "High": 1},
    "Не знает":       {"Low": 0,    "Medium": 0,   "High": 0},
}
qualities = ["Не знает", "Что-то слышал", "Что-то знает", "Уверенно знает"]
difficulties = ["Low", "Medium", "High"]
grades = ["jun", "mid", "mid+", "senior", "senior+"]

# ---------- Expectations matrix: grade -> {difficulty: expected quality} ----------
expectations = {
    "jun":     {"Low": "Что-то знает",   "Medium": "Что-то слышал",  "High": "Не знает"},
    "mid":     {"Low": "Уверенно знает", "Medium": "Что-то знает",   "High": "Что-то слышал"},
    "mid+":    {"Low": "Уверенно знает", "Medium": "Уверенно знает", "High": "Что-то слышал"},
    "senior":  {"Low": "Уверенно знает", "Medium": "Уверенно знает", "High": "Что-то знает"},
    "senior+": {"Low": "Уверенно знает", "Medium": "Уверенно знает", "High": "Уверенно знает"},
}

# ---------- Question bank (category, difficulty, question, kp1, kp2, kp3) ----------
# Faithful port of the "Questions" tab. Pure-placeholder ("TODO") rows are dropped;
# empty key points are kept blank so they can be filled in the editor.
Q = [
 # Linux
 ("Linux","Low","Что такое systemd и зачем он нужен","знает что systemd это подсистема инициализации и управления службами","знает про service, timer, socket, ...","знает про systemd-(networkd, resolved, timesyncd, journald, ...)"),
 ("Linux","Low","Какие права на файл бывают","знает про RWX","знает про группу, пользователя, остальных","может привести примеры"),
 ("Linux","Medium","Как посмотреть доступные системе ресурсы ЦПУ ОЗУ / Как оценить утилизацию ресурсов","знает что вся информация хранится в /proc","рассказывает про top, htop, atop, free -m, df -h","знает почему LA не показателен"),
 ("Linux","Medium","что такое systemd unit и его структура для сервиса","знает про блоки unit, service, install","знает про execstart-stop, requires-after","знает про environment, что такое \"-\" после ="),
 ("Linux","Medium","опиши порядок загрузки linux","знает про GRUB","знает про initrd","знает про init и systemd"),
 ("Linux","Medium","Что такое lvm / привести пример как настроить","знает про pvs, lvs, vgs","знает что с помощью lvm можно растянуть том на несколько дисков","может описать процесс добавления места в логический том"),
 ("Linux","Medium","опиши процесс добавления места на жесткий диск для виртуальной машины","знает про то как добавить диск на лету","знает как пересоздать раздел к которому добавляем место","знает про resize2fs"),
 ("Linux","Medium","задача: есть отдельно смонтированный раздел /var/log, на котором всего 1 файл = 1Gb, df говорит всё занято / почему","знает про inodes","знает про то, что процесс может держать файл","знает хотя бы один способ как отпустить файл"),
 ("Linux","Medium","какие сигналы можно слать процессам / отличие SIGKILL / SIGTERM","знает, что существует 15 сигналов","может привести примеры сигналов помимо килл и терм","знает чем отличется килл от терм"),
 ("Linux","High","как работают системы типа cloud init / ignition / kickstart","знает про то как сформировать конфигурационный файл и что вообще можно настроить","знает когда и в какой момент что cloud-init может сделать","может привести примеры что он настраивал через этот механизм"),
 ("Linux","High","контекстное переключение / системные вызовы / организация памяти процесса / планировщик задач","знает про контекстное переключение, планировщик","знает что такое syscall, что при старте системы создается таблица с адресами этих сисколов","знает про организацию памяти процесса, TLB"),
 ("Linux","High","нужно ли перезагружать ОС после обновления / в каких случаях и как можно этого избежать / как минимизировать простой","знает про /run/reboot-required","знает что можно посмотреть lsof для списка удаленных файлов","знает что существуют механизмы, как у nginx, для подмены бинарника"),
 # Helm
 ("Helm","Low","структура helm пакета","знает про helpers.tpl","знает про values, templates","знает про chart.yml"),
 ("Helm","Medium","как откатить плохой релиз","знает про миграции или иные проблемы","знает про роллбек и может описать процесс отката","знает где хранятся данные \"релиза\""),
 ("Helm","Medium","как связываются друг с другом манифесты","знает про selector, labels","знает про metadata.labels && spec.template.metadata.labels","рассказывает про структуру переменных, helpers.tpl"),
 ("Helm","Medium","как перезапускать поды при изменении конфигурации","знает про watchdog'и","предполагает, что процесс может сам перечитывать раз в минуту","предлагает вариант с хеш суммой конфигмапа"),
 ("Helm","High","Chart Hooks / Debugging Templates","","",""),
 ("Helm","High","helmfile / helm-secrets","","",""),
 # Ansible
 ("Ansible","Low","Какие виды переменных существуют и их приоритеты","знает про extra vars, set_fact","group_vars, host_vars, all","переменные в роли, в таске, в плее"),
 ("Ansible","Medium","структура ансибл роли","tasks, handlers, templates, files, defaults, vars","meta","library, lookup_plugins, module_utils"),
 ("Ansible","Medium","как в ansible описать 3 разных кластера etcd / как будет выглядеть структура плейбука","предлагает использовать роль","рассказывает, что разделил бы сервера в инвентаре на группы","создаем group_vars, host_vars, all"),
 ("Ansible","High","писал ли свои фильтры или модули для Ansible на python","знает про структуру модуля","знает зачем нужны фильтры","может привести примеры какие задачи решал"),
 # Kubernetes
 ("Kubernetes","Low","из каких компонент состоит кластер k8s","апи, шедулер, итп","кубелет, кубепрокси","CNI"),
 ("Kubernetes","Medium","какую роль выполняет Api Server / где хранит данные","знает что это входящая точка для всех запросов и получения информации","знает что хранится в етцд","может рассказать как сделать отказоустойчивый кластер"),
 ("Kubernetes","Low","какой тип деплоя нужно использовать чтобы развернуться на всех нодах кластера","знает про демонсет","может привести примеры что через него можно разворачивать","а что если нет возможности сделать демонсет?"),
 ("Kubernetes","Medium","безопасно ли использовать secrets / чем отличается от ConfigMap","знает про base64 КОДИРОВАНИЕ","знает что секреты не шифруются в етцд по-умолчанию","понимает что в целом мы все равно и ключ и секрет храним на диске внутри кластера"),
 ("Kubernetes","Medium","requests limits / Опиши процесс выставления для нового приложения","знает про то что это такое (в каких цифрах выставляются) и что будет если не выставить","знает что превысить лимит по камню нельзя, а по памяти - придет оом","знает как замониторить приложение и выставить реквесты и лимиты"),
 ("Kubernetes","Medium","ливнес, рединес пробы. Как распределяется трафик","знает что это за пробы","знает что происходит когда проба срабатывает","знает как распределяется трафик между репликами при сработке проб"),
 ("Kubernetes","Medium","способы публикации сервиса вовне кластера","знает про ингресс (+ как публиковать сам ингресс)","знает про external ip, nodeport (как трафик долетает)","знает про loadbalancer и как он создается в облаке"),
 # Docker
 ("Docker","High","как трафик доставляется до процесса в контейнере","знает про bridge docker0, знает про network=host","знает что каждый контейнер имеет veth интерфейс со своим ip","знает что iptables выполняет NAT со внешнего интерфейса на veth"),
 ("Docker","Medium","как выполнить динамически изменяемый Dockerfile / например изменять параметры в RUN во время сборки","знает про ARG","может привести пример когда это пригодится",""),
 ("Docker","Medium","Рекомендации при сборке докер образа","знает про многослойность, дает рекомендации, например, объединять RUN","рассказывает про multistage, вычистку кешей","знает про alpine,slim,rootless,scratch"),
 ("Docker","Low","из каких компонент состоит docker","знает про namespaces, может про них рассказать","знает про cgroups, может про них рассказать","знает про docker daemon"),
 ("Docker","Medium","как настроить проверку жизнеспособности контейнера и действия в случае чего","знает про механизм встроенного хелсчека","предлагает вариант с сайдкар хелсчеками","предлагает вариант с запуском через демона, который будет следить за процессом сам"),
 ("Docker","Low","CMD / Entrypoint","знает что такое CMD","знает что такое entrypoint","знает, как они связаны друг с другом"),
 # CI/CD
 ("CI/CD","Low","Какие бывают стейджи stages / Из чего состоит типовой pipeline","build test deploy","sast",""),
 ("CI/CD","High","опиши процесс разработки, сборки, выкатки и доставки продукта","рассказывает про гитфлоу","предлагает автосоздание фича-стендов",""),
 ("CI/CD","Medium","как принести секрет в пайп? какие есть варианты кроме встроенного хранилища","","",""),
 # Postgresql
 ("Postgresql","Low","Какие базы данных бывают SQL NoSQL NewSQL можешь привести примеры. чем отличаются","знает что такое реляционные базы данных и NoSQL","может привести примеры баз данных",""),
 ("Postgresql","Medium","Если бы ты строил отказоустойчивую базу Postgres как бы ты это делал","Знает что такое RAFT и протокол консенсуса и что etcd/consul >= 3","DCS на consul или etcd, несколько экземпляров postgres","что такое синхронная и асинхронная репликация"),
 ("Postgresql","High","Point in time recovery PITR с patroni / recovery signal / timeline / pgrewind","pgbackrest, wal-g, wal-e, barman","",""),
 # Git
 ("Git","Low","Для чего нужна система контроля версий","Совместная разработка и разрешение конфликтов при работе с одним и тем же кодом","",""),
 ("Git","Medium","Разрешение конфликтов merge rebase reset","Знает отличия rebase от reset","Знает как правильно смержить ветки",""),
 ("Git","High","Если удалить коммит, удалится ли он полностью на удаленном репозитории в gitlab","","",""),
 # Virtualization
 ("Virtualization","Low","Отличие виртуализации от контейнеризации и примеры","Может привести примеры виртуализации и контейнеризации","контейнер общее ядро хоста - но более легковесное","более высокая степень изоляции но требуется больше ресурсов"),
 ("Virtualization","Medium","Виртуализация и паравиртуализация (Xen)","","",""),
 # Nginx
 ("Nginx","Low","Как проверить на валидность конфигурацию","nginx -t / в разных дистрибутивах возможны /etc/init.d/nginx checkconfig testconfig","",""),
 ("Nginx","Medium","Какой сигнал заставляет перечитать конфигурацию nginx","HUP","nginx -s reload",""),
 # Networking
 ("Networking","Low","что такое dhcp, как работает","","",""),
 ("Networking","Medium","как сделать DHCP, развернутый в одном сегменте сети, доступным для других сегментов","","",""),
 ("Networking","Low","чем отличается tcp от udp","","",""),
 ("Networking","Low","по какому протоколу работает DNS","","",""),
 ("Networking","Low","если в системе несколько интерфейсов, как трафик будет ходить в интернет?","","",""),
 ("Networking","Medium","есть 2 пк соединенных коммутатором, расскажи про ping пкB с пкА","знает про ARP-запрос, который широковещательно улетит в коммутатор","знает что коммутатор производит маклернинг и имеет свою CAM таблицу","знает состав icmp пакета на L2,L3"),
 ("Networking","Medium","расскажи про инструменты, используемые при отладке сетей","","",""),
 # S3
 ("S3","Low","какой опыт использования S3, поднимал ли свой minio","","",""),
 ("S3","Low","расскажи про процесс создания и доступа к бакету","","",""),
 ("S3","Medium","как строить кластерную версию minio, с какими проблемами сталкивался","","",""),
 ("S3","High","как пробросить бакет в интернет с авторизацией","","",""),
 # Hashicorp Vault
 ("Hashicorp Vault","Low","что такое vault и для чего может быть использован","","",""),
 ("Hashicorp Vault","Medium","в чем смысл хранения секретов в отдельной базе","","",""),
 ("Hashicorp Vault","Low","как выдать доступ к секрету","","",""),
 ("Hashicorp Vault","Low","в чем отличие kv v1 от kv v2","","",""),
 ("Hashicorp Vault","Medium","опыт использования vault как УЦ","","",""),
 ("Hashicorp Vault","Medium","опыт построения отказоустойчивого Hashicorp Vault","","",""),
 # Openshift
 ("Openshift","Medium","Отличия Openshift от ванильного Kubernetes","знает что такое DeploymentConfig / BuildConfig / ImageStream / Operators","Есть удобная вебпанель по управлению кластером","ингресс на основе ha_proxy, встроенный CNI"),
 # Allure
 ("Allure","High","Из каких компонентов состоит allure и за что каждый из них отвечает","","",""),
 # Clickhouse
 ("Clickhouse","High","Шардирование, репликация, подключение к PostgreSQL","","",""),
]

questions = []
for i, (cat, diff, q, k1, k2, k3) in enumerate(Q, start=1):
    questions.append({
        "id": "q%d" % i,
        "category": cat,
        "difficulty": diff,
        "question": q,
        "keyPoints": [k1, k2, k3],
    })

# ---------- Built-in preset: the set selected in the original sheet1 ----------
PRESET_BASE = [
 ("Linux", "Что такое systemd и зачем он нужен"),
 ("Linux", "Какие права на файл бывают"),
 ("Linux", "Как посмотреть доступные системе ресурсы ЦПУ ОЗУ / Как оценить утилизацию ресурсов"),
 ("Linux", "опиши порядок загрузки linux"),
 ("Linux", "опиши процесс добавления места на жесткий диск для виртуальной машины"),
 ("Linux", "какие сигналы можно слать процессам / отличие SIGKILL / SIGTERM"),
 ("Linux", "как работают системы типа cloud init / ignition / kickstart"),
 ("Linux", "контекстное переключение / системные вызовы / организация памяти процесса / планировщик задач"),
 ("Helm", "структура helm пакета"),
 ("Helm", "как откатить плохой релиз"),
 ("Helm", "как связываются друг с другом манифесты"),
 ("Helm", "как перезапускать поды при изменении конфигурации"),
 ("Ansible", "Какие виды переменных существуют и их приоритеты"),
 ("Ansible", "структура ансибл роли"),
 ("Ansible", "как в ansible описать 3 разных кластера etcd / как будет выглядеть структура плейбука"),
 ("Ansible", "писал ли свои фильтры или модули для Ansible на python"),
 ("Kubernetes", "из каких компонент состоит кластер k8s"),
 ("Kubernetes", "какой тип деплоя нужно использовать чтобы развернуться на всех нодах кластера"),
 ("Kubernetes", "безопасно ли использовать secrets / чем отличается от ConfigMap"),
 ("Kubernetes", "requests limits / Опиши процесс выставления для нового приложения"),
 ("Kubernetes", "ливнес, рединес пробы. Как распределяется трафик"),
 ("Docker", "как трафик доставляется до процесса в контейнере"),
 ("Docker", "Рекомендации при сборке докер образа"),
 ("Docker", "из каких компонент состоит docker"),
 ("Docker", "CMD / Entrypoint"),
 ("CI/CD", "опиши процесс разработки, сборки, выкатки и доставки продукта"),
 ("Postgresql", "Если бы ты строил отказоустойчивую базу Postgres как бы ты это делал"),
 ("Networking", "чем отличается tcp от udp"),
 ("Networking", "есть 2 пк соединенных коммутатором, расскажи про ping пкB с пкА"),
]
qindex = {(x["category"], x["question"]): x["id"] for x in questions}
preset_ids, missing = [], []
for cat, qt in PRESET_BASE:
    key = (cat, qt)
    (preset_ids.append(qindex[key]) if key in qindex else missing.append(key))
assert not missing, "Preset questions not found in bank: %s" % missing
assert len(preset_ids) == 29, "Preset size %d, expected 29" % len(preset_ids)
presets = [{"id": "builtin-base", "name": "Базовый набор (как в таблице)",
            "questionIds": preset_ids, "builtin": True}]

data = {
    "version": 1,
    "categories": categories,
    "grades": grades,
    "difficulties": difficulties,
    "qualities": qualities,
    "scoreMatrix": score_matrix,
    "expectations": expectations,
    "questions": questions,
    "presets": presets,
}

# ---------- Verification of the scoring math against the original example ----------
def threshold(grade, nLow, nMed, nHigh):
    e = expectations[grade]
    return (nLow * score_matrix[e["Low"]]["Low"]
            + nMed * score_matrix[e["Medium"]]["Medium"]
            + nHigh * score_matrix[e["High"]]["High"])

# Original sheet1 example had 10 Low / 15 Medium / 4 High -> 12.5/44/59/67/75
expected = {"jun": 12.5, "mid": 44, "mid+": 59, "senior": 67, "senior+": 75}
got = {g: threshold(g, 10, 15, 4) for g in grades}
assert got == expected, "Scoring mismatch: %s != %s" % (got, expected)
print("Scoring check OK:", got)
print("Categories:", len(categories), "| Questions:", len(questions))
by_diff = {d: sum(1 for x in questions if x["difficulty"] == d) for d in difficulties}
print("By difficulty:", by_diff)
pset = {q["id"]: q for q in questions}
pdiff = {d: sum(1 for i in preset_ids if pset[i]["difficulty"] == d) for d in difficulties}
print("Preset 'base':", len(preset_ids), "questions | by difficulty:", pdiff,
      "| thresholds:", {g: threshold(g, pdiff["Low"], pdiff["Medium"], pdiff["High"]) for g in grades})

# ---------- Inject into template ----------
HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "template.html")
# Default: write index.html to the parent of this source folder. Override with OUT_DIR env var.
OUT_DIR = os.environ.get("OUT_DIR") or os.path.dirname(HERE)
OUT = os.path.join(OUT_DIR, "index.html")

if "--data-only" in sys.argv or not os.path.exists(TEMPLATE):
    with open(os.path.join(HERE, "predefined.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("Wrote predefined.json (template not found yet)" )
    sys.exit(0)

with open(TEMPLATE, encoding="utf-8") as f:
    tpl = f.read()
payload = json.dumps(data, ensure_ascii=False)
needle = "/*__PREDEFINED_DATA__*/ null"
assert needle in tpl, "placeholder not found in template"
tpl = tpl.replace(needle, payload)
os.makedirs(OUT_DIR, exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(tpl)
print("Wrote", OUT, "(%d bytes)" % len(tpl))
