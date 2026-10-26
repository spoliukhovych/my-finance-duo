// Спрощений вигляд Fava: зрозумілі назви замість бухгалтерських і англійських.
// app.py додає цей файл на кожну сторінку разом зі списком доступних обліків.
(() => {
  const MENU = {
    "/income_statement/": "Доходи і витрати",
    "/balance_sheet/": "Гроші на рахунках",
    "/journal/": "Усі операції",
    "/account/Assets/": "Усі операції",
  };
  const TITLE = {
    "Доходний звіт": "Доходи і витрати",
    "Баланс": "Гроші на рахунках",
    "Журнал": "Усі операції",
  };
  const TEXT = {
    "Stacked Bars": "Разом",
    "Single Bars": "Окремо",
    "Income": "Доходи",
    "Expenses": "Витрати",
    "Liabilities": "Борги",
    "Equity": "Початковий залишок",
    "Converted to PLN": "У злотих",
    "Одиниці": "Сума",
    "Отримувач/Опис": "Опис",
    "Net Worth": "Усього",
    "Assets": "Рахунки",
    "Account Balance": "Залишок",
    "Журнал Рахунку": "Операції",
    "Вартість / Зміна": "Сума",
    "Ціна / Баланс": "Залишок",
    "continue": "додати ще одну",
  };
  const PLACEHOLDER = {
    "Filter by tag, payee, …": "Пошук: магазин або тег",
    "Час": "Період, напр. 2026-09",
  };
  // Вікно «+»: підказки, що писати в кожне поле.
  const DIALOG_PLACEHOLDER = {
    "Отримувач": "Де (магазин, кафе)",
    "Опис": "Що купили",
    "Рахунок": "Категорія, напр. Expenses:Кафе",
  };
  const HINT = "Перший рядок: категорія (Expenses:Кафе) і сума. Другий рядок: звідки гроші, " +
    "Assets:Готівка, суму можна не писати.";
  // Початок підпису → зрозуміліший (дужки з періодом лишаються: «(щомісячно)», «(щоденно)»).
  const PREFIX = [["Зміни (", "Прихід мінус витрати ("], ["Баланс (", "Залишок ("]];
  const allowed = window.TRACKER_LEDGERS || [];

  function fix() {
    // Клас сторінки на <html>, щоб simple.css міг ховати зайве лише там, де треба.
    const page = decodeURIComponent(location.pathname).split("/").slice(2).join("/").replace(/\/$/, "");
    const cls = "tracker-page-" + page.replace(/[^a-z_]/gi, "-");
    if (!document.documentElement.classList.contains(cls)) {
      document.documentElement.className = document.documentElement.className
        .split(" ").filter((c) => !c.startsWith("tracker-page-")).concat(cls).join(" ");
    }
    // «Усі операції» ведуть на виписку всіх рахунків (банк і готівка) із сумою та залишком.
    // Fava дописує до посилань фільтри (?interval=day, ?time=...), тому шукаємо «/journal/» у будь-якому місці.
    for (const a of document.querySelectorAll('aside a[href*="/journal/"]')) {
      a.setAttribute("href", a.getAttribute("href").replace("/journal/", "/account/Assets/"));
    }
    const title = document.querySelector("header h1 strong");
    if (title) {
      const want = page === "account/Assets" ? "Усі операції" : TITLE[title.textContent.trim()];
      if (want && title.textContent !== want) title.textContent = want;
    }
    for (const a of document.querySelectorAll("aside a[href]")) {
      const path = decodeURIComponent(a.getAttribute("href").split("?")[0]);
      const key = Object.keys(MENU).find((k) => path.endsWith(k));
      const node = a.firstChild;
      if (key && node && node.nodeType === 3 && node.data.trim() !== MENU[key]) node.data = MENU[key];
    }
    const add = document.querySelector("aside a.add-transaction");
    if (add && add.textContent !== "+ Додати витрату") add.textContent = "+ Додати витрату";

    // Назви в заголовку, кнопках і шапках таблиць; назви рахунків не чіпаємо.
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let n = walker.nextNode(); n; n = walker.nextNode()) {
      const t = n.data.trim();
      if (!(t in TEXT) || n.parentElement.closest("a.account")) continue;
      n.data = n.data.replace(t, TEXT[t]);
    }
    // Графіки боргів і капіталу нам не потрібні: боргів немає, капітал лише бухгалтерський.
    for (const b of document.querySelectorAll("article button.unset")) {
      if (["Борги", "Початковий залишок"].includes(b.textContent.trim())) b.classList.add("tracker-hidden");
    }
    for (const input of document.querySelectorAll("input[placeholder]")) {
      const p = (input.closest("dialog") ? DIALOG_PLACEHOLDER : PLACEHOLDER)[input.placeholder];
      if (p) input.placeholder = p;
    }
    const form = document.querySelector("dialog form");
    const submit = form && form.querySelector('button[type="submit"]');
    if (submit && !form.querySelector(".tracker-hint")) {
      const hint = document.createElement("p");
      hint.className = "tracker-hint";
      hint.textContent = HINT;
      submit.parentElement.before(hint);
    }
    // Вибір «За вартістю / Одиниці / За ринковою вартістю» потрібен лише для кількох валют.
    for (const li of document.querySelectorAll('ul[role="listbox"] li')) {
      if (li.textContent.trim() === "За ринковою вартістю") li.closest("ul").parentElement.classList.add("tracker-hidden");
    }
    // У перемикачі обліків лишаємо тільки ті, які цій людині дозволено відкривати.
    for (const a of document.querySelectorAll(".beancount-files a[href]")) {
      const slug = decodeURIComponent(a.getAttribute("href").split("/")[1] || "");
      if (!allowed.includes(slug)) a.closest("li").classList.add("tracker-hidden");
    }
    // Заголовки таблиць на сторінці «Усі операції»: «Зміни (щомісячно)», «Баланс (щомісячно)».
    for (const h of document.querySelectorAll("article .headerline h3, article .headerline h3 a")) {
      const node = h.firstChild;
      if (!node || node.nodeType !== 3) continue;
      for (const [from, to] of PREFIX) {
        if (node.data.startsWith(from)) node.data = to + node.data.slice(from.length);
      }
    }
    for (const [from, to] of Object.entries(TITLE)) {
      if (document.title.startsWith(from + " ")) document.title = document.title.replace(from, to);
    }
  }

  let queued = false;
  new MutationObserver(() => {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => { queued = false; fix(); });
  }).observe(document.documentElement, {
    childList: true, subtree: true, characterData: true,
    attributes: true, attributeFilter: ["href", "placeholder"],  // Fava оновлює посилання при зміні фільтрів
  });
  fix();
})();
