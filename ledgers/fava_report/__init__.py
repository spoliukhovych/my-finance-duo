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
IN_MONTH = ["", "у січні", "у лютому", "у березні", "у квітні", "у травні", "у червні", "у липні",
            "у серпні", "у вересні", "у жовтні", "у листопаді", "у грудні"]
SHORT = ["", "січ", "лют", "бер", "кві", "тра", "чер", "лип", "сер", "вер", "жов", "лис", "гру"]
# Значок біля категорії у списках, як у банківських застосунках.
ICONS = {"Продукти": "🛒", "Доставка Їжі": "🛵", "Кафе": "☕", "Транспорт": "🚌", "Підписки": "📺",
         "Побут": "🧴", "Спорт": "🏋️", "Звязок": "📱", "Комунальні": "💡", "Покупки": "🛍️",
         "Розваги": "🎮", "Житло": "🏠", "Інше": "📦", "Без Категорії": "❔", "Зарплата": "💼"}
RECENT = 5  # скільки останніх операцій показувати


def money(value):
    return f"{value:,.2f}".replace(",", " ").replace(".", ",")


def short(value):
    """Ціле число для маленьких карток: 4709,28 → «4 709»."""
    return f"{value:,.0f}".replace(",", " ").replace("-", "−")


def category(account):
    """Expenses:Доставка-Їжі → «Доставка Їжі»."""
    return account.split(":", 1)[1].replace("-", " ")


def nice(text):
    """Банк пише великими літерами: «KAUFLAND WARSZAWA» → «Kaufland Warszawa»."""
    return text.title() if text.isupper() else text


def operation(e, shared):
    """Рядок «Останні операції»: значок, назва, дата з категорією, сума зі знаком."""
    spent = [p for p in e.postings if p.account.startswith("Expenses:")]
    earned = [p for p in e.postings if p.account.startswith("Income:") and not p.account.startswith("Income:Заплатив:")]
    name = category(spent[0].account) if spent else category(earned[0].account) if earned else ""
    amount = sum((p.units.number for p in spent), Decimal(0)) or -sum((p.units.number for p in earned), Decimal(0))
    sign = "−" if spent else "+"
    title = e.narration if shared or not e.payee else e.payee
    return {
        "icon": ICONS.get(name, "💳"), "title": nice(title or name),
        "date": f"{e.date.day} {SHORT[e.date.month]}", "category": name,
        "amount": sign + money(amount), "plus": not spent,
        "who": e.payee if shared else "",
    }


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
                    categories[category(p.account)] += n
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
        shared = bool(paid)
        recent = sorted((e for e in txns if any(p.account.startswith(("Expenses:", "Income:")) for p in e.postings)),
                        key=lambda e: e.date, reverse=True)[:RECENT]
        total = expenses or Decimal(1)
        return {
            "month": month,
            "title": f"{MONTHS[mon]} {year}",
            "in_month": IN_MONTH[mon],
            "pills": [(m, MONTHS[int(m[5:])].capitalize() + ("" if m[:4] == str(year) else " " + m[:4]))
                      for m in reversed(months)],
            "recent": [operation(e, shared) for e in recent],
            "incomplete": last_date is not None and last_date.day < 28 and month == months[0],
            "last_date": last_date.strftime("%d.%m") if last_date else "",
            # (значок, назва, сума, довжина смужки відносно найбільшої, частка від усіх витрат у %)
            "categories": [(ICONS.get(name, "💳"), name, money(v), int(v / top * 100) if top else 0,
                            round(v / total * 100)) for name, v in cats],
            "income": money(income), "expenses": money(expenses), "saved": money(saved),
            "half": money(expenses / 2),
            "rate": f"{rate:.1f}".replace(".", ",") if rate is not None else "дохід ще не надійшов",
            "has_income": rate is not None,
            "fixed": money(fixed), "variable": money(expenses - fixed),
            "fixed_pct": int(fixed / expenses * 100) if expenses else 0,
            "paid_olya": money(paid["Оля"]), "paid_marko": money(paid["Марко"]),
            "debt": money(abs(debt)), "debt_short": short(abs(debt)),
            "debtor": "Марко винен Олі" if debt > 0 else "Оля винна Марку" if debt else "Ніхто нікому не винен",
            "saved_short": short(saved),
            "olya_short": short(paid["Оля"]), "marko_short": short(paid["Марко"]),
            "debtor_short": "Марко → Олі" if debt > 0 else "Оля → Марку" if debt else "нікому",
            "olya_pct": int(paid["Оля"] / total * 100) if paid else 0,
        }
