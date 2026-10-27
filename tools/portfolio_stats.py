#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Обновляет цифры в портфолио из живых источников.

Читает, ничего не меняя:
  • afisha.db СПРУТа — строго на чтение (mode=ro), живой WAL не трогается
  • /srv/marki/catalog.json — сводка каталога марок и монет

Меняет только тексты в index.html, resume.html и README.md портфолио.

    portfolio_stats.py                    показать, что изменится (сухой прогон)
    portfolio_stats.py --write            записать
    portfolio_stats.py --write --deploy   записать и выложить на сервер
"""

import argparse
import json
import os
import re
import sqlite3
import subprocess

DB = '/home/shuni/projects/afisha-spb/data/afisha.db'
CATALOG = '/srv/marki/catalog.json'
SITE = '/home/shuni/projects/portfolio'
SRV = '/srv/me'

# число с разделителями тысяч: '9 136', '10 135' или просто '565'.
# Строгий шаблон: иначе жадный \d[\d ]* съедает соседние числа в строке.
NUM = r'(?:\d{1,3}(?:[ \u00a0\u2009]\d{3})+|\d+)'


def fmt(n):
    return f'{n:,}'.replace(',', ' ')


def is_one(n):
    """Одна единица: 1, 21, 141 — но не 11."""
    n = abs(n) % 100
    return n % 10 == 1 and n != 11


def is_few(n):
    """2-4 для именительного падежа: 2 предмета."""
    n = abs(n) % 100
    return 2 <= n % 10 <= 4 and not 11 <= n <= 14


def pick(n, one, few, many):
    return one if is_one(n) else (few if is_few(n) else many)


def spurt():
    """Считает метрики СПРУТа. База открывается строго на чтение."""
    if not os.path.exists(DB):
        raise SystemExit(f'нет базы: {DB}')
    con = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
    try:
        cur = con.cursor()
        q = lambda sql: cur.execute(sql).fetchone()[0]
        return {
            'events':   q('SELECT COUNT(*) FROM events'),
            'sources':  q('SELECT COUNT(*) FROM sources'),
            'venues':   q('SELECT COUNT(*) FROM venues'),
            'verified': q("SELECT COUNT(*) FROM events WHERE status = 'VERIFIED'"),
        }
    finally:
        con.close()


def stamps():
    """Берёт готовую сводку каталога."""
    if not os.path.exists(CATALOG):
        raise SystemExit(f'нет каталога: {CATALOG}')
    with open(CATALOG, encoding='utf-8') as f:
        d = json.load(f)
    return {
        'count':  d['count'],
        'stamps': d['stamps_count'],
        'coins':  d['coins_count'],
        'value':  d['total_value_rub'],
        'photos': d.get('with_photo') or d['count'],
    }


def rules(sm, st):
    """(файл, регулярка, замена) — что именно переписать."""
    # после «из» нужен родительный: из 141 источника / из 147 источников
    src_gen = 'источника' if is_one(sm['sources']) else 'источников'
    ven_gen = 'площадки' if is_one(sm['venues']) else 'площадок'
    # именительный для названий
    src_nom = pick(sm['sources'], 'источник', 'источника', 'источников')
    ven_nom = pick(sm['venues'], 'площадка', 'площадки', 'площадок')
    items = pick(st['count'], 'предмет', 'предмета', 'предметов')
    marks = pick(st['stamps'], 'марка', 'марки', 'марок')
    coins = pick(st['coins'], 'монета', 'монеты', 'монет')

    sput_fact = (f"{fmt(sm['events'])} событий из {fmt(sm['sources'])} {src_gen} "
                 f"и {fmt(sm['venues'])} {ven_gen}, "
                 f"{fmt(sm['verified'])} подтверждены полностью")

    return [
        # index.html — карточка СПРУТа и реплика скрепыша
        ('index.html',
         rf"'{NUM} событий из {NUM} источник\w* и {NUM} площадок, {NUM} подтверждены полностью'",
         f"'{sput_fact}'"),
        ('index.html',
         rf"'{NUM} событий, и ни одно не выдумано\.",
         f"'{fmt(sm['events'])} событий, и ни одно не выдумано."),
        # index.html — каталог
        ('index.html',
         rf"Каталог марок и монет: {NUM} предмета?",
         f"Каталог марок и монет: {fmt(st['count'])} {items}"),
        ('index.html',
         rf"'{NUM} предмета?: {NUM} марок и {NUM} монеты?, все с фотографиями'",
         f"'{fmt(st['count'])} {items}: {fmt(st['stamps'])} {marks} "
         f"и {fmt(st['coins'])} {coins}, все с фотографиями'"),
        ('index.html',
         rf"'{NUM} ₽ по каталогу, каждая цена привязана",
         f"'{fmt(st['value'])} ₽ по каталогу, каждая цена привязана"),
        ('index.html',
         rf"'{NUM} предмета?\. У меня одна скрепка",
         f"'{fmt(st['count'])} {items}. У меня одна скрепка"),
        # resume.html
        ('resume.html',
         rf"<b>{NUM} событий · {NUM} источник\w* · {NUM} площадк\w*</b>",
         f"<b>{fmt(sm['events'])} событий · {fmt(sm['sources'])} {src_nom} · "
         f"{fmt(sm['venues'])} {ven_nom}</b>"),
        ('resume.html',
         rf"<b>{NUM} предмет\w* \({NUM} марок и {NUM} монет\w*\) · {NUM} ₽ по каталогу · ({NUM}) фото</b>",
         # число фото не пересчитываем: их считают в проекте каталога, а не здесь
         lambda m: (f"<b>{fmt(st['count'])} {items} "
                    f"({fmt(st['stamps'])} {marks} и {fmt(st['coins'])} {coins}) · "
                    f"{fmt(st['value'])} ₽ по каталогу · {m.group(1)} фото</b>")),
        # README.md
        ('README.md',
         rf"{NUM} событий и {NUM} источник\w*",
         f"{fmt(sm['events'])} событий и {fmt(sm['sources'])} {src_gen}"),
        ('README.md',
         rf"{NUM} предмет\w* в каталоге марок",
         f"{fmt(st['count'])} {items} в каталоге марок"),
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true', help='записать изменения')
    ap.add_argument('--deploy', action='store_true', help='выложить на сервер')
    args = ap.parse_args()

    sm, st = spurt(), stamps()
    print(f"СПРУТ:   {fmt(sm['events'])} событий, {fmt(sm['sources'])} источников, "
          f"{fmt(sm['venues'])} площадок, {fmt(sm['verified'])} VERIFIED")
    print(f"Каталог: {fmt(st['count'])} {pick(st['count'], 'предмет', 'предмета', 'предметов')} "
          f"({fmt(st['stamps'])} {pick(st['stamps'], 'марка', 'марки', 'марок')} + "
          f"{fmt(st['coins'])} {pick(st['coins'], 'монета', 'монеты', 'монет')}), "
          f"{fmt(st['value'])} ₽")
    print()

    changed = set()
    changes = 0

    for fname, pattern, repl in rules(sm, st):
        path = os.path.join(SITE, fname)
        if not os.path.exists(path):
            print(f'ПРОПУСК: нет {fname}')
            continue
        text = open(path, encoding='utf-8').read()
        if not re.search(pattern, text):
            print(f'НЕ НАЙДЕНО в {fname}: {pattern[:70]}')
            continue

        new_text = re.sub(pattern, repl if callable(repl) else (lambda m: repl), text)
        if new_text == text:
            continue

        for m in re.finditer(pattern, text):
            shown = repl(m) if callable(repl) else repl
            print(f'{fname}: {m.group(0)[:95]}')
            print(f'     → {shown[:95]}')
            changes += 1

        changed.add(fname)
        if args.write:
            open(path, 'w', encoding='utf-8').write(new_text)

    print()
    if not changes:
        print('Цифры актуальны, менять нечего.')
    elif args.write:
        print(f'Записано: {", ".join(sorted(changed))}')
    else:
        print(f'Расхождений: {changes}. Сухой прогон — для записи добавь --write')

    if args.write and args.deploy:
        md5 = lambda p: subprocess.run(['sudo', 'md5sum', p], capture_output=True,
                                       text=True).stdout.split()[0] if os.path.exists(p) else None
        # сверяем все файлы из правил: на сервере мог остаться прошлый прогон
        for f in sorted({f for f, _, _ in rules(sm, st)}):
            src = os.path.join(SITE, f)
            dst = os.path.join(SRV, f)
            if not os.path.exists(dst):
                print(f'  на сервере нет {dst}')
                continue
            local, remote = md5(src), md5(dst)
            if local == remote:
                print(f'  {f}: уже актуален')
                continue
            subprocess.run(['sudo', 'cp', src, dst], check=True)
            print(f'  {f}: выложен, {"✓ совпадает" if md5(src) == md5(dst) else "✗ расходится"}')
        # резюме живёт ещё и в PDF — его надо пересобрать, иначе цифры разъедутся
        if 'resume.html' in changed:
            node_env = dict(os.environ, NODE_PATH='/home/shuni/projects/gaslight_app/node_modules')
            build = subprocess.run(['node', 'mkpdf.js'], cwd=SITE, env=node_env,
                                   capture_output=True, text=True)
            pdf = os.path.join(SITE, 'assets/CV_Oleg_Sparber.pdf')
            if build.returncode == 0 and os.path.exists(pdf):
                dst = os.path.join(SRV, 'assets/CV_Oleg_Sparber.pdf')
                subprocess.run(['sudo', 'cp', pdf, dst], check=False)
                print(f'  CV PDF пересобран и выложен '
                      f'({"✓ совпадает" if md5(pdf) == md5(dst) else "✗ проверь вручную"})')
            else:
                print('  CV PDF НЕ пересобран:', (build.stderr or '').strip()[:200])

        subprocess.run(['sudo', 'chown', '-R', 'caddy:caddy', SRV], check=False)
        print('Сервер синхронизирован.')


if __name__ == '__main__':
    main()
