"""Розширення Fava «Спільні витрати»: усі місяці спільного обліку на одному екрані.

Замінює сторінку «Доходи і витрати», яка розрахована на особистий бюджет:
у спільного котла доходу немає, є лише внески Олі й Марка (Income:Заплатив:<імʼя>).

1. Хто скільки вніс за кожен місяць і хто кому винен.
2. Витрати за категоріями по місяцях.
"""
from collections import defaultdict
from decimal import Decimal

from beancount.core.data import Transaction
from fava.ext import FavaExtensionBase

MONTHS = ["", "січень", "лютий", "березень", "квітень", "травень", "червень", "липень",
          "серпень", "вересень", "жовтень", "листопад", "грудень"]


def money(value):
    return f"{value:,.2f}".replace(",", " ").replace(".", ",")


class SharedExpenses(FavaExtensionBase):
    report_title = "Спільні витрати"

    def report(self):
        paid = defaultdict(lambda: defaultdict(Decimal))   # місяць → хто → скільки вніс
        spent = defaultdict(lambda: defaultdict(Decimal))  # місяць → категорія → скільки
        for e in self.ledger.all_entries:
            if not isinstance(e, Transaction):
                continue
            ym = (e.date.year, e.date.month)
            for p in e.postings:
                if p.account.startswith("Income:Заплатив:"):
                    paid[ym][p.account.rsplit(":", 1)[1]] -= p.units.number
                elif p.account.startswith("Expenses:"):
                    spent[ym][p.account.split(":", 1)[1].replace("-", " ")] += p.units.number
        if not paid:
            return None

        months = sorted(paid, reverse=True)
        rows, totals = [], defaultdict(Decimal)
        for ym in months:
            olya, marko = paid[ym]["Оля"], paid[ym]["Марко"]
            debt = (olya - marko) / 2
            total = sum(spent[ym].values())
            totals["Оля"] += olya
            totals["Марко"] += marko
            totals["разом"] += total
            rows.append({
                "key": f"{ym[0]}-{ym[1]:02d}",
                "title": f"{MONTHS[ym[1]].capitalize()} {ym[0]}",
                "olya": money(olya), "marko": money(marko), "total": money(total),
                "half": money(total / 2),
                "debt": money(abs(debt)),
                "debtor": "Марко винен Олі" if debt > 0 else "Оля винна Марку" if debt else "ніхто нікому",
                "olya_pct": int(olya / total * 100) if total else 0,
            })

        names = sorted({c for m in spent.values() for c in m},
                       key=lambda c: -sum(spent[ym][c] for ym in months))
        categories = [{
            "name": name,
            "amounts": [money(spent[ym][name]) if spent[ym][name] else "" for ym in months],
            "total": money(sum(spent[ym][name] for ym in months)),
        } for name in names]

        return {
            "rows": rows,
            "months": [r["title"] for r in rows],
            "categories": categories,
            "total_olya": money(totals["Оля"]), "total_marko": money(totals["Марко"]),
            "olya_short": f"{totals['Оля']:,.0f}".replace(",", " "),
            "marko_short": f"{totals['Марко']:,.0f}".replace(",", " "),
            "total_all": money(totals["разом"]),
        }
