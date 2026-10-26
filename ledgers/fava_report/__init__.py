"""Розширення Fava «Звіт за місяць»: три питання PRD на одному екрані телефона.

1. Скільки йде на кожну категорію витрат.
2. Норма заощаджень = (дохід − витрати) / дохід.
3. Фіксовані (тег #fixed) і змінні витрати.
У спільному обліку замість цього показує, хто кому винен.
"""
from collections import defaultdict
from decimal import Decimal

from beancount.core.data import Transaction
from fava.ext import FavaExtensionBase

MONTHS = ["", "січень", "лютий", "березень", "квітень", "травень", "червень", "липень",
          "серпень", "вересень", "жовтень", "листопад", "грудень"]


def money(value):
    return f"{value:,.2f}".replace(",", " ").replace(".", ",")


class FavaReport(FavaExtensionBase):
    report_title = "Звіт за місяць"

    def _transactions(self):
        return [e for e in self.ledger.all_entries if isinstance(e, Transaction)]

    def months(self):
        found = {(e.date.year, e.date.month) for e in self._transactions()
                 if any(p.account.startswith(("Expenses:", "Income:")) for p in e.postings)}
        return [f"{y}-{m:02d}" for y, m in sorted(found, reverse=True)]

    def is_shared(self):
        return any(e.account.startswith("Income:Заплатив:") for e in self.ledger.all_entries
                   if hasattr(e, "account"))

    def report(self, month):
        months = self.months()
        if not months:
            return None
        if month not in months:
            month = months[0]
        year, mon = map(int, month.split("-"))
        txns = [e for e in self._transactions() if (e.date.year, e.date.month) == (year, mon)]
        last_date = max((e.date for e in txns), default=None)
        categories = defaultdict(Decimal)
        income = expenses = fixed = Decimal(0)
        paid = defaultdict(Decimal)
        for e in txns:
            for p in e.postings:
                n = p.units.number
                if p.account.startswith("Expenses:"):
                    categories[p.account.split(":", 1)[1].replace("-", " ")] += n
                    expenses += n
                    if "fixed" in e.tags:
                        fixed += n
                elif p.account.startswith("Income:Заплатив:"):  # спільний облік: хто скільки вніс
                    paid[p.account.rsplit(":", 1)[1]] -= n
                elif p.account.startswith("Income:"):
                    income -= n
        saved = income - expenses
        rate = (saved / income * 100) if income else None
        cats = sorted(categories.items(), key=lambda kv: kv[1], reverse=True)
        top = cats[0][1] if cats else Decimal(1)
        debt = (paid["Оля"] - paid["Марко"]) / 2
        return {
            "month": month,
            "title": f"{MONTHS[mon]} {year}",
            "incomplete": last_date is not None and last_date.day < 28 and month == months[0],
            "last_date": last_date.strftime("%d.%m") if last_date else "",
            "categories": [(name, money(v), int(v / top * 100) if top else 0) for name, v in cats],
            "income": money(income), "expenses": money(expenses), "saved": money(saved),
            "rate": f"{rate:.1f}".replace(".", ",") if rate is not None else "дохід ще не надійшов",
            "has_income": rate is not None,
            "fixed": money(fixed), "variable": money(expenses - fixed),
            "fixed_pct": int(fixed / expenses * 100) if expenses else 0,
            "paid_olya": money(paid["Оля"]), "paid_marko": money(paid["Марко"]),
            "debt": money(abs(debt)),
            "debtor": "Марко винен Олі" if debt > 0 else "Оля винна Марку",
        }
