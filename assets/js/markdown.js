(() => {
  "use strict";

  const escapeHtml = value => String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

  const inline = value => escapeHtml(value)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>")
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+|mailto:[^\s)]+|[^\s)]+)\)/g, '<a href="$2">$1</a>');

  function renderMarkdown(markdown) {
    const lines = String(markdown || "").replace(/\r/g, "").split("\n");
    const html = [];
    let list = null;
    let paragraph = [];

    const closeParagraph = () => {
      if (paragraph.length) html.push(`<p>${inline(paragraph.join(" "))}</p>`);
      paragraph = [];
    };
    const closeList = () => {
      if (list) html.push(`</${list}>`);
      list = null;
    };

    for (const raw of lines) {
      const line = raw.trim();
      if (!line) {
        closeParagraph();
        closeList();
        continue;
      }
      const heading = /^(#{1,4})\s+(.+)$/.exec(line);
      if (heading) {
        closeParagraph(); closeList();
        const level = heading[1].length;
        html.push(`<h${level}>${inline(heading[2])}</h${level}>`);
        continue;
      }
      if (/^---+$/.test(line)) {
        closeParagraph(); closeList(); html.push("<hr>"); continue;
      }
      if (line.startsWith("> ")) {
        closeParagraph(); closeList(); html.push(`<blockquote>${inline(line.slice(2))}</blockquote>`); continue;
      }
      const task = /^- \[([ xX])\]\s+(.+)$/.exec(line);
      if (task) {
        closeParagraph();
        if (list !== "ul") { closeList(); html.push("<ul>"); list = "ul"; }
        html.push(`<li class="task"><input type="checkbox" ${task[1] !== " " ? "checked" : ""} disabled><span>${inline(task[2])}</span></li>`);
        continue;
      }
      const unordered = /^[-*]\s+(.+)$/.exec(line);
      if (unordered) {
        closeParagraph();
        if (list !== "ul") { closeList(); html.push("<ul>"); list = "ul"; }
        html.push(`<li>${inline(unordered[1])}</li>`);
        continue;
      }
      const ordered = /^\d+[.)]\s+(.+)$/.exec(line);
      if (ordered) {
        closeParagraph();
        if (list !== "ol") { closeList(); html.push("<ol>"); list = "ol"; }
        html.push(`<li>${inline(ordered[1])}</li>`);
        continue;
      }
      closeList();
      paragraph.push(line);
    }
    closeParagraph(); closeList();
    return html.join("\n");
  }

  window.renderKedushaMarkdown = renderMarkdown;
})();
