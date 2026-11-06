"""Responsive, Stitch-inspired web UI served by the FastAPI entrypoint."""

HOME_PAGE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#f8f8f6">
  <title>Chatterbox — Mutual Fund Explorer</title>
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
    .suggestions { view-transition-name: conversation-panel; }

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

    .fund-filters {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin: 0 0 14px;
    }

    .fund-filters select {
      min-width: 190px;
      border: 1px solid var(--line-strong);
      border-radius: 8px;
      background: var(--surface);
      color: var(--ink);
      padding: 9px 12px;
      font: 12px var(--sans);
    }

    .fund-category {
      color: var(--muted);
      font-size: 11px;
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
      display: none;
      margin: 4px 0 22px;
      overflow: hidden;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: rgb(255 255 255 / 96%);
      box-shadow: 0 12px 32px rgb(65 70 74 / 6%);
    }

    .chat-shell.is-active {
      display: block;
      view-transition-name: conversation-panel;
      animation: chat-arrive .58s cubic-bezier(.2,.8,.2,1) both;
    }

    ::view-transition-group(conversation-panel) { animation-duration: .55s; }
    ::view-transition-old(conversation-panel) { animation: panel-pan-out .38s cubic-bezier(.4,0,.2,1) both; }
    ::view-transition-new(conversation-panel) { animation: panel-pan-in .58s cubic-bezier(.2,.8,.2,1) both; }

    .conversation-bar {
      display: flex;
      align-items: center;
      gap: 8px;
      overflow-x: auto;
      border-bottom: 1px solid var(--line);
      background: #f7f8f6;
      padding: 8px 12px;
    }

    .conversation-tabs {
      display: flex;
      min-width: 0;
      flex: 1 1 auto;
      align-items: center;
      gap: 6px;
    }

    .conversation-tab-item { display: inline-flex; flex: 0 0 auto; align-items: center; }

    .conversation-tab {
      display: inline-flex;
      max-width: 240px;
      min-height: 34px;
      align-items: center;
      gap: 8px;
      border: 1px solid transparent;
      border-radius: 7px;
      background: transparent;
      padding: 5px 9px;
      color: var(--muted);
      cursor: pointer;
      font: 11px var(--mono);
      white-space: nowrap;
    }

    .conversation-tab[aria-selected="true"] {
      border-color: var(--line);
      background: white;
      color: var(--ink-strong);
      box-shadow: 0 1px 3px rgb(65 70 74 / 5%);
    }

    .conversation-tab-title { overflow: hidden; text-overflow: ellipsis; }

    .close-tab {
      display: grid;
      width: 20px;
      height: 20px;
      flex: 0 0 auto;
      place-items: center;
      border: 0;
      border-radius: 4px;
      background: transparent;
      color: var(--quiet);
      cursor: pointer;
    }

    .close-tab:hover { background: var(--surface-dim); color: var(--ink-strong); }

    .new-conversation, .read-aloud {
      min-height: 32px;
      flex: 0 0 auto;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: white;
      padding: 5px 10px;
      color: var(--sage-dark);
      cursor: pointer;
      font: 10px var(--mono);
      transition: border-color .18s ease, background .18s ease;
    }

    .new-conversation:hover, .read-aloud:hover { border-color: #bdc9c1; background: #fdfefd; }

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

    .return-calculator {
      display: grid;
      grid-template-columns: minmax(210px, .75fr) minmax(280px, 1.25fr);
      gap: 18px;
      border-bottom: 1px solid var(--line);
      background: linear-gradient(115deg, #f8faf8, #fff 62%);
      padding: 18px clamp(14px, 4vw, 28px);
      animation: enter .35s ease-out both;
    }

    .calculator-copy h2 {
      margin: 4px 0 7px;
      color: var(--ink-strong);
      font: 650 19px/1.2 var(--display);
      letter-spacing: -.025em;
    }

    .calculator-copy p:last-child {
      margin: 0;
      color: var(--muted);
      font-size: 11px;
    }

    .calculator-fields {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 9px;
      align-content: start;
    }

    .calculator-field { display: grid; gap: 5px; }
    .calculator-field label { color: var(--muted); font: 9px var(--mono); }

    .calculator-field input {
      width: 100%;
      min-width: 0;
      border: 1px solid var(--line-strong);
      border-radius: 7px;
      background: white;
      padding: 9px 10px;
      color: var(--ink-strong);
      font: 12px var(--mono);
      font-variant-numeric: tabular-nums;
    }

    .calculator-field input:focus-visible {
      outline: 3px solid rgb(111 143 123 / 25%);
      outline-offset: 2px;
    }

    .calculator-result {
      grid-column: 1 / -1;
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
      border-top: 1px solid var(--line);
      padding-top: 10px;
    }

    .calculator-output { display: grid; gap: 3px; }
    .calculator-output span { color: var(--quiet); font: 9px var(--mono); text-transform: uppercase; }
    .calculator-output strong { color: var(--ink-strong); font: 600 14px var(--mono); font-variant-numeric: tabular-nums; }
    .calculator-assumption { grid-column: 1 / -1; margin: 0; color: var(--muted); font-size: 10px; }
    .calculator-assumption strong { color: var(--ink-strong); }

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

    .answer-actions { display: flex; justify-content: flex-end; margin: -2px 0 8px; }

    .read-aloud[aria-pressed="true"] { border-color: #bdc9c1; background: var(--sage-pale); }

    .fact-visuals {
      display: grid;
      grid-template-columns: minmax(210px, .75fr) minmax(280px, 1.25fr);
      gap: 12px;
      width: 100%;
    }

    .metric-card, .chart-card {
      min-width: 0;
      border: 1px solid var(--line);
      border-radius: 11px;
      background: white;
      padding: 17px;
    }

    .metric-label {
      margin: 0;
      color: var(--muted);
      font: 10px var(--mono);
      letter-spacing: .07em;
      text-transform: uppercase;
    }

    .metric-value {
      margin: 10px 0 7px;
      color: var(--ink-strong);
      font: 650 clamp(30px, 5vw, 46px)/1.05 var(--display);
      letter-spacing: -.045em;
      font-variant-numeric: tabular-nums;
      overflow-wrap: anywhere;
    }

    .metric-source { margin: 0; color: var(--quiet); font-size: 10px; }

    .metric-card {
      display: flex;
      flex-direction: column;
      justify-content: center;
      min-height: 184px;
    }

    .metric-value { min-height: 1.1em; }

    .source-mood {
      display: inline-flex;
      width: fit-content;
      align-items: center;
      gap: 7px;
      margin-top: 14px;
      border: 1px solid #d5e5dc;
      border-radius: 999px;
      background: #f1f6f8;
      padding: 5px 9px;
      color: #39586d;
      font: 9px var(--mono);
      letter-spacing: .04em;
      text-transform: uppercase;
    }

    .source-mood.third-party {
      border-color: #eadfc8;
      background: #fbf6eb;
      color: #755b2c;
    }

    .source-mood::before {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: currentColor;
      content: "";
    }

    .chart-card { margin: 0; }
    .chart-title { margin: 0 0 18px; color: var(--ink-strong); font: 600 13px var(--display); }
    .chart-rows { display: grid; gap: 10px; }
    .chart-row { display: grid; grid-template-columns: minmax(85px, 30%) 1fr auto; align-items: center; gap: 9px; font-size: 11px; }
    .chart-name { overflow-wrap: anywhere; color: var(--muted); }
    .chart-track { height: 12px; overflow: hidden; border-radius: 999px; background: #e9ece9; }
    .chart-bar { display: block; width: 0; height: 100%; border-radius: inherit; background: linear-gradient(90deg, #91aa98, #526d5b); transition: width .9s cubic-bezier(.2,.8,.2,1); }
    .chart-value { color: var(--ink-strong); font: 11px var(--mono); font-variant-numeric: tabular-nums; white-space: nowrap; }
    .chart-axis { display: flex; justify-content: space-between; margin: 8px 0 0; color: var(--quiet); font: 9px var(--mono); }
    .chart-caption { margin: 12px 0 0; color: var(--muted); font-size: 10px; }

    .follow-ups {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 7px;
      margin-top: 12px;
      border-top: 1px solid var(--line);
      padding-top: 11px;
    }

    .follow-ups-label {
      width: 100%;
      color: var(--quiet);
      font: 9px var(--mono);
      letter-spacing: .08em;
      text-transform: uppercase;
    }

    .follow-up {
      border: 1px solid var(--line);
      border-radius: 999px;
      background: #fbfcfa;
      padding: 6px 10px;
      color: var(--sage-dark);
      cursor: pointer;
      font-size: 11px;
      line-height: 1.4;
      text-align: left;
      transition: border-color .18s ease, background .18s ease;
    }

    .follow-up:hover { border-color: #bdc9c1; background: var(--sage-pale); }

    .feature-dialog {
      width: min(440px, calc(100% - 32px));
      border: 1px solid var(--line-strong);
      border-radius: 14px;
      background: var(--surface);
      padding: 0;
      color: var(--ink);
      box-shadow: 0 24px 80px rgb(25 30 27 / 22%);
    }

    .feature-dialog::backdrop { background: rgb(35 40 37 / 42%); backdrop-filter: blur(3px); }
    .dialog-content { padding: 24px; }
    .dialog-content h2 { margin: 9px 0 8px; color: var(--ink-strong); font: 650 22px/1.2 var(--display); }
    .dialog-content p { margin: 0; color: var(--muted); font-size: 14px; }
    .dialog-icon { display: grid; width: 42px; height: 42px; place-items: center; border: 1px solid #d4e2d7; border-radius: 11px; background: var(--sage-pale); color: var(--sage-dark); font-size: 20px; }
    .dialog-actions { display: flex; justify-content: flex-end; margin-top: 20px; }
    .dialog-actions button { min-height: 38px; border: 1px solid #526859; border-radius: 7px; background: #414a44; padding: 0 14px; color: white; cursor: pointer; font: 11px var(--mono); }

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

    .non-advice {
      margin: 13px 0 0;
      border: 1px solid #d8ded9;
      border-left: 4px solid #596b5f;
      border-radius: 5px 9px 9px 5px;
      background: #f5f7f5;
      padding: 11px 13px;
      color: #303833;
      font-size: 12px;
      line-height: 1.5;
    }

    .non-advice strong {
      display: block;
      margin-bottom: 2px;
      font: 700 10px var(--mono);
      letter-spacing: .055em;
      text-transform: uppercase;
    }

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

    @keyframes panel-pan-out {
      to { opacity: 0; filter: blur(3px); transform: scale(.94) translateY(-24px); clip-path: inset(0 3% 12% round 24px); }
    }

    @keyframes panel-pan-in {
      from { opacity: 0; filter: blur(3px); transform: scale(.92) translateY(42px); clip-path: inset(0 7% 9% round 28px); }
      to { opacity: 1; filter: blur(0); transform: scale(1) translateY(0); clip-path: inset(0 0 0 round 14px); }
    }

    @keyframes chat-arrive {
      from { opacity: 0; transform: translateY(20px) scale(.985); }
      to { opacity: 1; transform: translateY(0) scale(1); }
    }

    @keyframes metric-count-in {
      from { opacity: .45; transform: translateY(8px) scale(.97); }
      to { opacity: 1; transform: translateY(0) scale(1); }
    }

    @keyframes dot {
      0%, 60%, 100% { opacity: .3; transform: translateY(0); }
      30% { opacity: 1; transform: translateY(-3px); }
    }

    @media (max-width: 720px) {
      .suggestion-grid { grid-template-columns: 1fr; }
      .fact-visuals { grid-template-columns: 1fr; }
      .return-calculator { grid-template-columns: 1fr; }
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

      ::view-transition-group(conversation-panel),
      ::view-transition-old(conversation-panel),
      ::view-transition-new(conversation-panel) { animation: none !important; }

      .chat-shell.is-active { animation: none !important; }
      .chart-bar { transition: none !important; }
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
        <span class="brand-caption">Mutual fund explorer</span>
      </span>
    </a>
    <span class="header-note"><i class="status-dot" aria-hidden="true"></i> Public-source answers</span>
  </header>

  <main>
    <section class="welcome" id="welcome">
      <p class="eyebrow"><span class="status-dot" aria-hidden="true"></span> A quieter way to find fund facts</p>
      <h1>Clear answers across mutual funds.</h1>
      <p class="intro">Explore schemes across six AMCs and eight categories. Answers prioritize official AMC sources and label third-party citations when used.</p>
      <div class="trust-row">
        <span class="trust-pill"><span aria-hidden="true">●</span> Facts-only. No investment advice.</span>
        <span class="privacy-note"><span aria-hidden="true">◇</span> Please don’t share personal, account, or contact information.</span>
      </div>
    </section>

    <section class="suggestions" id="suggestions" aria-labelledby="suggestion-title">
      <div class="section-heading">
        <h2 id="suggestion-title">Explore schemes</h2>
        <span class="micro-label" id="fund-count">Choose a scheme to ask about it</span>
      </div>
      <div class="fund-filters" aria-label="Filter schemes">
        <label class="micro-label" for="category-filter">Category</label>
        <select id="category-filter" aria-label="Filter by category"><option value="">All categories</option></select>
        <label class="micro-label" for="amc-filter">AMC</label>
        <select id="amc-filter" aria-label="Filter by AMC"><option value="">All AMCs</option></select>
      </div>
      <div class="suggestion-grid" id="fund-cards" aria-live="polite"></div>
    </section>

    <section class="chat-shell" aria-label="Question and answer">
      <div class="conversation-bar">
        <div class="conversation-tabs" id="conversation-tabs" role="tablist" aria-label="Conversations"></div>
        <button class="new-conversation" id="new-conversation" type="button">+ New chat</button>
      </div>
      <div class="chat-head">
        <span class="chat-label"><span class="status-dot" aria-hidden="true"></span> Question console</span>
        <button class="reset" id="reset" type="button" hidden>Clear chat</button>
      </div>
      <section class="return-calculator" id="return-calculator" aria-labelledby="calculator-title" hidden>
        <div class="calculator-copy">
          <p class="micro-label">Illustrative calculator · not a forecast</p>
          <h2 id="calculator-title">Explore a hypothetical return</h2>
          <p id="calculator-fund-name"></p>
        </div>
        <div class="calculator-fields">
          <div class="calculator-field">
            <label for="calculator-monthly">Monthly investment (₹)</label>
            <input id="calculator-monthly" type="number" min="1" max="10000000" step="500" inputmode="decimal" placeholder="Enter amount">
          </div>
          <div class="calculator-field">
            <label for="calculator-years">Time horizon (years)</label>
            <input id="calculator-years" type="number" min="1" max="50" step="1" inputmode="numeric" placeholder="1–50">
          </div>
          <div class="calculator-field">
            <label for="calculator-rate">Assumed annual return (%)</label>
            <input id="calculator-rate" type="number" min="0" max="30" step="0.5" inputmode="decimal" placeholder="Your assumption">
          </div>
          <div class="calculator-result" id="calculator-result" aria-live="polite">
            <p class="calculator-assumption">Enter your assumptions to see an illustration. This does not use or predict this fund’s returns.</p>
          </div>
        </div>
      </section>
      <div class="messages" id="messages" role="tabpanel" aria-live="polite" aria-relevant="additions"></div>
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
      <span>Chatterbox · Mutual fund explorer</span>
      <span>Facts-only · No investment advice</span>
    </footer>
  </main>

  <dialog class="feature-dialog" id="read-aloud-dialog" aria-labelledby="read-aloud-title">
    <div class="dialog-content">
      <span class="dialog-icon" aria-hidden="true">◖</span>
      <p class="micro-label" style="margin-top:14px">A little more personal</p>
      <h2 id="read-aloud-title">Listen to an answer</h2>
      <p>Use the “Read aloud” control on any answer to hear it spoken in your browser’s voice. Playback stays on this device, and you can stop it whenever you like.</p>
      <div class="dialog-actions"><button id="dismiss-read-aloud" type="button">Sounds good</button></div>
    </div>
  </dialog>

  <script>
    const form = document.getElementById("chat-form");
    const questionField = document.getElementById("question");
    const sendButton = document.getElementById("send");
    const messages = document.getElementById("messages");
    const chatShell = document.querySelector(".chat-shell");
    const resetButton = document.getElementById("reset");
    const welcome = document.getElementById("welcome");
    const suggestions = document.getElementById("suggestions");
    const tabsElement = document.getElementById("conversation-tabs");
    const fundCards = document.getElementById("fund-cards");
    const categoryFilter = document.getElementById("category-filter");
    const amcFilter = document.getElementById("amc-filter");
    const fundCount = document.getElementById("fund-count");
    const speechSupported = "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;
    let nextConversationId = 2;
    let conversations = [{ id: 1, title: "New chat", turns: [], pending: false }];
    let activeConversationId = 1;
    let activeSpeechButton = null;
    let fundCatalog = [];
    const animatedMetricResponses = new WeakSet();
    const returnCalculator = document.getElementById("return-calculator");
    const calculatorFundName = document.getElementById("calculator-fund-name");
    const calculatorMonthly = document.getElementById("calculator-monthly");
    const calculatorYears = document.getElementById("calculator-years");
    const calculatorRate = document.getElementById("calculator-rate");
    const calculatorResult = document.getElementById("calculator-result");

    function renderReturnCalculator() {
      const conversation = activeConversation();
      const selectedFund = fundCatalog.find((fund) => fund.fund_id === (conversation && conversation.fundId));
      returnCalculator.hidden = !selectedFund;
      if (!selectedFund) return;
      calculatorFundName.textContent = selectedFund.name;

      const monthly = Number(calculatorMonthly.value);
      const years = Number(calculatorYears.value);
      const annualRate = Number(calculatorRate.value);
      const valid = calculatorMonthly.value !== "" && calculatorYears.value !== ""
        && calculatorRate.value !== ""
        && Number.isFinite(monthly) && monthly > 0 && monthly <= 10000000
        && Number.isInteger(years) && years >= 1 && years <= 50
        && Number.isFinite(annualRate) && annualRate >= 0 && annualRate <= 30;
      calculatorResult.replaceChildren();
      if (!valid) {
        const prompt = document.createElement("p");
        prompt.className = "calculator-assumption";
        prompt.textContent = "Enter a monthly amount, 1–50 years, and an assumed rate from 0–30%.";
        calculatorResult.append(prompt);
        return;
      }

      const months = years * 12;
      const monthlyRate = Math.pow(1 + annualRate / 100, 1 / 12) - 1;
      const invested = monthly * months;
      const estimate = monthlyRate === 0
        ? invested
        : monthly * ((Math.pow(1 + monthlyRate, months) - 1) / monthlyRate);
      const items = [
        ["Illustrative value", estimate],
        ["Total contributed", invested],
        ["Illustrative difference", estimate - invested],
      ];
      const currency = new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        maximumFractionDigits: 0,
      });
      for (const [label, amount] of items) {
        const output = document.createElement("div");
        output.className = "calculator-output";
        const outputLabel = document.createElement("span");
        outputLabel.textContent = label;
        const value = document.createElement("strong");
        value.textContent = currency.format(amount);
        output.append(outputLabel, value);
        calculatorResult.append(output);
      }
      const assumption = document.createElement("p");
      assumption.className = "calculator-assumption";
      const emphasis = document.createElement("strong");
      emphasis.textContent = "Illustration only.";
      assumption.append(emphasis, document.createTextNode(
        " Assumes month-end contributions and monthly compounding at your entered rate; excludes fees and taxes. " +
        "Actual returns may be lower, higher, or negative. This is not a forecast or investment recommendation."
      ));
      calculatorResult.append(assumption);
    }

    function animateMetricValue(element, metric, response) {
      if (animatedMetricResponses.has(response)) {
        element.textContent = metric.display_value;
        return;
      }
      animatedMetricResponses.add(response);
      const formatted = metric.display_value.match(/^([^0-9+-]*)([-+]?\d[\d,]*(?:\.\d+)?)(.*)$/);
      if (!formatted || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        element.textContent = metric.display_value;
        return;
      }
      const prefix = formatted[1];
      const suffix = formatted[3];
      const decimals = (formatted[2].split(".")[1] || "").length;
      const target = metric.value;
      const formatter = new Intl.NumberFormat("en-IN", {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      });
      const start = performance.now();
      const duration = 1050;
      element.classList.add("is-counting");
      function tick(now) {
        const progress = Math.min(1, (now - start) / duration);
        const eased = 1 - Math.pow(1 - progress, 4);
        element.textContent = `${prefix}${formatter.format(target * eased)}${suffix}`;
        if (progress < 1) requestAnimationFrame(tick);
        else {
          element.textContent = metric.display_value;
          element.classList.remove("is-counting");
        }
      }
      requestAnimationFrame(tick);
    }

    function renderFundCatalog() {
      const category = categoryFilter.value;
      const amc = amcFilter.value;
      const visibleFunds = fundCatalog.filter((fund) =>
        (!category || fund.category === category) && (!amc || fund.amc === amc)
      );
      fundCount.textContent = `${visibleFunds.length} scheme${visibleFunds.length === 1 ? "" : "s"}`;
      fundCards.replaceChildren();
      if (!visibleFunds.length) {
        const empty = document.createElement("p");
        empty.className = "micro-label";
        empty.textContent = "No schemes match these filters.";
        fundCards.append(empty);
        return;
      }
      for (const fund of visibleFunds) {
        const card = document.createElement("button");
        card.className = "suggestion";
        card.type = "button";
        card.dataset.question = `What is the expense ratio of ${fund.name}?`;
        card.dataset.fundId = fund.fund_id;
        const meta = document.createElement("span");
        meta.className = "suggestion-top";
        const amcName = document.createElement("span");
        amcName.textContent = fund.amc;
        const arrow = document.createElement("span");
        arrow.setAttribute("aria-hidden", "true");
        arrow.textContent = "↗";
        meta.append(amcName, arrow);
        const name = document.createElement("span");
        name.className = "suggestion-text";
        name.textContent = fund.name;
        const foot = document.createElement("span");
        foot.className = "suggestion-foot";
        const categoryLabel = document.createElement("span");
        categoryLabel.className = "fund-category";
        categoryLabel.textContent = fund.category;
        const action = document.createElement("span");
        action.textContent = "Ask about this scheme";
        foot.append(categoryLabel, action);
        card.append(meta, name, foot);
        fundCards.append(card);
      }
    }

    async function loadFundCatalog() {
      try {
        const response = await fetch("/api/funds");
        if (!response.ok) throw new Error("The scheme catalog could not be loaded.");
        const catalog = await response.json();
        fundCatalog = catalog.funds;
        for (const category of catalog.categories) {
          const option = document.createElement("option");
          option.value = category;
          option.textContent = category;
          categoryFilter.append(option);
        }
        for (const amc of catalog.amcs) {
          const option = document.createElement("option");
          option.value = amc;
          option.textContent = amc;
          amcFilter.append(option);
        }
        renderFundCatalog();
      } catch (error) {
        fundCount.textContent = "Catalog unavailable";
        const message = document.createElement("p");
        message.className = "micro-label";
        message.setAttribute("role", "alert");
        message.textContent = error.message || "The scheme catalog could not be loaded.";
        fundCards.replaceChildren(message);
      }
    }

    function activeConversation() {
      return conversations.find((conversation) => conversation.id === activeConversationId);
    }

    function updateControls() {
      const conversation = activeConversation();
      const pending = Boolean(conversation && conversation.pending);
      sendButton.disabled = pending;
      questionField.disabled = pending;
      resetButton.disabled = pending;
      resetButton.hidden = !conversation || conversation.turns.length === 0;
      const hasTurns = Boolean(conversation && conversation.turns.length);
      welcome.hidden = hasTurns;
      suggestions.hidden = hasTurns;
      chatShell.classList.toggle("is-active", hasTurns);
      renderReturnCalculator();
    }

    function renderTabs() {
      tabsElement.replaceChildren();
      for (const conversation of conversations) {
        const tabItem = document.createElement("div");
        tabItem.className = "conversation-tab-item";
        tabItem.setAttribute("role", "presentation");
        const tab = document.createElement("button");
        tab.className = "conversation-tab";
        tab.type = "button";
        tab.setAttribute("role", "tab");
        tab.id = `conversation-tab-${conversation.id}`;
        tab.setAttribute("aria-controls", "messages");
        tab.setAttribute("aria-selected", String(conversation.id === activeConversationId));
        tab.tabIndex = conversation.id === activeConversationId ? 0 : -1;
        tab.dataset.conversationId = String(conversation.id);
        const title = document.createElement("span");
        title.className = "conversation-tab-title";
        title.textContent = conversation.title;
        tab.append(title);
        tabItem.append(tab);

        if (conversations.length > 1) {
          const close = document.createElement("button");
          close.className = "close-tab";
          close.type = "button";
          close.dataset.closeConversation = String(conversation.id);
          close.setAttribute("aria-label", `Close ${conversation.title}`);
          close.textContent = "×";
          close.disabled = conversation.pending;
          tabItem.append(close);
        }
        tabsElement.append(tabItem);
      }
    }

    function renderConversation() {
      const conversation = activeConversation();
      messages.replaceChildren();
      if (conversation) {
        messages.setAttribute("aria-labelledby", `conversation-tab-${conversation.id}`);
        for (const turn of conversation.turns) {
          appendQuestion(turn.question);
          if (turn.response) {
            if (turn.response.error) appendFailure(turn.response.error);
            else appendAnswer(turn.response, turn.question);
          }
        }
        if (conversation.pending) appendLoading();
      }
      updateControls();
      renderTabs();
    }

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
      turn.innerHTML = '<span class="typing"><i></i><i></i><i></i> Looking through the available sources</span>';
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

    function appendFollowUps(data, container) {
      if (!Array.isArray(data.follow_ups)) return;
      const questions = data.follow_ups.filter((question) =>
        typeof question === "string" && question.trim()
      ).slice(0, 3);
      if (!questions.length) return;
      const section = document.createElement("div");
      section.className = "follow-ups";
      section.setAttribute("aria-label", "Suggested follow-up questions");
      const label = document.createElement("span");
      label.className = "follow-ups-label";
      label.textContent = "More facts from this scheme";
      section.append(label);
      for (const text of questions) {
        const button = document.createElement("button");
        button.className = "follow-up";
        button.type = "button";
        button.dataset.question = text;
        button.textContent = text;
        section.append(button);
      }
      container.append(section);
    }

    function appendChart(chart, citations, container) {
      if (!chart || chart.verified !== true || !Array.isArray(chart.data)
          || chart.data.length < 1 || chart.data.length > 12
          || !Array.isArray(citations) || !citations.some((item) => safeHttpUrl(item.url))) return;
      const rows = chart.data.filter((item) => item
        && typeof item.label === "string" && item.label.trim()
        && typeof item.value === "number" && Number.isFinite(item.value) && item.value >= 0);
      if (rows.length !== chart.data.length) return;
      const maximum = Math.max(...rows.map((item) => item.value));
      const scaleMaximum = Number(chart.scale_max);
      if (maximum <= 0 || !Number.isFinite(scaleMaximum) || scaleMaximum < maximum) return;
      const formatAxisValue = (value) => {
        const number = value.toLocaleString();
        if (chart.unit === "₹") return `₹${number}`;
        if (chart.unit === "₹ Cr") return `₹${number} Cr`;
        if (chart.unit === "%") return `${number}%`;
        return `${number} ${chart.unit || ""}`.trim();
      };

      const figure = document.createElement("figure");
      figure.className = "chart-card";
      const title = document.createElement("figcaption");
      title.className = "chart-title";
      title.textContent = chart.title || "Source data";
      figure.append(title);
      const list = document.createElement("div");
      list.className = "chart-rows";
      list.setAttribute("role", "list");
      for (const item of rows) {
        const row = document.createElement("div");
        row.className = "chart-row";
        row.setAttribute("role", "listitem");
        const name = document.createElement("span");
        name.className = "chart-name";
        name.textContent = item.label;
        const track = document.createElement("span");
        track.className = "chart-track";
        track.setAttribute("aria-hidden", "true");
        const bar = document.createElement("span");
        bar.className = "chart-bar";
        const targetWidth = `${Math.max(0, item.value / scaleMaximum * 100)}%`;
        requestAnimationFrame(() => { bar.style.width = targetWidth; });
        track.append(bar);
        const value = document.createElement("span");
        value.className = "chart-value";
        value.textContent = item.display_value || formatAxisValue(item.value);
        row.append(name, track, value);
        list.append(row);
      }
      figure.append(list);
      const axis = document.createElement("div");
      axis.className = "chart-axis";
      const zero = document.createElement("span");
      zero.textContent = formatAxisValue(0);
      const maximumLabel = document.createElement("span");
      maximumLabel.textContent = formatAxisValue(scaleMaximum);
      axis.append(zero, maximumLabel);
      figure.append(axis);
      if (chart.source_label) {
        const caption = document.createElement("p");
        caption.className = "chart-caption";
        caption.textContent = `Source: ${chart.source_label} · single-fund source value`;
        figure.append(caption);
      }
      container.append(figure);
    }

    function appendMetricCard(metric, citations, container, response) {
      if (!metric || typeof metric.label !== "string"
          || typeof metric.display_value !== "string"
          || typeof metric.value !== "number" || !Number.isFinite(metric.value)
          || !Array.isArray(citations) || !citations.some((item) => safeHttpUrl(item.url))) return;
      const card = document.createElement("section");
      card.className = "metric-card";
      card.setAttribute("aria-label", `${metric.label}: ${metric.display_value}`);
      const label = document.createElement("p");
      label.className = "metric-label";
      label.textContent = metric.label;
      const value = document.createElement("p");
      value.className = "metric-value";
      value.textContent = "0";
      const source = document.createElement("p");
      source.className = "metric-source";
      source.textContent = "Source class only · not a risk, performance, or suitability signal";
      const sourceType = citations.some((item) => item.source_type === "official_amc")
        ? "official"
        : citations.some((item) => ["third_party_fallback", "required_groww_target"]
          .includes(item.source_type))
          ? "third-party"
          : "source";
      const mood = document.createElement("span");
      mood.className = `source-mood${sourceType === "third-party" ? " third-party" : ""}`;
      mood.textContent = sourceType === "official"
        ? "Official AMC source"
        : sourceType === "third-party"
          ? "Third-party source"
          : "Cited source";
      card.append(label, value, source, mood);
      animateMetricValue(value, metric, response);
      container.append(card);
    }

    function appendAnswer(data, question) {
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

      const disclaimer = document.createElement("p");
      disclaimer.className = "non-advice";
      const disclaimerTitle = document.createElement("strong");
      disclaimerTitle.textContent = "Not an investment recommendation";
      disclaimer.append(
        disclaimerTitle,
        document.createTextNode(
          "This response only reflects information available from the cited sources. " +
          "It does not suggest whether you should invest."
        )
      );
      card.append(disclaimer);

      const actions = document.createElement("div");
      actions.className = "answer-actions";
      const readAloud = document.createElement("button");
      readAloud.className = "read-aloud";
      readAloud.type = "button";
      readAloud.textContent = speechSupported ? "Read aloud" : "Read aloud unavailable";
      readAloud.disabled = !speechSupported;
      readAloud.setAttribute("aria-label", speechSupported
        ? "Read this answer aloud" : "Read aloud is not supported in this browser");
      readAloud.addEventListener("click", () => {
        if (!speechSupported) return;
        if (activeSpeechButton === readAloud && window.speechSynthesis.speaking) {
          window.speechSynthesis.cancel();
          readAloud.setAttribute("aria-pressed", "false");
          readAloud.textContent = "Read aloud";
          activeSpeechButton = null;
          return;
        }
        if (activeSpeechButton) {
          activeSpeechButton.setAttribute("aria-pressed", "false");
          activeSpeechButton.textContent = "Read aloud";
          activeSpeechButton = null;
        }
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(answer.textContent);
        utterance.rate = 0.96;
        utterance.pitch = 1;
        utterance.onend = utterance.onerror = () => {
          if (activeSpeechButton === readAloud) {
            readAloud.setAttribute("aria-pressed", "false");
            readAloud.textContent = "Read aloud";
            activeSpeechButton = null;
          }
        };
        readAloud.setAttribute("aria-pressed", "true");
        readAloud.textContent = "Stop reading";
        activeSpeechButton = readAloud;
        window.speechSynthesis.speak(utterance);
      });
      actions.append(readAloud);
      card.append(actions);

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
      details.open = citations.length > 0;
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
          const label = citation.label || href;
          const sourceType = citation.source_type === "official_amc"
            ? "Official AMC"
            : ["third_party_fallback", "required_groww_target"].includes(citation.source_type)
              ? "Third-party source"
              : "";
          link.textContent = `${label}${citation.publisher ? ` · ${citation.publisher}` : ""}${sourceType ? ` (${sourceType})` : ""}`;
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
      if (data.metric || data.chart) {
        const visuals = document.createElement("div");
        visuals.className = "fact-visuals";
        appendMetricCard(data.metric, citations, visuals, data);
        appendChart(data.chart, citations, visuals);
        if (visuals.childElementCount) turn.append(visuals);
      }
      appendFollowUps(data, turn);
      messages.append(turn);
      messages.scrollTop = messages.scrollHeight;
    }

    function appendFailure(messageText) {
      const failure = document.createElement("article");
      failure.className = "turn";
      failure.setAttribute("role", "alert");
      const message = document.createElement("p");
      message.className = "answer-card answer-text";
      message.textContent = messageText;
      failure.append(message);
      messages.append(failure);
    }

    async function submitQuestion(rawQuestion, suggestionButton = null) {
      const question = rawQuestion.trim();
      const conversation = activeConversation();
      if (!question || !conversation || conversation.pending) return;

      const context = conversation.turns
        .find((turn) => turn.response && !["rejected", "refused"].includes(turn.response.status))
        ?.question || "";
      const turn = { question, response: null };
      if (suggestionButton && suggestionButton.dataset.fundId) {
        conversation.fundId = suggestionButton.dataset.fundId;
      }
      let transitionUpdate = null;
      const beginSubmission = () => {
        questionField.value = "";
        conversation.turns.push(turn);
        conversation.pending = true;
        if (conversation.turns.length === 1) {
          conversation.title = question.length > 28 ? `${question.slice(0, 27)}…` : question;
        }
        renderConversation();
      };
      const firstSuggestion = suggestionButton && conversation.turns.length === 0;
      if (firstSuggestion && typeof document.startViewTransition === "function"
          && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        transitionUpdate = document.startViewTransition(beginSubmission).updateCallbackDone;
      } else {
        beginSubmission();
      }
      const conversationId = conversation.id;

      try {
        if (transitionUpdate) await transitionUpdate;
        const response = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question, context })
        });
        if (!response.ok) throw new Error("The request could not be completed. Please try again.");
        turn.response = await response.json();
      } catch (error) {
        turn.response = { error: error.message || "Sorry, that request didn’t go through. Please try again." };
      } finally {
        const completedConversation = conversations.find((item) => item.id === conversationId);
        if (completedConversation) completedConversation.pending = false;
        if (activeConversationId === conversationId) renderConversation();
      }
    }

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      submitQuestion(questionField.value);
    });

    fundCards.addEventListener("click", (event) => {
      const button = event.target.closest("[data-question]");
      if (button) submitQuestion(button.dataset.question || "", button);
    });

    categoryFilter.addEventListener("change", renderFundCatalog);
    amcFilter.addEventListener("change", renderFundCatalog);
    loadFundCatalog();

    messages.addEventListener("click", (event) => {
      const button = event.target.closest("[data-question]");
      if (button) submitQuestion(button.dataset.question || "", button);
    });

    document.getElementById("new-conversation").addEventListener("click", () => {
      window.speechSynthesis?.cancel();
      activeSpeechButton = null;
      const conversation = { id: nextConversationId++, title: "New chat", turns: [], pending: false };
      conversations.push(conversation);
      activeConversationId = conversation.id;
      questionField.value = "";
      renderConversation();
      questionField.focus();
    });

    tabsElement.addEventListener("click", (event) => {
      const closeButton = event.target.closest("[data-close-conversation]");
      if (closeButton) {
        const id = Number(closeButton.dataset.closeConversation);
        const conversation = conversations.find((item) => item.id === id);
        if (!conversation || conversation.pending) return;
        conversations = conversations.filter((item) => item.id !== id);
        if (activeConversationId === id) {
          activeConversationId = conversations[0].id;
          questionField.value = "";
        }
        window.speechSynthesis?.cancel();
        activeSpeechButton = null;
        renderConversation();
        return;
      }
      const tab = event.target.closest("[data-conversation-id]");
      if (tab) {
        window.speechSynthesis?.cancel();
        activeSpeechButton = null;
        activeConversationId = Number(tab.dataset.conversationId);
        questionField.value = "";
        renderConversation();
      }
    });

    tabsElement.addEventListener("keydown", (event) => {
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
      const current = event.target.closest("[role='tab']");
      if (!current) return;
      const tabs = Array.from(tabsElement.querySelectorAll("[role='tab']"));
      const currentIndex = tabs.indexOf(current);
      const direction = event.key === "ArrowRight" ? 1 : -1;
      const next = tabs[(currentIndex + direction + tabs.length) % tabs.length];
      event.preventDefault();
      next.focus();
      next.click();
    });

    resetButton.addEventListener("click", () => {
      const conversation = activeConversation();
      if (!conversation || conversation.pending) return;
      window.speechSynthesis?.cancel();
      activeSpeechButton = null;
      conversation.turns = [];
      conversation.title = "New chat";
      conversation.fundId = null;
      questionField.value = "";
      renderConversation();
      questionField.focus();
    });

    const readAloudDialog = document.getElementById("read-aloud-dialog");
    document.getElementById("dismiss-read-aloud").addEventListener("click", () => {
      readAloudDialog.close();
      try {
        window.sessionStorage.setItem("chatterbox-read-aloud-intro-seen", "true");
      } catch {
        // The introduction remains available on the next visit when session storage is disabled.
      }
    });
    let showReadAloudIntro = true;
    try {
      showReadAloudIntro = window.sessionStorage.getItem("chatterbox-read-aloud-intro-seen") !== "true";
    } catch {
      showReadAloudIntro = true;
    }
    if (showReadAloudIntro && typeof readAloudDialog.showModal === "function") readAloudDialog.showModal();
    for (const input of [calculatorMonthly, calculatorYears, calculatorRate]) {
      input.addEventListener("input", renderReturnCalculator);
    }
    renderConversation();
  </script>
</body>
</html>"""
