"""Збирає облік з виписок Олі й Марка.

Створює (повністю перезаписує):
  ledgers/olya-transactions.beancount   — операції з банку Олі
  ledgers/marko-transactions.beancount  — операції з банку Марка
  ledgers/spilne-transactions.beancount — спільні витрати обох (для «хто кому винен»)

Файли *-manual.beancount (витрати, додані з телефона) імпорт не чіпає.
Запуск: python importer.py
"""
import csv
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data"
LEDGERS = ROOT / "ledgers"


@dataclass
class Row:
    date: date
    description: str
    amount: Decimal
    balance: Decimal


@dataclass
class Person:
    key: str          # olya / marko
    name: str         # Оля / Марко
    statement: Path
    rules: Path
    bank: str
    reader: object


def read_olya(path):
    """Формат банку Олі: CSV з комами, Completed Date, порядок банку зверху вниз."""
    rows, seen = [], set()
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            if r["State"] != "COMPLETED":
                continue
            if Decimal(r["Fee"]) != 0:
                sys.exit(f"Комісія в рядку «{r['Description']}» не підтримується")
            key = (r["Completed Date"], r["Description"], r["Amount"], r["Balance"])
            if key in seen:
                continue
            seen.add(key)
            rows.append(Row(date.fromisoformat(r["Completed Date"][:10]), r["Description"].strip(),
                            Decimal(r["Amount"]), Decimal(r["Balance"])))
    return rows


def pl_number(text):
    return Decimal(text.replace(" ", "").replace(" ", "").replace(",", "."))


def read_marko(path):
    """Формат банку Марка: службові рядки, потім таблиця з «;», нові операції зверху.

    Місяць визначаємо за датою операції (Data operacji). Рядки повертаємо від найстаріших,
    щоб залишок ішов у порядку банку.
    """
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("Data operacji")) + 1
    rows = []
    for r in csv.reader(lines[start:], delimiter=";"):
        if not r:
            continue
        rows.append(Row(datetime.strptime(r[0], "%d.%m.%Y").date(), r[3].strip(),
                        pl_number(r[4]), pl_number(r[5])))
    rows.reverse()
    return rows


PEOPLE = [
    Person("olya", "Оля", DATA / "olya-statement.csv", ROOT / "rules-olya.csv", "Assets:Банк", read_olya),
    Person("marko", "Марко", DATA / "marko-statement.csv", ROOT / "rules-marko.csv", "Assets:Банк", read_marko),
]


def read_rules(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return [(r["шаблон"].strip().lower(), r["рахунок"].strip(),
                 r["фіксована"].strip().lower() == "так", r["спільна"].strip().lower() == "так")
                for r in csv.DictReader(f)]


def categorize(description, amount, rules):
    text = description.lower()
    for pattern, account, fixed, shared in rules:
        if pattern in text:
            return account, fixed, shared
    return ("Income:Інше" if amount > 0 else "Expenses:Без-Категорії"), False, False


def quote(text):
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def build(person):
    rules = read_rules(person.rules)
    rows = person.reader(person.statement)
    lines, shared = [], []
    for r in rows:
        account, fixed, is_shared = categorize(r.description, r.amount, rules)
        tags = (" #fixed" if fixed else "") + (" #shared" if is_shared else "")
        lines += [f"{r.date} * {quote(r.description)}{tags}",
                  f"  {person.bank}  {r.amount:.2f} PLN",
                  f"  {account}  {-r.amount:.2f} PLN", ""]
        if is_shared:
            shared.append((r, account, person))

    # Звірка з банком: залишок після останньої операції кожного місяця (у порядку банку).
    last = {}
    for r in rows:
        last[(r.date.year, r.date.month)] = r
    months = sorted(last)
    for ym in months:
        r = last[ym]
        if ym == months[-1]:
            check = max(x.date for x in rows) + timedelta(days=1)
        else:
            check = date(ym[0] + ym[1] // 12, ym[1] % 12 + 1, 1)
        lines.append(f"{check} balance {person.bank}  {r.balance:.2f} PLN")

    out = LEDGERS / f"{person.key}-transactions.beancount"
    out.write_text("; Згенеровано importer.py — не редагуйте вручну\n\n" + "\n".join(lines) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"{person.name}: {len(rows)} операцій → {out.name}")
    return shared


def build_shared(shared):
    lines = []
    for r, account, person in sorted(shared, key=lambda s: (s[0].date, s[2].key)):
        category = account.split(":", 1)[1]
        lines += [f"{r.date} * {quote(r.description)} #shared",
                  f"  Expenses:{category}  {-r.amount:.2f} PLN",
                  f"  Income:Заплатив:{person.name}  {r.amount:.2f} PLN", ""]
    out = LEDGERS / "spilne-transactions.beancount"
    out.write_text("; Згенеровано importer.py — не редагуйте вручну\n\n" + "\n".join(lines) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"Спільні: {len(shared)} операцій → {out.name}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    shared = []
    for person in PEOPLE:
        shared += build(person)
    build_shared(shared)


if __name__ == "__main__":
    main()
