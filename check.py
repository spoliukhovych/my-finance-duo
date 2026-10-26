"""Одна команда перевірки: імпорт, bean-check і контрольні цифри Олі й Марка.

Запуск: uv run check.py
Код виходу 0 — усе зійшлося, 1 — є помилка.
"""
import subprocess
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from beancount import loader
from beancount.core.data import Transaction

import importer

ROOT = Path(__file__).parent
LEDGERS = ["olya", "marko", "spilne"]
CONTROL = {  # змінні витрати з умови задання
    "olya": {(2026, 8): Decimal("2195.21"), (2026, 9): Decimal("2582.42")},
    "marko": {(2026, 8): Decimal("1855.57"), (2026, 9): Decimal("2432.83")},
}
NAMES = {"olya": "Оля", "marko": "Марко"}


def load(name):
    entries, errors, _ = loader.load_file(str(ROOT / "ledgers" / f"{name}.beancount"))
    return entries, errors


def monthly(entries):
    """Змінні витрати, фіксовані, дохід і витрати по місяцях."""
    out = defaultdict(lambda: defaultdict(Decimal))
    for e in entries:
        if not isinstance(e, Transaction):
            continue
        ym = (e.date.year, e.date.month)
        for p in e.postings:
            if p.account.startswith("Expenses:"):
                kind = "fixed" if "fixed" in e.tags else "variable"
                out[ym][kind] += p.units.number
                out[ym]["expenses"] += p.units.number
            elif p.account.startswith("Income:"):
                out[ym]["income"] -= p.units.number
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ok = True
    importer.main()

    print("\n1. bean-check")
    for name in LEDGERS:
        result = subprocess.run([sys.executable, "-m", "beancount.scripts.check",
                                 str(ROOT / "ledgers" / f"{name}.beancount")],
                                capture_output=True, text=True)
        output = (result.stdout + result.stderr).strip()
        if result.returncode != 0 or output:
            ok = False
            print(f"   {name}.beancount: ПОМИЛКА\n{output}")
        else:
            print(f"   {name}.beancount: без повідомлень")

    print("\n2. Контрольні цифри: змінні витрати, зл")
    for name, expected in CONTROL.items():
        entries, _ = load(name)
        data = monthly(entries)
        for ym, value in expected.items():
            got = data[ym]["variable"]
            mark = "збігається" if got == value else f"НЕ збігається (очікували {value})"
            ok &= got == value
            print(f"   {NAMES[name]:<6} {ym[1]:02d}.{ym[0]}: {got:>9}  {mark}")

    print("\n3. Хто кому винен за спільне (оренда, Kaufland, Auchan, світло, інтернет)")
    entries, _ = load("spilne")
    paid = defaultdict(lambda: defaultdict(Decimal))
    for e in entries:
        if isinstance(e, Transaction):
            for p in e.postings:
                if p.account.startswith("Assets:Заплатив:"):
                    paid[(e.date.year, e.date.month)][p.account.rsplit(":", 1)[1]] -= p.units.number
    for ym in sorted(paid):
        olya, marko = paid[ym]["Оля"], paid[ym]["Марко"]
        debt = (olya - marko) / 2
        who = f"Марко винен Олі {debt:.2f}" if debt > 0 else f"Оля винна Марку {-debt:.2f}"
        print(f"   {ym[1]:02d}.{ym[0]}: Оля заплатила {olya:.2f}, Марко {marko:.2f} → {who}")

    print("\nУСЕ ГАРАЗД" if ok else "\nЄ ПОМИЛКИ")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
