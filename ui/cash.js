// Вікно «Додати витрату» для готівки: магазин, опис (необовʼязково), категорія і сума.
// Замінює загальне вікно Fava «+», де треба було самому писати рахунки й другий рядок.
// Запис іде через той самий API Fava (api/add_entries) і потрапляє в <імʼя>-manual.beancount.
(() => {
  const SHARED = "спільне";
  const CASH = "Assets:Готівка";  // готівка: звідки гроші, завжди одне й те саме
  const SKIP = ["Expenses:Без-Категорії"];  // службова категорія імпорту, вручну не обирають
  // Значки як у «Звіт за місяць» (ledgers/fava_report/__init__.py, ICONS).
  const ICONS = {
    "Продукти": "🛒", "Доставка Їжі": "🛵", "Кафе": "☕", "Транспорт": "🚌", "Підписки": "📺",
    "Побут": "🧴", "Спорт": "🏋️", "Звязок": "📱", "Комунальні": "💡", "Покупки": "🛍️",
    "Розваги": "🎮", "Житло": "🏠", "Інше": "📦",
  };

  const ledger = () => decodeURIComponent(location.pathname.split("/")[1] || "");
  const title = (account) => account.split(":").slice(1).join(" ").replace(/-/g, " ");
  const clean = (text) => text.replace(/"/g, "").replace(/\s+/g, " ").trim();

  function categories() {
    let data = {};
    try { data = JSON.parse(document.getElementById("ledger-data").textContent); } catch { /* немає даних */ }
    const accounts = Array.isArray(data) ? data[0] : data.accounts || [];
    return accounts.filter((a) => a.startsWith("Expenses:") && a.split(":").length === 2 && !SKIP.includes(a))
      .sort((a, b) => title(a).localeCompare(title(b), "uk"));
  }

  function today() {
    const d = new Date();
    return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
  }

  function build() {
    const dlg = document.createElement("dialog");
    dlg.className = "tracker-cash";
    dlg.innerHTML = `
      <form method="dialog">
        <div class="tc-head"><h3>Додати витрату</h3><button type="button" class="tc-close" aria-label="Закрити">×</button></div>
        <p class="tc-sub">Готівкою: банківські операції підтягуються з виписки самі.</p>
        <label>Магазин<input name="shop" required autocomplete="off" placeholder="Напр. Biedronka"></label>
        <label><span>Опис <small>необовʼязково</small></span><input name="note" autocomplete="off" placeholder="Напр. продукти на вихідні"></label>
        <label>Категорія<select name="category" required><option value="">Оберіть категорію</option></select></label>
        <div class="tc-row">
          <label>Сума, зл<input name="amount" required inputmode="decimal" autocomplete="off" placeholder="0,00"></label>
          <label>Дата<input name="date" type="date" required></label>
        </div>
        <p class="tc-error" hidden></p>
        <button type="submit" class="tc-save">Зберегти</button>
      </form>`;
    const select = dlg.querySelector("select");
    for (const account of categories()) {
      const name = title(account);
      select.add(new Option(`${ICONS[name] || "💳"} ${name}`, account));
    }
    dlg.querySelector(".tc-close").addEventListener("click", () => dlg.close());
    dlg.addEventListener("click", (ev) => { if (ev.target === dlg) dlg.close(); });  // тап поза вікном
    dlg.querySelector("form").addEventListener("submit", (ev) => { ev.preventDefault(); save(dlg); });
    document.body.append(dlg);
    return dlg;
  }

  async function save(dlg) {
    const form = dlg.querySelector("form");
    const error = dlg.querySelector(".tc-error");
    const button = dlg.querySelector(".tc-save");
    const shop = clean(form.shop.value);
    const note = clean(form.note.value);
    const amount = Number(form.amount.value.replace(/\s/g, "").replace(",", "."));
    const show = (text) => { error.textContent = text; error.hidden = false; };
    if (!shop) return show("Напишіть магазин.");
    if (!form.category.value) return show("Оберіть категорію.");
    if (!(amount > 0)) return show("Сума має бути додатним числом, напр. 12,50.");
    const sum = amount.toFixed(2);
    const entry = {
      t: "Transaction", date: form.date.value, flag: "*", payee: "",
      // Опис у дужках після магазину: «Biedronka (продукти на вихідні)».
      narration: note ? `${shop} (${note})` : shop,
      tags: [], links: [], meta: {},
      postings: [
        { account: form.category.value, amount: `${sum} PLN` },
        { account: CASH, amount: `-${sum} PLN` },
      ],
    };
    button.disabled = true;
    try {
      const response = await fetch(`/${encodeURIComponent(ledger())}/api/add_entries`, {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ entries: [entry] }),
      });
      if (!response.ok) {
        let text = await response.text();
        try { text = JSON.parse(text).error || text; } catch { /* звичайний текст */ }
        throw new Error(text);
      }
      dlg.close();
      location.reload();  // звіт і список операцій одразу з новою витратою
    } catch (err) {
      show("Не вдалося зберегти: " + err.message);
    } finally {
      button.disabled = false;
    }
  }

  function open() {
    const dlg = document.querySelector("dialog.tracker-cash") || build();
    const form = dlg.querySelector("form");
    form.reset();
    form.date.value = today();
    dlg.querySelector(".tc-error").hidden = true;
    dlg.showModal();
    form.shop.focus();
  }

  // Кнопки «+» (нижнє меню на телефоні) і «+ Додати витрату» (меню збоку) відкривають це вікно.
  // Перехоплюємо клік раніше за Fava, щоб не відкрилося її загальне вікно.
  document.addEventListener("click", (ev) => {
    const link = ev.target instanceof Element && ev.target.closest("a.tracker-plus, aside a.add-transaction");
    if (!link || ledger() === SHARED) return;
    ev.preventDefault();
    ev.stopPropagation();
    open();
  }, true);
})();
