// Спрощений вигляд Fava: зрозумілі назви замість бухгалтерських і англійських.
// app.py додає цей файл на кожну сторінку разом зі списком доступних обліків.
(() => {
  const MENU = {
    "/income_statement/": "Доходи і витрати",
    "/balance_sheet/": "Гроші на рахунках",
  };
  // Сторінки-виписки, на які ведуть пункти меню: [куди веде, назва, підпис стовпців за період].
  // У спільному обліку власних грошей немає: «Усі операції» там — усі спільні покупки,
  // хто скільки вніс видно в «Доходи і витрати», а пункт «Гроші на рахунках» ховаємо.
  const SHARED = "спільне";
  const STATEMENTS = {
    personal: { "/journal/": ["account/Assets", "Усі операції", "Прихід мінус витрати", "Залишок"] },
    shared: { "/journal/": ["account/Expenses", "Усі операції", "Витрати за період", "Разом з початку"] },
  };
  // У спільному обліку «Доходи і витрати» і «Гроші на рахунках» розраховані на особистий бюджет,
  // якого там немає. Замість них працює розширення fava_shared, і свій пункт меню воно додає саме.
  const SHARED_HIDDEN = ["/income_statement/", "/balance_sheet/"];
  const BAR_LABELS = ["Зміни", "Прихід мінус витрати", "Витрати за період"];

  // Міняємо текст у наявному текстовому вузлі: якщо замінити сам вузол, Fava перестане його оновлювати.
  function setText(el, text) {
    const node = [...el.childNodes].find((n) => n.nodeType === 3 && n.data.trim());
    if (node) { if (node.data.trim() !== text) node.data = text; } else el.textContent = text;
  }
  const TITLE = {
    "Доходний звіт": "Доходи і витрати",
    "Баланс": "Гроші на рахунках",
    "Журнал": "Усі операції",
  };
  const TEXT = {
    "Stacked Bars": "По категоріях",  // стовпці з кольоровими частинами: кожна категорія окремо
    "Single Bars": "Підсумок",  // один стовпець за місяць: чистий результат
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
  const allowed = window.TRACKER_LEDGERS || [];
  const own = allowed.find((l) => l !== SHARED) || allowed[0];

  // Нижнє меню на телефоні, як у банківських застосунках: [значок, назва, посилання, сторінка].
  // У спільному обліку «+» веде в особистий облік: готівку записуємо у свій *-manual.beancount.
  const base = (ledger) => "/" + encodeURIComponent(ledger) + "/";
  function tabs(ledger) {
    const here = base(ledger);
    const mine = base(own);
    if (ledger === SHARED) {
      return [
        ["📊", "Звіт", here + "extension/FavaReport/", "extension/FavaReport"],
        ["🧾", "Операції", here + "account/Expenses/", "account/Expenses"],
        ["+", "", mine + "extension/FavaReport/#add-transaction", ""],
        ["🤝", "Підсумки", here + "extension/SharedExpenses/", "extension/SharedExpenses"],
        ["👤", "Мій облік", mine + "extension/FavaReport/", ""],
      ];
    }
    return [
      ["📊", "Звіт", here + "extension/FavaReport/", "extension/FavaReport"],
      ["🧾", "Операції", here + "account/Assets/", "account/Assets"],
      ["+", "", "#add-transaction", ""],
      ["👛", "Рахунки", here + "balance_sheet/", "balance_sheet"],
      allowed.includes(SHARED) ? ["🤝", "Спільне", "/" + encodeURIComponent(SHARED) + "/extension/FavaReport/", ""] : null,
    ].filter(Boolean);
  }

  function tabbar(ledger, page) {
    let bar = document.querySelector("nav.tracker-tabbar");
    if (!bar) {
      bar = document.createElement("nav");
      bar.className = "tracker-tabbar";
      document.body.append(bar);
    }
    const items = tabs(ledger);
    const key = ledger + "|" + page;
    if (bar.dataset.key === key) return;
    bar.dataset.key = key;
    bar.replaceChildren(...items.map(([icon, label, href, target]) => {
      const a = document.createElement("a");
      a.href = href;
      if (!label) {
        a.className = "tracker-plus";
        a.textContent = "+";
        a.setAttribute("aria-label", "Додати витрату");
        // На своїй сторінці відкриваємо те саме вікно, що й кнопка «Додати витрату» в меню.
        a.addEventListener("click", (ev) => {
          const add = href.startsWith("#") && document.querySelector("aside a.add-transaction");
          ev.preventDefault();
          if (add) add.click(); else location.assign(href);
        });
        return a;
      }
      if (target && target === page) a.className = "on";
      // Fava відкриває посилання всередині поточного обліку; інший облік завантажуємо повністю.
      if (!href.startsWith(base(ledger))) a.addEventListener("click", (ev) => { ev.preventDefault(); location.assign(href); });
      const i = document.createElement("i");
      i.textContent = icon;
      a.append(i, label);
      return a;
    }));
  }

  function fix() {
    // Клас сторінки на <html>, щоб simple.css міг ховати зайве лише там, де треба.
    const page = decodeURIComponent(location.pathname).split("/").slice(2).join("/").replace(/\/$/, "");
    const cls = "tracker-page-" + page.replace(/[^a-z_]/gi, "-");
    if (!document.documentElement.classList.contains(cls)) {
      document.documentElement.className = document.documentElement.className
        .split(" ").filter((c) => !c.startsWith("tracker-page-")).concat(cls).join(" ");
    }
    const ledger = decodeURIComponent(location.pathname.split("/")[1] || "");
    if (ledger && allowed.includes(ledger)) tabbar(ledger, page);
    const statements = STATEMENTS[ledger === SHARED ? "shared" : "personal"];
    const labels = { ...MENU };
    for (const [target, label] of Object.values(statements)) labels["/" + target + "/"] = label;
    const current = Object.values(statements).find(([target]) => target === page);
    document.documentElement.classList.toggle("tracker-statement", Boolean(current));
    document.documentElement.classList.toggle("tracker-shared", ledger === SHARED);
    if (ledger === SHARED) {
      for (const page of SHARED_HIDDEN) {
        for (const a of document.querySelectorAll(`aside a[href*="${page}"]`)) {
          a.closest("li").classList.add("tracker-hidden");
        }
      }
    }

    // Пункти меню ведуть на виписки. Fava дописує до посилань фільтри (?interval=day, ?time=...),
    // тому шукаємо «/journal/» у будь-якому місці посилання.
    for (const [from, [target]] of Object.entries(statements)) {
      for (const a of document.querySelectorAll(`aside a[href*="${from}"]`)) {
        a.setAttribute("href", a.getAttribute("href").replace(from, "/" + target + "/"));
      }
    }
    const title = document.querySelector("header h1 strong");
    if (title) {
      const want = current ? current[1] : TITLE[title.textContent.trim()];
      // Заголовок малює Fava, тому текст не міняємо, а показуємо свій поверх (див. simple.css).
      if (want && title.dataset.trackerTitle !== want) {
        if (!title.dataset.trackerTitle) title.style.setProperty("--tracker-fs", getComputedStyle(title).fontSize);
        title.dataset.trackerTitle = want;
      } else if (!want && title.dataset.trackerTitle) {
        delete title.dataset.trackerTitle;
      }
    }
    for (const a of document.querySelectorAll("aside a[href]")) {
      const path = decodeURIComponent(a.getAttribute("href").split("?")[0]);
      const key = Object.keys(labels).find((k) => path.endsWith(k));
      const node = a.firstChild;
      if (key && node && node.nodeType === 3 && node.data.trim() !== labels[key]) node.data = labels[key];
      // Підсвічуємо пункт поточної виписки (Fava сам підсвітив би «Баланс»).
      a.classList.toggle("tracker-current", Boolean(current) && path.endsWith("/" + page + "/"));
    }
    const add = document.querySelector("aside a.add-transaction");
    if (add) setText(add, "+ Додати витрату");

    // Назви в заголовку, кнопках і шапках таблиць; назви рахунків не чіпаємо.
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let n = walker.nextNode(); n; n = walker.nextNode()) {
      const t = n.data.trim();
      if (!(t in TEXT) || n.parentElement.closest("a.account")) continue;
      n.data = n.data.replace(t, TEXT[t]);
    }
    // Виписка: лінія залишку завжди йде по днях і не реагує на «Щоденно / Щомісячно».
    // Тому показуємо стовпці за період, а лінію й графіки окремих місяців ховаємо.
    if (current) {
      const [, , bars, total] = current;
      const head = document.querySelector("ol.journal li.head p > .num:last-child");
      if (head) setText(head, total);
      for (const b of document.querySelectorAll("article button.unset")) {
        const t = b.textContent.trim();
        if (t === "Залишок" || t === "Account Balance" || /^\d{4}(-|$)/.test(t)) b.classList.add("tracker-hidden");
        if (BAR_LABELS.includes(t) && !b.classList.contains("selected")) b.click();
        if (BAR_LABELS.includes(t)) setText(b, bars);
      }
      // Заголовки таблиць: «Зміни (щомісячно)», «Баланс (щомісячно)»; дужки з періодом лишаються.
      for (const h of document.querySelectorAll("article .headerline h3, article .headerline h3 a")) {
        const node = h.firstChild;
        if (!node || node.nodeType !== 3) continue;
        for (const [from, to] of [...BAR_LABELS.map((l) => [l + " (", bars + " ("]), ["Баланс (", total + " ("]]) {
          if (node.data.startsWith(from) && from !== to) node.data = to + node.data.slice(from.length);
        }
      }
    }
    // Позначки «хто заплатив» у спільному обліку: Оля фіолетова, Марко бірюзовий (як на «Спільні витрати»).
    for (const el of document.querySelectorAll("ol.journal .payee")) {
      el.classList.toggle("tracker-marko", el.textContent.trim() === "Марко");
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
