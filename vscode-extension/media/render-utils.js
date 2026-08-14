function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function escapeHtml(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function renderInline(segment) {
  segment = escapeHtml(segment);
  segment = segment.replace(/`([^`]+)`/g, "<code>$1</code>");
  segment = segment.replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>");
  segment = segment.replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g, "<i>$1</i>");
  segment = segment.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2">$1</a>');
  return segment;
}

function isTableRow(line) {
  return /\|/.test(line) && line.trim() !== "";
}

function isTableSeparator(line) {
  return /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/.test(line);
}

function splitTableRow(line) {
  const trimmed = line.trim().replace(/^\|/, "").replace(/\|$/, "");
  return trimmed.split("|").map((cell) => cell.trim());
}

function renderTable(headerLine, bodyLines) {
  const headerCells = splitTableRow(headerLine);
  let html = "<table><thead><tr>";
  for (const cell of headerCells) {
    html += "<th>" + renderInline(cell) + "</th>";
  }
  html += "</tr></thead><tbody>";
  for (const row of bodyLines) {
    html += "<tr>";
    for (const cell of splitTableRow(row)) {
      html += "<td>" + renderInline(cell) + "</td>";
    }
    html += "</tr>";
  }
  html += "</tbody></table>";
  return html;
}

function renderTextBlock(text) {
  const lines = text.split("\n");
  let html = "";
  let listTag = null;
  const closeList = () => {
    if (listTag) {
      html += "</" + listTag + ">";
      listTag = null;
    }
  };
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];

    if (isTableRow(line) && i + 1 < lines.length && isTableSeparator(lines[i + 1])) {
      closeList();
      const bodyLines = [];
      let j = i + 2;
      while (j < lines.length && isTableRow(lines[j]) && !isTableSeparator(lines[j])) {
        bodyLines.push(lines[j]);
        j++;
      }
      html += renderTable(line, bodyLines);
      i = j;
      continue;
    }

    const heading = /^(#{1,6})\s+(.*)$/.exec(line);
    const bullet = /^[-*]\s+(.*)$/.exec(line);
    const numbered = /^\d+\.\s+(.*)$/.exec(line);
    const rule = /^ {0,3}([-*_])(?: *\1){2,} *$/.test(line);
    if (rule) {
      closeList();
      html += "<hr>";
    } else if (heading) {
      closeList();
      const level = heading[1].length;
      html += "<h" + level + ">" + renderInline(heading[2]) + "</h" + level + ">";
    } else if (bullet) {
      if (listTag !== "ul") {
        closeList();
        html += "<ul>";
        listTag = "ul";
      }
      html += "<li>" + renderInline(bullet[1]) + "</li>";
    } else if (numbered) {
      if (listTag !== "ol") {
        closeList();
        html += "<ol>";
        listTag = "ol";
      }
      html += "<li>" + renderInline(numbered[1]) + "</li>";
    } else if (line.trim() === "") {
      closeList();
      html += "\n";
    } else {
      closeList();
      html += renderInline(line) + "\n";
    }
    i++;
  }
  closeList();
  return html;
}

function renderMarkdown(raw) {
  const blocks = raw.split(/```(\w*\n[\s\S]*?)```/g);
  let html = "";
  for (let i = 0; i < blocks.length; i++) {
    if (i % 2 === 1) {
      html += "<pre><code>" + escapeHtml(blocks[i].replace(/^\w*\n/, "")) + "</code></pre>";
    } else {
      html += renderTextBlock(blocks[i]);
    }
  }
  return html;
}
