(() => {
  "use strict";

  const chapters = Array.isArray(window.KEDUSHA_CHAPTERS) ? window.KEDUSHA_CHAPTERS : [];
  const grid = document.querySelector("#cards-grid");
  const count = document.querySelector("#result-count");
  const search = document.querySelector("#chapter-search");
  const contentModal = document.querySelector("#content-modal");
  const contentTitle = document.querySelector("#modal-title");
  const contentBody = document.querySelector("#modal-body");
  const cardModal = document.querySelector("#card-modal");
  const lightboxImage = document.querySelector("#lightbox-image");
  const lightboxTitle = document.querySelector("#lightbox-title");
  const lightboxNumber = document.querySelector("#lightbox-number");
  const lightboxDownload = document.querySelector("#lightbox-download");
  const toast = document.querySelector("#toast");
  let activeFilter = "all";
  let activeCard = null;
  let activeSide = "front";

  const escapeHtml = value => String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

  const normalize = value => String(value || "")
    .normalize("NFKD")
    .replace(/[\u0591-\u05C7]/g, "")
    .toLocaleLowerCase("he");

  function cardMarkup(chapter) {
    const number = String(chapter.n).padStart(2, "0");
    return `
      <article class="chapter-card" data-id="${chapter.n}">
        <div class="card-frame">
          <div class="card-tools">
            <button type="button" data-flip="${chapter.n}" aria-label="הפיכת קלף ${escapeHtml(chapter.title)}">↻</button>
            <button type="button" data-open="${chapter.n}" aria-label="פתיחת קלף ${escapeHtml(chapter.title)} במסך מלא">⛶</button>
          </div>
          <button class="card-flipper" type="button" data-flip="${chapter.n}" aria-label="הפיכת קלף ${escapeHtml(chapter.title)}">
            <span class="card-face front"><img loading="lazy" src="${chapter.front}" alt="חזית קלף ${number} — ${escapeHtml(chapter.title)}"></span>
            <span class="card-face back"><img loading="lazy" src="${chapter.back}" alt="גב קלף ${number} — ${escapeHtml(chapter.title)}"></span>
          </button>
        </div>
        <div class="card-meta">
          <small>שער ${number} · ${escapeHtml(chapter.pages)}</small>
          <h3>${escapeHtml(chapter.title)}</h3>
          <p>${escapeHtml(chapter.core)}</p>
        </div>
      </article>`;
  }

  function visibleChapters() {
    const term = normalize(search?.value);
    return chapters.filter(chapter => {
      const matchesGroup = activeFilter === "all" || chapter.group === activeFilter;
      const haystack = normalize([chapter.title, chapter.core, ...(chapter.practice || [])].join(" "));
      return matchesGroup && (!term || haystack.includes(term));
    });
  }

  function renderCards() {
    const visible = visibleChapters();
    count.textContent = `מוצגים ${visible.length} מתוך ${chapters.length} שערים`;
    grid.innerHTML = visible.length
      ? visible.map(cardMarkup).join("")
      : '<div class="empty-state">לא נמצאו שערים התואמים לחיפוש. נסו מילה אחרת.</div>';
  }

  function chapterById(id) {
    return chapters.find(chapter => chapter.n === Number(id));
  }

  function flipCard(id) {
    const article = grid.querySelector(`[data-id="${id}"]`);
    article?.querySelector(".card-frame")?.classList.toggle("flipped");
  }

  function updateLightbox() {
    if (!activeCard) return;
    const path = activeSide === "front" ? activeCard.front : activeCard.back;
    lightboxImage.src = path;
    lightboxImage.alt = `${activeSide === "front" ? "חזית" : "גב"} קלף ${activeCard.n} — ${activeCard.title}`;
    lightboxTitle.textContent = activeCard.title;
    lightboxNumber.textContent = `שער ${String(activeCard.n).padStart(2, "0")} · ${activeCard.pages} · ${activeSide === "front" ? "חזית" : "גב"}`;
    lightboxDownload.href = path;
  }

  function openCard(id) {
    activeCard = chapterById(id);
    activeSide = "front";
    updateLightbox();
    cardModal.showModal();
  }

  function showToast(message) {
    toast.textContent = message;
    toast.classList.add("show");
    window.clearTimeout(showToast.timer);
    showToast.timer = window.setTimeout(() => toast.classList.remove("show"), 2400);
  }

  async function openDocument(path, title) {
    contentTitle.textContent = title;
    contentBody.innerHTML = "<p>טוען את המסמך…</p>";
    contentModal.showModal();
    try {
      const embedded = window.KEDUSHA_DOCS?.[path];
      const markdown = embedded ?? await fetch(path).then(response => {
        if (!response.ok) throw new Error("load");
        return response.text();
      });
      contentBody.innerHTML = window.renderKedushaMarkdown(markdown);
    } catch {
      contentBody.innerHTML = `<p>המסמך זמין בקובץ <a href="${escapeHtml(path)}">${escapeHtml(path)}</a>.</p>`;
    }
  }

  function openAbout() {
    contentTitle.textContent = "אודות המהדורה";
    contentBody.innerHTML = `
      <h2>🕯️ אוצר הקדושה — KedushaVault</h2>
      <p>מאגר לימוד, ליקוט, תרגול והדפסה המבוסס על הספר <strong>״אוצר הקדושה״</strong> מאת רבי אליעזר שלמה שיק.</p>
      <h3>✨ יצירה וקרדיטים</h3>
      <ul>
        <li>עריכה, ליקוט, אפיון ועיצוב: <strong>Cyber Shamanic (CySh)</strong>.</li>
        <li>יוזמה ויצירה: <strong>לאון יעקובוב (AnLoMinus)</strong>.</li>
        <li><a href="https://www.linkedin.com/in/anlominus/">LinkedIn</a> · <a href="https://github.com/AnLoMinus">GitHub</a> · <a href="https://www.facebook.com/AnlominusX">Facebook</a> · <a href="https://codepen.io/Anlominus">CodePen</a></li>
        <li><a href="https://github.com/Cyber-Shamanic">Cyber Shamanic ב־GitHub</a></li>
      </ul>
      <h3>📬 יצירת קשר</h3>
      <ul>
        <li><a href="mailto:GlobalElite8200@gmail.com">GlobalElite8200@gmail.com</a></li>
        <li><a href="https://wa.me/972543285967">054-328-5967 ב־WhatsApp</a></li>
        <li><a href="https://wa.me/972535366687">053-536-6687 ב־WhatsApp</a></li>
      </ul>
      <h3>🔢 מספר המידות</h3>
      <p><strong>16 שערים · 32 צדדים · 64 פעולות · 16 שאלות דרך · 128 ליקוטים.</strong></p>
      <blockquote>״לֵב טָהוֹר בְּרָא לִי אֱלֹהִים; וְרוּחַ נָכוֹן חַדֵּשׁ בְּקִרְבִּי״ — תהלים נא, יב.</blockquote>`;
    contentModal.showModal();
  }

  grid?.addEventListener("click", event => {
    const flip = event.target.closest("[data-flip]");
    const open = event.target.closest("[data-open]");
    if (open) { event.stopPropagation(); openCard(open.dataset.open); return; }
    if (flip) flipCard(flip.dataset.flip);
  });

  search?.addEventListener("input", renderCards);
  document.querySelectorAll("[data-filter]").forEach(button => button.addEventListener("click", () => {
    activeFilter = button.dataset.filter;
    document.querySelectorAll("[data-filter]").forEach(item => item.classList.toggle("active", item === button));
    renderCards();
  }));

  document.querySelectorAll("[data-doc]").forEach(button => button.addEventListener("click", () => {
    openDocument(button.dataset.doc, button.dataset.title);
  }));
  document.querySelectorAll("[data-about]").forEach(button => button.addEventListener("click", openAbout));
  document.querySelector("[data-close]")?.addEventListener("click", () => contentModal.close());
  document.querySelector("[data-card-close]")?.addEventListener("click", () => cardModal.close());
  document.querySelector("[data-lightbox-flip]")?.addEventListener("click", () => {
    activeSide = activeSide === "front" ? "back" : "front";
    updateLightbox();
  });

  for (const modal of [contentModal, cardModal]) {
    modal?.addEventListener("click", event => {
      if (event.target === modal) modal.close();
    });
  }

  document.querySelector("[data-random]")?.addEventListener("click", () => {
    const chapter = chapters[Math.floor(Math.random() * chapters.length)];
    document.querySelector("#chapters")?.scrollIntoView({behavior: "smooth"});
    window.setTimeout(() => openCard(chapter.n), 500);
  });

  document.querySelector("[data-share]")?.addEventListener("click", async () => {
    const share = {title: document.title, text: "אוצר הקדושה — 16 שערים ו־128 ליקוטים", url: location.href};
    try {
      if (navigator.share) await navigator.share(share);
      else {
        await navigator.clipboard.writeText(location.href);
        showToast("הקישור הועתק ללוח");
      }
    } catch (error) {
      if (error.name !== "AbortError") showToast("לא ניתן היה לשתף את הקישור");
    }
  });

  const themeButton = document.querySelector("[data-theme]");
  const storedTheme = localStorage.getItem("kedusha-theme");
  if (storedTheme) document.documentElement.dataset.theme = storedTheme;
  const syncThemeIcon = () => {
    const dark = document.documentElement.dataset.theme === "dark";
    themeButton.textContent = dark ? "🌙" : "☀️";
    themeButton.setAttribute("aria-label", dark ? "מעבר לערכה בהירה" : "מעבר לערכה כהה");
  };
  themeButton?.addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    localStorage.setItem("kedusha-theme", next);
    syncThemeIcon();
  });

  syncThemeIcon();
  renderCards();

  if ("serviceWorker" in navigator && location.protocol.startsWith("http")) {
    window.addEventListener("load", () => navigator.serviceWorker.register("./sw.js").catch(() => {}));
  }
})();
