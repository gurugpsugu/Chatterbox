"""Responsive, Stitch-inspired web UI served by the FastAPI entrypoint."""

HOME_PAGE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#f8f8f6">
  <title>Chatterbox — HDFC Mutual Fund FAQ</title>
  <style>
    :root {
      color-scheme: light;
      --paper: #f8f8f6;
      --surface: #fff;
      --surface-dim: #f0f1ef;
      --ink: #41464a;
      --ink-strong: #292e31;
      --muted: #777e82;
      --quiet: #a0a6a8;
      --line: #e3e6e4;
      --line-strong: #d3d7d5;
      --sage: #6f8f7b;
      --sage-dark: #3e5b49;
      --sage-pale: #ebf2ec;
      --error: #9c3e3e;
      --shadow: 0 1px 3px rgb(65 70 74 / 4%), 0 8px 24px rgb(65 70 74 / 4%);
      --sans: Inter, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
      --display: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
      --mono: "Cascadia Code", "SFMono-Regular", Consolas, monospace;
    }

    * { box-sizing: border-box; }

    html { min-width: 320px; background: var(--paper); }

    body {
      min-height: 100vh;
      margin: 0;
      color: var(--ink);
      background:
        radial-gradient(circle, rgb(182 190 185 / 38%) 1px, transparent 1.15px) 0 0 / 18px 18px,
        var(--paper);
      font: 15px/1.6 var(--sans);
      -webkit-font-smoothing: antialiased;
    }

    button, textarea { font: inherit; }
    button { color: inherit; }
    a { color: var(--sage-dark); }
    [hidden] { display: none !important; }

    .topbar {
      position: sticky;
      z-index: 5;
      top: 0;
      display: flex;
      min-height: 68px;
      align-items: center;
      justify-content: space-between;
      gap: 20px;
      padding: 12px clamp(18px, 5vw, 72px);
      border-bottom: 1px solid rgb(227 230 228 / 88%);
      background: rgb(255 255 255 / 90%);
      backdrop-filter: blur(14px);
    }

    .brand { display: flex; align-items: center; gap: 12px; min-width: 0; }

    .brand-mark {
      display: grid;
      width: 36px;
      height: 36px;
      flex: 0 0 auto;
      place-items: center;
      overflow: hidden;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: var(--surface-dim);
    }

    .brand-name {
      color: var(--ink-strong);
      font: 750 15px/1 var(--display);
      letter-spacing: .075em;
    }

    .brand-caption {
      display: block;
      margin-top: 5px;
      color: var(--muted);
      font: 10px/1.2 var(--mono);
      letter-spacing: .08em;
      text-transform: uppercase;
    }

    .header-note, .eyebrow, .micro-label {
      font-family: var(--mono);
      letter-spacing: .09em;
      text-transform: uppercase;
    }

    .header-note {
      display: inline-flex;
      align-items: center;
      gap: 9px;
      color: var(--muted);
      font-size: 10px;
    }

    .status-dot {
      width: 7px;
      height: 7px;
      flex: 0 0 auto;
      border-radius: 50%;
      background: var(--sage);
      box-shadow: 0 0 0 3px var(--sage-pale);
    }

    main { width: min(100% - 36px, 1040px); margin: 0 auto; }

    .welcome {
      position: relative;
      padding: clamp(58px, 9vw, 100px) 0 34px;
      animation: enter .55s ease-out both;
    }

    .welcome::after {
      position: absolute;
      z-index: -1;
      top: 42px;
      right: -20px;
      width: clamp(110px, 19vw, 220px);
      height: clamp(110px, 19vw, 220px);
      border-radius: 50%;
      background: radial-gradient(circle, rgb(196 208 200 / 62%) 1px, transparent 1.3px) 0 0 / 11px 11px;
      content: "";
      mask-image: radial-gradient(circle, #000 12%, transparent 72%);
      opacity: .7;
      pointer-events: none;
    }

    .eyebrow {
      display: flex;
      align-items: center;
      gap: 10px;
      margin: 0 0 18px;
      color: var(--muted);
      font-size: 10px;
    }

    h1 {
      max-width: 760px;
      margin: 0;
      color: var(--ink-strong);
      font: 650 clamp(34px, 6vw, 62px)/1.08 var(--display);
      letter-spacing: -.055em;
    }

    .intro {
      max-width: 610px;
      margin: 20px 0 0;
      color: var(--muted);
      font-size: clamp(15px, 2vw, 17px);
    }

    .trust-row {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 10px;
      margin-top: 25px;
    }

    .trust-pill, .privacy-note {
      display: inline-flex;
      min-height: 34px;
      align-items: center;
      gap: 8px;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: rgb(255 255 255 / 86%);
      padding: 6px 11px;
      font: 10px/1.4 var(--mono);
      letter-spacing: .035em;
    }

    .trust-pill { color: var(--sage-dark); }
    .privacy-note { color: var(--muted); }

    .suggestions { padding: 14px 0 32px; }

    .section-heading {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 12px;
      margin: 0 0 13px;
    }

    .section-heading h2 {
      margin: 0;
      color: var(--ink-strong);
      font: 600 14px/1.4 var(--display);
    }

    .micro-label { color: var(--quiet); font-size: 9px; }

    .suggestion-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }

    .suggestion {
      display: flex;
      min-height: 132px;
      flex-direction: column;
      justify-content: space-between;
      gap: 20px;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: var(--surface);
      padding: 17px;
      box-shadow: var(--shadow);
      cursor: pointer;
      text-align: left;
      transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease, background .18s ease;
    }

    .suggestion:hover {
      transform: translateY(-2px);
      border-color: #bdc9c1;
      background: #fdfefd;
      box-shadow: 0 8px 24px rgb(65 70 74 / 8%);
    }

    .suggestion:focus-visible, .send:focus-visible, .reset:focus-visible, textarea:focus-visible {
      outline: 3px solid rgb(111 143 123 / 35%);
      outline-offset: 3px;
    }

    .suggestion-top {
      display: flex;
      align-items: center;
      justify-content: space-between;
      color: var(--sage-dark);
      font: 10px var(--mono);
      letter-spacing: .08em;
      text-transform: uppercase;
    }

    .suggestion-text {
      color: var(--ink-strong);
      font: 600 15px/1.45 var(--display);
    }

    .suggestion-foot {
      display: flex;
      align-items: center;
      gap: 7px;
      border-top: 1px solid var(--line);
      padding-top: 10px;
      color: var(--muted);
      font-size: 11px;
    }

    .chat-shell {
      margin: 4px 0 22px;
      overflow: hidden;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: rgb(255 255 255 / 96%);
      box-shadow: 0 12px 32px rgb(65 70 74 / 6%);
    }

    .chat-head {
      display: flex;
      min-height: 48px;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      border-bottom: 1px solid var(--line);
      background: #fcfcfb;
      padding: 10px 16px;
    }

    .chat-label {
      display: flex;
      align-items: center;
      gap: 9px;
      color: var(--muted);
      font: 10px var(--mono);
      letter-spacing: .07em;
      text-transform: uppercase;
    }

    .reset {
      border: 0;
      background: transparent;
      color: var(--muted);
      padding: 5px;
      font: 11px var(--mono);
      cursor: pointer;
      transition: color .18s ease;
    }

    .reset:hover { color: var(--ink-strong); }

    .messages {
      display: flex;
      min-height: 100px;
      max-height: min(52vh, 500px);
      flex-direction: column;
      gap: 20px;
      overflow-y: auto;
      padding: 20px clamp(14px, 4vw, 28px);
      scroll-behavior: smooth;
    }

    .turn { display: grid; gap: 9px; animation: enter .25s ease-out both; }
    .user-turn { justify-items: end; }

    .user-bubble {
      max-width: min(88%, 680px);
      border: 1px solid #48514b;
      border-radius: 12px 12px 3px 12px;
      background: #414a44;
      color: white;
      padding: 12px 15px;
      overflow-wrap: anywhere;
    }

    .answer-card {
      width: min(100%, 760px);
      border: 1px solid var(--line);
      border-radius: 11px;
      background: white;
      padding: 15px;
    }

    .answer-meta {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
      margin-bottom: 10px;
      color: var(--muted);
      font: 10px var(--mono);
      text-transform: uppercase;
    }

    .answer-status {
      border: 1px solid var(--line);
      border-radius: 999px;
      background: var(--surface-dim);
      padding: 3px 8px;
      color: var(--ink);
      letter-spacing: .05em;
    }

    .answer-status.answered { border-color: #d4e2d7; background: var(--sage-pale); color: var(--sage-dark); }
    .answer-status.rejected, .answer-status.refused { border-color: #ead8d8; background: #fbf3f3; color: var(--error); }

    .answer-text { margin: 0; color: var(--ink-strong); white-space: pre-wrap; overflow-wrap: anywhere; }
    .answer-extra { margin: 10px 0 0; color: var(--muted); font-size: 12px; }

    .source-details {
      margin-top: 13px;
      border-top: 1px solid var(--line);
      padding-top: 11px;
    }

    .source-details summary {
      color: var(--sage-dark);
      font: 11px var(--mono);
      cursor: pointer;
      list-style-position: inside;
    }

    .source-list { display: grid; gap: 7px; margin: 11px 0 0; padding: 0; list-style: none; }
    .source-list a { overflow-wrap: anywhere; font-size: 12px; }
    .source-empty { margin: 9px 0 0; color: var(--muted); font-size: 12px; }

    .typing {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      color: var(--muted);
      font: 11px var(--mono);
    }

    .typing i {
      width: 5px;
      height: 5px;
      border-radius: 50%;
      background: var(--sage);
      animation: dot 1.15s ease-in-out infinite;
    }

    .typing i:nth-child(2) { animation-delay: .15s; }
    .typing i:nth-child(3) { animation-delay: .3s; }

    .composer {
      border-top: 1px solid var(--line);
      background: #fcfcfb;
      padding: 13px clamp(12px, 3vw, 20px) 15px;
    }

    .composer-row {
      display: flex;
      align-items: flex-end;
      gap: 10px;
      border: 1px solid var(--line-strong);
      border-radius: 9px;
      background: white;
      padding: 8px;
      transition: border-color .18s ease, box-shadow .18s ease;
    }

    .composer-row:focus-within {
      border-color: #9dae9f;
      box-shadow: 0 0 0 3px rgb(111 143 123 / 10%);
    }

    textarea {
      width: 100%;
      min-height: 44px;
      max-height: 130px;
      resize: vertical;
      border: 0;
      outline: 0;
      background: transparent;
      padding: 9px;
      color: var(--ink-strong);
      font-size: 14px;
    }

    textarea::placeholder { color: var(--quiet); }

    .send {
      display: inline-flex;
      min-height: 40px;
      align-items: center;
      justify-content: center;
      gap: 9px;
      flex: 0 0 auto;
      border: 1px solid #526859;
      border-radius: 7px;
      background: #414a44;
      padding: 0 14px;
      color: white;
      font: 600 10px var(--mono);
      letter-spacing: .08em;
      cursor: pointer;
      transition: background .18s ease, transform .18s ease;
    }

    .send:hover:not(:disabled) { transform: translateY(-1px); background: #303a33; }
    .send:disabled { cursor: wait; opacity: .65; }

    .composer-foot {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      margin-top: 8px;
      color: var(--quiet);
      font: 9px/1.5 var(--mono);
      letter-spacing: .04em;
    }

    footer {
      display: flex;
      justify-content: space-between;
      gap: 14px;
      border-top: 1px solid var(--line);
      margin-top: 40px;
      padding: 17px 0 24px;
      color: var(--muted);
      font: 9px/1.5 var(--mono);
      letter-spacing: .06em;
      text-transform: uppercase;
    }

    @keyframes enter {
      from { opacity: 0; transform: translateY(7px); }
      to { opacity: 1; transform: translateY(0); }
    }

    @keyframes dot {
      0%, 60%, 100% { opacity: .3; transform: translateY(0); }
      30% { opacity: 1; transform: translateY(-3px); }
    }

    @media (max-width: 720px) {
      .suggestion-grid { grid-template-columns: 1fr; }
      .suggestion { min-height: 105px; }
      .welcome { padding-top: 56px; }
      .welcome::after { top: 18px; right: -14px; opacity: .5; }
      .header-note { font-size: 0; }
      .header-note .status-dot { width: 8px; height: 8px; }
      .messages { max-height: 56vh; }
    }

    @media (max-width: 440px) {
      main { width: min(100% - 24px, 1040px); }
      .topbar { min-height: 60px; padding-inline: 12px; }
      .brand-caption { font-size: 9px; }
      .trust-row { align-items: stretch; flex-direction: column; }
      .trust-pill, .privacy-note { width: fit-content; }
      .send { width: 42px; padding: 0; font-size: 0; }
      .send span { font-size: 17px; }
      .composer-foot span:last-child { display: none; }
      footer { flex-direction: column; }
    }

    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after {
        scroll-behavior: auto !important;
        animation-duration: .01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: .01ms !important;
      }
    }
  </style>
</head>
<body>
  <header class="topbar">
    <a class="brand" href="/" aria-label="Chatterbox home">
      <span class="brand-mark" aria-hidden="true">
        <svg width="26" height="26" viewBox="0 0 26 26" fill="none">
          <circle cx="13" cy="13" r="10" stroke="#AAB6B1" stroke-dasharray="1.5 2"></circle>
          <circle cx="13" cy="3" r="1.1" fill="#6F8F7B"></circle>
          <circle cx="23" cy="13" r="1.1" fill="#777E82"></circle>
          <circle cx="13" cy="23" r="1.1" fill="#6F8F7B"></circle>
          <circle cx="3" cy="13" r="1.1" fill="#777E82"></circle>
          <circle cx="13" cy="13" r="5.6" stroke="#6F8F7B"></circle>
          <circle cx="13" cy="13" r="2" fill="#41464A"></circle>
        </svg>
      </span>
      <span>
        <span class="brand-name">CHATTERBOX</span>
        <span class="brand-caption">HDFC Mutual Fund FAQ</span>
      </span>
    </a>
    <span class="header-note"><i class="status-dot" aria-hidden="true"></i> Public-source answers</span>
  </header>

  <main>
    <section class="welcome" id="welcome">
      <p class="eyebrow"><span class="status-dot" aria-hidden="true"></span> A quieter way to find fund facts</p>
      <h1>Get clear answers about HDFC mutual funds.</h1>
      <p class="intro">Ask a factual question. Chatterbox uses the source material available to this prototype and shows citations when they are returned.</p>
      <div class="trust-row">
        <span class="trust-pill"><span aria-hidden="true">●</span> Facts-only. No investment advice.</span>
        <span class="privacy-note"><span aria-hidden="true">◇</span> Please don’t share personal, account, or contact information.</span>
      </div>
    </section>

    <section class="suggestions" id="suggestions" aria-labelledby="suggestion-title">
      <div class="section-heading">
        <h2 id="suggestion-title">Try a question</h2>
        <span class="micro-label">Choose a prompt to begin</span>
      </div>
      <div class="suggestion-grid">
        <button class="suggestion" type="button" data-question="What is the expense ratio of HDFC Large Cap Fund Direct Growth?">
          <span class="suggestion-top"><span>Scheme detail</span><span aria-hidden="true">↗</span></span>
          <span class="suggestion-text">What is the expense ratio of HDFC Large Cap Fund Direct Growth?</span>
          <span class="suggestion-foot"><span class="status-dot" aria-hidden="true"></span> Ask from available sources</span>
        </button>
        <button class="suggestion" type="button" data-question="What is the minimum SIP for HDFC Mid Cap Fund Direct Growth?">
          <span class="suggestion-top"><span>Investing terms</span><span aria-hidden="true">↗</span></span>
          <span class="suggestion-text">What is the minimum SIP for HDFC Mid Cap Fund Direct Growth?</span>
          <span class="suggestion-foot"><span class="status-dot" aria-hidden="true"></span> Ask from available sources</span>
        </button>
        <button class="suggestion" type="button" data-question="What is the ELSS lock-in period for HDFC ELSS Tax Saver Fund?">
          <span class="suggestion-top"><span>ELSS basics</span><span aria-hidden="true">↗</span></span>
          <span class="suggestion-text">What is the ELSS lock-in period for HDFC ELSS Tax Saver Fund?</span>
          <span class="suggestion-foot"><span class="status-dot" aria-hidden="true"></span> Ask from available sources</span>
        </button>
      </div>
    </section>

    <section class="chat-shell" aria-label="Question and answer">
      <div class="chat-head">
        <span class="chat-label"><span class="status-dot" aria-hidden="true"></span> Question console</span>
        <button class="reset" id="reset" type="button" hidden>Clear session</button>
      </div>
      <div class="messages" id="messages" aria-live="polite" aria-relevant="additions"></div>
      <form class="composer" id="chat-form">
        <div class="composer-row">
          <label for="question" class="micro-label" style="position:absolute;left:-10000px">Your factual question</label>
          <textarea id="question" name="question" maxlength="1000" rows="1" placeholder="Ask about a scheme, SIP, expense ratio, or fund term…" required></textarea>
          <button class="send" id="send" type="submit"><span>SEND</span><span aria-hidden="true">→</span></button>
        </div>
        <div class="composer-foot">
          <span>Your question is sent to the assistant for this response.</span>
          <span>Enter a factual question · 1000 characters max</span>
        </div>
      </form>
    </section>

    <footer>
      <span>Chatterbox · Mutual fund FAQ prototype</span>
      <span>Facts-only · No investment advice</span>
    </footer>
  </main>

  <script>
    const form = document.getElementById("chat-form");
    const questionField = document.getElementById("question");
    const sendButton = document.getElementById("send");
    const messages = document.getElementById("messages");
    const resetButton = document.getElementById("reset");
    const welcome = document.getElementById("welcome");
    const suggestions = document.getElementById("suggestions");

    function appendQuestion(question) {
      const turn = document.createElement("article");
      turn.className = "turn user-turn";
      turn.setAttribute("aria-label", "Your question");
      const bubble = document.createElement("div");
      bubble.className = "user-bubble";
      bubble.textContent = question;
      turn.append(bubble);
      messages.append(turn);
      messages.scrollTop = messages.scrollHeight;
    }

    function appendLoading() {
      const turn = document.createElement("div");
      turn.className = "turn loading-turn";
      turn.setAttribute("role", "status");
      turn.innerHTML = '<span class="typing"><i></i><i></i><i></i> Checking available sources</span>';
      messages.append(turn);
      messages.scrollTop = messages.scrollHeight;
      return turn;
    }

    function safeHttpUrl(value) {
      try {
        const url = new URL(value);
        return url.protocol === "https:" || url.protocol === "http:" ? url.href : null;
      } catch {
        return null;
      }
    }

    function appendAnswer(data) {
      const turn = document.createElement("article");
      turn.className = "turn";
      turn.setAttribute("aria-label", "Assistant answer");

      const card = document.createElement("div");
      card.className = "answer-card";
      const meta = document.createElement("div");
      meta.className = "answer-meta";
      const status = document.createElement("span");
      const statusText = String(data.status || "answered");
      status.className = `answer-status ${statusText}`;
      status.textContent = statusText.replaceAll("_", " ");
      meta.append(status);
      card.append(meta);

      const answer = document.createElement("p");
      answer.className = "answer-text";
      answer.textContent = data.answer || "The assistant returned no answer.";
      card.append(answer);

      if (data.last_updated_from_sources) {
        const updated = document.createElement("p");
        updated.className = "answer-extra";
        updated.textContent = `Last updated from sources: ${data.last_updated_from_sources}`;
        card.append(updated);
      }

      const details = document.createElement("details");
      details.className = "source-details";
      const summary = document.createElement("summary");
      const citations = Array.isArray(data.citations) ? data.citations : [];
      summary.textContent = `Sources (${citations.length})`;
      details.append(summary);

      if (citations.length) {
        const list = document.createElement("ul");
        list.className = "source-list";
        for (const citation of citations) {
          const href = safeHttpUrl(citation.url);
          if (!href) continue;
          const item = document.createElement("li");
          const link = document.createElement("a");
          link.href = href;
          link.target = "_blank";
          link.rel = "noopener noreferrer";
          link.textContent = citation.label || href;
          item.append(link);
          list.append(item);
        }
        details.append(list);
      } else {
        const empty = document.createElement("p");
        empty.className = "source-empty";
        empty.textContent = "No source links were returned for this response.";
        details.append(empty);
      }
      card.append(details);
      turn.append(card);
      messages.append(turn);
      messages.scrollTop = messages.scrollHeight;
    }

    async function submitQuestion(rawQuestion) {
      const question = rawQuestion.trim();
      if (!question || sendButton.disabled) return;

      welcome.hidden = true;
      suggestions.hidden = true;
      resetButton.hidden = false;
      resetButton.disabled = true;
      questionField.value = "";
      appendQuestion(question);
      const loading = appendLoading();
      sendButton.disabled = true;
      questionField.disabled = true;

      try {
        const response = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question })
        });
        if (!response.ok) throw new Error("The request could not be completed. Please try again.");
        appendAnswer(await response.json());
      } catch (error) {
        const failure = document.createElement("article");
        failure.className = "turn";
        failure.setAttribute("role", "alert");
        const message = document.createElement("p");
        message.className = "answer-card answer-text";
        message.textContent = error.message || "The request could not be completed. Please try again.";
        failure.append(message);
        messages.append(failure);
      } finally {
        loading.remove();
        sendButton.disabled = false;
        questionField.disabled = false;
        resetButton.disabled = false;
        questionField.focus();
        messages.scrollTop = messages.scrollHeight;
      }
    }

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      submitQuestion(questionField.value);
    });

    document.querySelectorAll("[data-question]").forEach((button) => {
      button.addEventListener("click", () => submitQuestion(button.dataset.question || ""));
    });

    resetButton.addEventListener("click", () => {
      messages.replaceChildren();
      questionField.value = "";
      welcome.hidden = false;
      suggestions.hidden = false;
      resetButton.hidden = true;
      resetButton.disabled = false;
      questionField.focus();
    });
  </script>
</body>
</html>"""
