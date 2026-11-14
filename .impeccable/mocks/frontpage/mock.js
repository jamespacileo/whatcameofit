// Front page mocks: one renderer per direction, over the real published export (data.js).
// Wording for statuses is copied from site/src/lib/status.ts; a mock adds no status wording.
(() => {
  const M = window.MOCK;
  const TODAY = M.today;
  const LAST_VISIT = "2026-11-07"; // the one made-up value: a reader who last opened the page a week ago
  const SITE = "https://whatcameofit.com/";

  const LABEL = {
    preclinical_only: "Preclinical only", no_trial_found: "No trial record found", trial_registered: "Trial registered",
    phase_1: "Phase 1 trial", phase_2: "Phase 2 trial", phase_3: "Phase 3 trial", approved: "Approved",
    failed: "Trial missed its primary endpoint", terminated: "Trials ended early", retracted: "Origin paper retracted",
  };
  const GLOSS = {
    preclinical_only: "No trial in people on record", no_trial_found: "Studied in people, no registered trial found",
    trial_registered: "A trial in people is registered", phase_1: "Early trial in people, checking safety",
    phase_2: "Mid-stage trial in people", phase_3: "Large late-stage trial in people", approved: "Approved by a regulator",
    failed: "A trial did not meet its main goal", terminated: "Its trials were stopped early", retracted: "The original paper was retracted",
  };
  const PATH = ["preclinical_only", "trial_registered", "phase_1", "phase_2", "phase_3", "approved"];
  const SHORT = ["Preclinical", "Registered", "Phase 1", "Phase 2", "Phase 3", "Approved"];
  const STAGE = { in_vitro: "Laboratory (in vitro)", animal: "Animal study", early_human: "Early human study", late_human: "Late human study" };
  const REPORTED_FROM = {
    in_vitro: "The report was of laboratory (in vitro) work.", animal: "The report was of an animal study.",
    early_human: "The report was of an early human study.", late_human: "The report was of a late human study.",
  };
  const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

  const esc = (s) => String(s).replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[ch]);
  const fmt = (d) => `<span class="nowrap">${+d.slice(8)} ${MONTHS[+d.slice(5, 7) - 1]} ${d.slice(0, 4)}</span>`;
  const daysBetween = (a, b) => Math.round((Date.parse(b) - Date.parse(a)) / 864e5);
  const shift = (d, n) => new Date(Date.parse(d) + n * 864e5).toISOString().slice(0, 10);
  const plural = (n, one, many = one + "s") => `${n} ${n === 1 ? one : many}`;
  function age(d) {
    const n = daysBetween(d, TODAY);
    if (n < 14) return [n, n === 1 ? "day" : "days"];
    if (n < 60) return [Math.round(n / 7), "weeks"];
    if (n < 365) return [Math.round(n / 30.4), "months"];
    const y = Math.floor(n / 365.25);
    return [y, y === 1 ? "year" : "years"];
  }
  const ago = (d) => { const [n, u] = age(d); return n === 0 ? "today" : `${n} ${u} ago`; };

  const claims = M.claims.map((c) => ({ ...c, art: c.arts[c.arts.length - 1], url: SITE + c.slug }));
  const bySlug = Object.fromEntries(claims.map((c) => [c.slug, c]));
  const newestFirst = [...claims].sort((a, b) => (a.art.d < b.art.d ? 1 : -1));

  function track(code, scale = 1) {
    const at = PATH.indexOf(code);
    if (at < 0) return "";
    const gap = 17 * scale, r = 3 * scale, big = 5.2 * scale, h = 14 * scale, w = gap * 5 + big * 2;
    const dots = PATH.map((_, i) => `<circle cx="${big + i * gap}" cy="${h / 2}" r="${i === at ? big : r}"${i === at ? ' class="at"' : ""}/>`).join("");
    return `<svg class="track" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" role="img" aria-label="Place ${at + 1} of 6, from preclinical to approved"><line x1="${big}" y1="${h / 2}" x2="${w - big}" y2="${h / 2}"/>${dots}</svg>`;
  }
  function outlet(a, withDomain = false) {
    const icon = M.outlets[a.dom];
    const mark = icon ? `<img src="${icon}" alt="">` : `<span class="tile" aria-hidden="true">${esc(a.o[0])}</span>`;
    return `<span class="outlet">${mark}<b>${esc(a.o)}</b>${withDomain ? ` <span>${esc(a.dom)}</span>` : ""}</span>`;
  }
  const chip = (c) => `<span class="chip">${esc(c.topic)}</span>`;
  const quote = (c, a = c.art) => `<a class="q" href="${c.url}" target="_blank" rel="noopener">“${esc(a.t)}”</a>`;
  const isNew = (d) => d > LAST_VISIT;
  const newTag = (d) => (isNew(d) ? ' <span class="tagged">New</span>' : "");
  const moreReports = (c) => (c.arts.length > 1 ? `<span>and ${plural(c.arts.length - 1, "more report")}</span>` : "");

  // What the records add to the headline, in sentences. Every number is counted from the export.
  function learned(c) {
    const out = [];
    const t = c.trials;
    if (c.approval) out.push(`${esc(c.approval.text)} Recorded ${fmt(c.approval.date)}.`);
    if (c.status === "retracted") out.push(`The paper the first reports were about has been retracted. Recorded ${fmt(c.hist[c.hist.length - 1].on)}.`);
    if (t.firstReg) {
      const gap = +c.first.slice(0, 4) - +t.firstReg.slice(0, 4);
      if (gap >= 2) out.push(`Its first trial was registered in ${t.firstReg.slice(0, 4)}, ${gap} years before this report.`);
    }
    if (t.n) {
      const parts = [`${plural(t.n, "trial")} on record`];
      if (t.completed) parts.push(`${t.completed} completed`);
      parts.push(t.results ? `${t.results} with results posted` : "none with results posted");
      out.push(parts.join(", ") + ".");
    } else {
      if (c.quiet) out.push(`No registry record found in the ${c.quiet} years since the report.`);
      out.push(REPORTED_FROM[c.stage]);
    }
    return out;
  }
  // The same, for a layout that already shows the evidence stage in a cell of its own.
  const learnedBesideStage = (c) => learned(c).filter((s) => s !== REPORTED_FROM[c.stage]);
  function promiseText(p) {
    const text = esc(p.text);
    if (!p.date) return text;
    const year = p.date.slice(0, 4);
    return text.includes(year) ? text.replace(year, `<b>${year}</b>`) : `<b>${year}</b>. ${text}`;
  }
  const followPill = () => `<button class="pill" type="button" aria-pressed="false"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 21l-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg><span>Follow</span></button>`;

  // ---------- furniture ----------
  const MARK = `<svg viewBox="8 8 48 48" aria-hidden="true"><path fill="#fff" fill-rule="evenodd" d="M42.38 49.02A22 22 0 1 1 49.02 42.38A1.2 1.2 0 0 0 49.18 43.88L54.36 49.06A3.75 3.75 0 0 1 49.06 54.36L43.88 49.18A1.2 1.2 0 0 0 42.38 49.02ZM47 30.5A16.5 16.5 0 1 0 14 30.5A16.5 16.5 0 1 0 47 30.5Z"/><path d="M29.7 23.75h-6.2a6.75 6.75 0 0 0 0 13.5h6.2z" fill="#f28a62"/><path d="M31.3 23.75h6.2a6.75 6.75 0 0 1 0 13.5h-6.2z" fill="#1687da"/></svg>`;
  const TRIES = ["tooth regrowth", "pig kidney", "Ozempic"];
  function shell(name, slim, body) {
    const approved = claims.filter((c) => c.status === "approved").length;
    const topics = new Set(claims.map((c) => c.topic)).size;
    document.body.innerHTML = `
      <div class="mockbar"><div class="wrap">Mock: “${name}”. Real records from the published export of 13 Nov 2026; links open the live site. <a href="directions.html">All directions</a></div></div>
      <header class="mast"><div class="wrap">
        <a class="name" href="#top">${MARK}<span>What came <b>of it</b><i>?</i></span></a>
        <form class="mini" role="search"><label class="sr" for="mini">Look up</label><input id="mini" placeholder="Paste a link, or search"></form>
        <nav><a href="#top" aria-current="page">Look up</a><a href="#">Topics</a><a href="#">It happened</a></nav>
      </div></header>
      <div class="band${slim ? " slim" : ""}" id="top"><div class="wrap">
        <div><h1>What happened to that breakthrough?</h1>
        <p class="lede">Each reported breakthrough gets a page showing where it stands now and the dated, sourced records that say so.</p></div>
        <form class="lookup" role="search">
          <label for="look">Paste a link to an article, or search by treatment or condition</label>
          <div class="row"><input id="look" placeholder="https://… or tooth regrowth" autocomplete="off"><button class="btn">Look up</button></div>
          <p class="tries">Try: ${TRIES.map((t) => `<button type="button">${t}</button>`).join(", ")}</p>
          <div class="answer" hidden aria-live="polite"></div>
        </form>
      </div></div>
      <main>${body}</main>
      <footer><div class="wrap">
        <p><b>Not medical advice.</b> <b>A registered trial is not a treatment option.</b></p>
        <p class="small">Data: ClinicalTrials.gov, Europe PMC, Crossref. Registries last checked 14 Nov 2026. We will check again.</p>
      </div></footer>`;
    document.title = `${name} · front page mock`;
    if (window.self !== window.top) document.body.classList.add("embedded");
    const tally = document.querySelector("[data-tally]");
    if (tally) tally.innerHTML = `<b>${claims.length}</b> claims tracked in <b>${topics}</b> topics. Approvals on record: <b>${approved}</b> of ${claims.length}. Registries last checked 14 Nov 2026.`;

    const form = document.querySelector(".lookup"), input = form.querySelector("input"), answer = form.querySelector(".answer");
    const run = () => {
      const words = input.value.toLowerCase().split(/\s+/).filter(Boolean);
      if (!words.length) return;
      const hits = claims.filter((c) => {
        const hay = [c.iv, ...c.aka, c.ind, c.head, c.topic, ...c.arts.map((a) => a.t)].join(" ").toLowerCase();
        return words.every((w) => hay.includes(w));
      }).slice(0, 5);
      answer.hidden = false;
      answer.innerHTML = /^https?:/.test(input.value)
        ? "<p>This mock does not read links. Type a treatment or a condition.</p>"
        : hits.length
          ? `<ul>${hits.map((c) => `<li><a href="${c.url}" target="_blank" rel="noopener"><b>${esc(c.iv)}</b></a> · ${esc(c.ind)}<br><span class="status">${LABEL[c.status]}</span> <span class="muted">${GLOSS[c.status]}</span></li>`).join("")}</ul>`
          : `<p>No record found for “${esc(input.value)}”. We say that a lot.</p>`;
    };
    form.addEventListener("submit", (e) => { e.preventDefault(); run(); });
    form.querySelectorAll(".tries button").forEach((b) => b.addEventListener("click", () => { input.value = b.textContent; run(); }));
    document.querySelector(".mini").addEventListener("submit", (e) => { e.preventDefault(); input.value = e.target.querySelector("input").value; window.scrollTo({ top: 0 }); run(); });
    new IntersectionObserver(([entry]) => document.body.classList.toggle("past-band", !entry.isIntersecting)).observe(form);
    document.addEventListener("click", (e) => {
      const pill = e.target.closest(".pill[aria-pressed]");
      if (!pill || pill.dataset.filter !== undefined) return;
      const on = pill.getAttribute("aria-pressed") !== "true";
      pill.setAttribute("aria-pressed", on);
      const word = pill.querySelector("span");
      if (word) word.textContent = on ? "Following" : "Follow";
    });
  }
  const showMore = (list, items, render, step) => {
    let shown = 0;
    const button = list.nextElementSibling;
    const add = () => {
      list.insertAdjacentHTML("beforeend", items.slice(shown, shown + step).map(render).join(""));
      shown += step;
      button.hidden = shown >= items.length;
      button.textContent = `Show ${Math.min(step, items.length - shown)} more of ${items.length}`;
    };
    button.onclick = add;
    list.innerHTML = "";
    add();
  };

  // ---------- 1. Then and now: a stream ----------
  const streamItem = (c) => {
      const facts = learnedBesideStage(c).slice(0, 2).join(" ");
      return `<li class="item">
        <div class="src">${outlet(c.art)}<span>${fmt(c.art.d)}, ${ago(c.art.d)}</span>${moreReports(c)}${chip(c)}${newTag(c.art.d)}</div>
        <h3>${quote(c)}</h3>
        <div class="thennow">
          <div><div class="lab">Evidence when first reported</div><div class="big">${STAGE[c.stage]}</div><div class="gloss">${fmt(c.first)}</div></div>
          <div class="now"><div class="lab">On record now</div><div class="big status">${LABEL[c.status]}</div><div class="gloss">${GLOSS[c.status]}${c.quiet ? `. No signal for ${c.quiet} years` : ""}</div>${track(c.status)}</div>
        </div>
        ${facts ? `<p class="learn">${facts}</p>` : ""}
        ${c.promise ? `<p class="promise"><span class="lab">Promised</span> ${promiseText(c.promise)}</p>` : ""}
        <div class="foot"><span class="claim">${esc(c.iv)} · ${esc(c.ind)}</span><a href="${c.url}" target="_blank" rel="noopener">See the records</a>${followPill()}</div>
      </li>`;
    };
  function stream() {
    const item = streamItem;
    const sorts = streamSorts();
    const reportsSince = claims.flatMap((c) => c.arts).filter((a) => isNew(a.d)).length;
    const recordsSince = M.recent.filter((r) => isNew(r.date)).length;
    const topics = Object.entries(claims.reduce((a, c) => ((a[c.topic] = (a[c.topic] ?? 0) + 1), a), {})).sort((a, b) => b[1] - a[1]).slice(0, 9);
    shell("Then and now", false, `<div class="wrap">
      <p class="tally" data-tally></p>
      <div class="stream">
        <div>
          <div class="tabs" role="tablist">${Object.entries(sorts).map(([k, v], i) => `<button role="tab" aria-selected="${i === 0}">${k}<span>${v.length}</span></button>`).join("")}</div>
          <ol id="list"></ol><button class="pill more" type="button"></button>
        </div>
        <aside class="rail">
          <div class="since"><h2>Since your last visit on 7 Nov 2026</h2><p>${plural(reportsSince, "news report")}, marked <span class="tagged">New</span>. ${recordsSince ? plural(recordsSince, "registry record") : "No registry record"} dated since.</p></div>
          <div><h2>Lately on the registries</h2><ul>${M.recent.slice(0, 6).map((r) => `<li><span class="muted">${fmt(r.date)}</span><br><b>${r.label}</b>: <a href="${SITE + r.slug}" target="_blank" rel="noopener">${esc(bySlug[r.slug].iv)}</a></li>`).join("")}</ul></div>
          <div><h2>Topics</h2><div class="chips">${topics.map(([t, n]) => `<a class="chip" href="#">${esc(t)} ${n}</a>`).join("")}</div></div>
        </aside>
      </div></div>`);
    const list = document.getElementById("list");
    const tabs = [...document.querySelectorAll(".tabs button")];
    const pick = (i) => { tabs.forEach((t, j) => t.setAttribute("aria-selected", i === j)); showMore(list, Object.values(sorts)[i], item, 12); };
    tabs.forEach((t, i) => (t.onclick = () => pick(i)));
    pick(0);
  }

  // ---------- 2. The wire: a dense list ----------
  function wire() {
    const line = (c) => {
      const [n, unit] = age(c.art.d);
      const fact = learned(c)[0];
      return `<li class="line" data-status="${c.status}">
        <div class="age"><b>${n === 0 ? "New" : n}</b><span>${n === 0 ? "today" : unit}</span></div>
        <div><h3>${quote(c)} <span class="dom">${esc(c.art.dom)}</span></h3>
        <p class="meta"><b>${LABEL[c.status]}.</b> ${GLOSS[c.status]}${c.quiet ? `; no signal for ${c.quiet} years` : ""}. ${fact} <span class="nowrap">· ${esc(c.topic)}</span></p></div>
        <div class="side">${track(c.status)}</div></li>`;
    };
    const groups = [];
    for (const c of newestFirst) {
      const recent = c.art.d.slice(0, 4) === TODAY.slice(0, 4);
      const key = recent ? c.art.d.slice(0, 7) : c.art.d.slice(0, 4);
      const title = recent ? `${["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"][+key.slice(5) - 1]} 2026` : `Reported in ${key}`;
      const last = groups[groups.length - 1];
      if (last && last.key === key) last.items.push(c); else groups.push({ key, title, items: [c] });
    }
    const kinds = [
      ["All", () => true],
      ["No trial in people on record", (c) => c.status === "preclinical_only"],
      ["In trials", (c) => ["trial_registered", "phase_1", "phase_2", "phase_3"].includes(c.status)],
      ["Approved", (c) => c.status === "approved"],
      ["No signal for years", (c) => c.quiet],
    ];
    shell("The wire", true, `<div class="wrap">
      <p class="tally" data-tally></p>
      <div class="filters">${kinds.map(([k, f], i) => `<button class="pill" data-filter="${i}" aria-pressed="${i === 0}">${k} <span class="muted">${claims.filter(f).length}</span></button>`).join("")}</div>
      <div id="groups"></div></div>`);
    const draw = (f) => {
      document.getElementById("groups").innerHTML = groups.map((g) => {
        const items = g.items.filter(f);
        return items.length ? `<section><div class="day"><h2>${g.title}</h2><span>${plural(items.length, "headline")}</span></div><ol>${items.map(line).join("")}</ol></section>` : "";
      }).join("");
    };
    document.querySelectorAll("[data-filter]").forEach((b) => (b.onclick = () => {
      document.querySelectorAll("[data-filter]").forEach((o) => o.setAttribute("aria-pressed", o === b));
      draw(kinds[+b.dataset.filter][1]);
    }));
    draw(kinds[0][1]);
  }

  // ---------- 3. Today's edition: finite, dated ----------
  function edition() {
    const brief = (c) => `<li class="brief">
      <div class="src">${outlet(c.art)}<span>${fmt(c.art.d)}</span>${chip(c)}</div>
      <h3>${quote(c)}</h3>
      <div class="now"><span class="status">${LABEL[c.status]}</span><span class="muted">${GLOSS[c.status]}</span>${track(c.status)}</div>
      <p>${learned(c).slice(0, 2).join(" ")}</p></li>`;
    const e = editionData();
    const { thisWeek, next, passed, back, anniv } = e;
    shell("Today’s edition", false, `<div class="wrap">
      ${editionHead(e)}
      <div class="edition">
        <div>
          <section><h2 class="h2">Reported this week, and where each stands</h2><ol>${thisWeek.slice(0, 6).map(brief).join("")}</ol>
            ${thisWeek.length > 6 ? `<p class="note" style="margin-top:.8rem"><a href="#">All ${thisWeek.length} from this week</a></p>` : ""}</section>
          <section><h2 class="h2">One from before</h2><p class="note">Picked by the date, a different one each day. First reported ${ago(back.first)}.</p><ol>${brief(back)}</ol></section>
          <div class="caught"><p><b>That is the record for today.</b></p><p>The registries are read again tomorrow morning. A claim you follow is listed first when its status changes.</p></div>
        </div>
        <div class="side-col">
          <section><h2 class="h2">Dated on the registries lately</h2><ul>${M.recent.slice(0, 7).map((r) => `<li><span class="when">${fmt(r.date)}${r.id ? ` · ${r.id}` : ""}</span><b>${r.label}.</b> <a href="${SITE + r.slug}" target="_blank" rel="noopener">${esc(bySlug[r.slug].iv)}</a> · ${esc(bySlug[r.slug].ind)}</li>`).join("")}</ul></section>
          <section><h2 class="h2">Promised dates coming up</h2><ul>${next.map(promisedItem).join("")}</ul></section>
          ${passed.length ? `<section><h2 class="h2">A promised date now passed</h2><ul>${passed.map(promisedItem).join("")}</ul></section>` : ""}
          <section><h2 class="h2">Next anniversary</h2><ul><li><span class="when">${+anniv.md.slice(3)} ${MONTHS[+anniv.md.slice(0, 2) - 1]}, first reported ${anniv.c.first.slice(0, 4)}</span>${quote(anniv.c)}<br><span class="status">${LABEL[anniv.c.status]}</span> <span class="muted">${anniv.c.quiet ? `No signal for ${anniv.c.quiet} years` : GLOSS[anniv.c.status]}</span></li></ul></section>
        </div>
      </div></div>`);
  }

  // ---------- 4. Said and recorded: the promise ledger ----------
  function promises() {
    const pair = (c) => `<div class="pair">
      <div><div class="src">${outlet(c.art)}<span>${fmt(c.art.d)}</span></div><h3>${quote(c)}</h3>
        <p class="promise">${promiseText(c.promise)}</p></div>
      <div class="rec"><span class="status">${LABEL[c.status]}</span>${track(c.status)}<p class="muted">${GLOSS[c.status]}${c.quiet ? `. No signal for ${c.quiet} years` : ""}</p>
        <p style="margin-top:.4rem">${learned(c).slice(0, 2).join(" ")}</p>
        ${c.latest ? `<ul><li><span>${fmt(c.latest.date)}</span><span>Latest record: ${c.latest.label.toLowerCase()}${c.latest.id ? `, ${c.latest.id}` : ""}</span></li></ul>` : ""}
        <p class="links"><a href="${c.url}" target="_blank" rel="noopener">See the records</a></p></div></div>`;
    const withPromise = claims.filter((c) => c.promise);
    const buckets = new Map();
    for (const c of withPromise.sort((a, b) => ((a.promise.date ?? "9") < (b.promise.date ?? "9") ? -1 : a.art.d < b.art.d ? 1 : -1))) {
      const key = c.promise.date ? c.promise.date.slice(0, 4) : "No date";
      buckets.set(key, [...(buckets.get(key) ?? []), c]);
    }
    const sub = (key, n) => key === "No date" ? `${plural(n, "promise")} with no date named` : +key < +TODAY.slice(0, 4) ? "The date has passed" : +key === +TODAY.slice(0, 4) ? "By the end of this year" : plural(n, "promise");
    shell("Said and recorded", false, `<div class="wrap">
      <p class="tally" data-tally></p>
      <p style="margin-top:1.2rem;max-width:42rem"><b>${withPromise.length} of ${claims.length} reports named a next step.</b> ${withPromise.filter((c) => c.promise.date).length} gave a date. Each is listed by the year it was promised for, beside what the registries hold.</p>
      <div class="ledger-head"><span>Promised for</span><span>What the report said</span><span>What is on record</span></div>
      ${[...buckets].map(([key, items]) => `<section class="due"><div class="yr"><b>${key === "No date" ? "—" : key}</b><span>${sub(key, items.length)}</span></div><div>${items.map(pair).join("")}</div></section>`).join("")}
      <p class="note" style="margin-top:1.4rem">${claims.length - withPromise.length} tracked claims have no promise on record. <a href="#">See all headlines</a></p></div>`);
  }

  // ---------- 5. The path: a board by place ----------
  function path() {
    const cutoff = shift(TODAY, -90);
    const moved = (c) => c.hist.length > 1 && c.hist[c.hist.length - 1].on >= cutoff;
    const card = (c) => {
      const was = moved(c) ? c.hist[c.hist.length - 2] : null;
      return `<li class="card"><h3>${quote(c)}</h3><div class="by">${outlet(c.art)}<span>${fmt(c.art.d)}</span></div>
        ${was ? `<p class="moved"><span class="tagged">Changed</span> Was: ${LABEL[was.code]}. Now: ${LABEL[c.status]}. ${fmt(c.hist[c.hist.length - 1].on)}</p>` : ""}
        ${c.quiet ? `<p class="moved muted">No signal for ${c.quiet} years</p>` : ""}</li>`;
    };
    const column = (code) => {
      const items = newestFirst.filter((c) => c.status === code).sort((a, b) => moved(b) - moved(a));
      return `<section class="col"><header><div class="place"></div><b>${items.length}</b><h2>${LABEL[code]}</h2><p>${GLOSS[code]}</p></header>
        <ol>${items.slice(0, 7).map(card).join("")}</ol>
        ${items.length > 7 ? `<button class="rest" type="button">Show ${items.length - 7} more</button><ol hidden>${items.slice(7).map(card).join("")}</ol>` : ""}</section>`;
    };
    const off = ["no_trial_found", "retracted"].map((code) => { const items = newestFirst.filter((c) => c.status === code); return `<section><h2>${LABEL[code]} <span class="muted">${items.length}</span></h2><ol>${items.map(card).join("")}</ol></section>`; }).join("");
    const pre = claims.filter((c) => c.status === "preclinical_only").length;
    shell("The path", false, `<div class="wrap"><p class="tally" data-tally></p>
      <p style="margin-top:1.2rem;max-width:42rem"><b>${pre} of ${claims.length} reported breakthroughs have no trial in people on record.</b> Every headline sits at the place the records put it today. A claim that changes place is listed first there for ninety days.</p></div>
      <div class="board-wrap"><div class="board">${PATH.map(column).join("")}</div></div>
      <div class="wrap"><div class="offpath">${off}</div></div>`);
    document.querySelectorAll(".rest").forEach((b) => (b.onclick = () => { b.nextElementSibling.hidden = false; b.remove(); }));
  }

  // ---------- 6. Guess first ----------
  function guess() {
    const onPath = newestFirst.filter((c) => PATH.includes(c.status));
    // Deal the list so neighbours differ: one from each place in turn.
    const piles = PATH.map((code) => onPath.filter((c) => c.status === code));
    const dealt = [];
    for (let i = 0; dealt.length < onPath.length; i++) for (const pile of [piles[0], piles[4], piles[2], piles[0], piles[3], piles[1], piles[5]]) { const c = pile.shift(); if (c) dealt.push(c); }
    const item = (c) => `<li class="item guess" data-slug="${c.slug}">
      <div class="src">${outlet(c.art)}<span>${fmt(c.art.d)}, ${ago(c.art.d)}</span>${chip(c)}</div>
      <h3>“${esc(c.art.t)}”</h3>
      <p class="ask">Where do the records put this today?</p>
      <div class="places">${SHORT.map((s, i) => `<button type="button" data-i="${i}">${s}</button>`).join("")}</div>
      <button class="skip" type="button">Just show me</button>
      <div class="reveal" hidden></div></li>`;
    shell("Guess first", false, `<div class="score"><div class="wrap" id="score">Pick the place you expect, then see the record. Kept in this browser only: no account, nothing sent.</div></div>
      <div class="wrap"><ol id="list"></ol><button class="pill more" type="button"></button></div>`);
    const list = document.getElementById("list");
    let seen = 0, matched = 0;
    showMore(list, dealt, item, 10);
    list.addEventListener("click", (e) => {
      const button = e.target.closest(".places button, .skip");
      const li = e.target.closest(".guess");
      if (!button || !li || li.dataset.done) return;
      li.dataset.done = "1";
      const c = bySlug[li.dataset.slug], at = PATH.indexOf(c.status), pick = button.dataset.i === undefined ? null : +button.dataset.i;
      const places = li.querySelector(".places");
      places.classList.add("done");
      places.children[at].classList.add("at");
      if (pick !== null && pick !== at) places.children[pick].classList.add("picked");
      li.querySelector(".ask").textContent = pick === null ? "On record:" : `You expected ${SHORT[pick]}. On record:`;
      li.querySelector(".skip").remove();
      const reveal = li.querySelector(".reveal");
      reveal.hidden = false;
      reveal.innerHTML = `<p><span class="status big">${LABEL[c.status]}</span> <span class="muted">${GLOSS[c.status]}${c.quiet ? `. No signal for ${c.quiet} years` : ""}</span></p>
        <p>${[...learnedBesideStage(c).slice(0, 2), REPORTED_FROM[c.stage]].join(" ")}</p>
        <p><a href="${c.url}" target="_blank" rel="noopener"><b>See the records</b></a> for ${esc(c.iv)}</p>`;
      if (pick !== null) { seen++; if (pick === at) matched++; }
      if (seen) document.getElementById("score").innerHTML = `You have placed <b>${seen}</b>. <b>${matched}</b> matched the record${seen - matched ? `; in ${seen - matched} the record was somewhere else` : ""}. Kept in this browser only.`;
    });
  }

  // ---------- shared by the stream, the edition and the two mixes ----------
  const FULL_MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  const dayName = (d) => { const w = new Date(d); return `${DAYS[w.getUTCDay()]} ${w.getUTCDate()} ${FULL_MONTHS[w.getUTCMonth()]}`; };
  const streamSorts = () => ({
    "Newest": newestFirst,
    "Lately on record": claims.filter((c) => c.latest).sort((a, b) => (a.latest.date < b.latest.date ? 1 : -1)),
    "Longest quiet": claims.filter((c) => c.quiet).sort((a, b) => b.quiet - a.quiet || (a.first < b.first ? -1 : 1)),
    "Promised": claims.filter((c) => c.promise).sort((a, b) => ((a.promise.date ?? "9") < (b.promise.date ?? "9") ? -1 : 1)),
  });
  function editionData() {
    const weekStart = shift(TODAY, -6);
    const thisWeek = newestFirst.filter((c) => c.art.d >= weekStart);
    const reportsOn = (d) => claims.flatMap((c) => c.arts).filter((a) => a.d === d).length;
    const week = Array.from({ length: 7 }, (_, i) => shift(weekStart, i));
    const dated = claims.filter((c) => c.promise?.date).sort((a, b) => (a.promise.date < b.promise.date ? -1 : 1));
    const upcoming = dated.filter((c) => c.promise.date >= TODAY);
    const older = claims.filter((c) => c.first < "2022").sort((a, b) => (a.first < b.first ? -1 : 1));
    const back = older[daysBetween(TODAY.slice(0, 4) + "-01-01", TODAY) % older.length];
    const md = TODAY.slice(5);
    const anniv = older.map((c) => ({ c, md: c.first.slice(5) })).sort((a, b) => ((a.md < md ? "1" : "0") + a.md < (b.md < md ? "1" : "0") + b.md ? -1 : 1))[0];
    return { week, thisWeek, reportsOn, dated, upcoming, next: upcoming.slice(0, 3), passed: dated.filter((c) => c.promise.date < TODAY), back, anniv };
  }
  // The dated head. With `jump`, each day of the strip leads to that day's part of the page.
  const editionHead = (e, jump = false) => `<div class="ed-head">
      <h2>${dayName(TODAY)} ${TODAY.slice(0, 4)}</h2>
      <p>${plural(e.thisWeek.length, "headline")} reported in the last seven days, ${plural(M.recent.filter((r) => r.date >= shift(TODAY, -30)).length, "registry record")} dated in the last thirty. Registries checked this morning.</p>
      <div class="week">${e.week.map((day) => {
        const n = e.reportsOn(day), w = new Date(day), current = day === TODAY ? ' aria-current="date"' : "";
        const inner = `<span class="wd">${DAYS[w.getUTCDay()].slice(0, 3)}</span><span class="dn">${w.getUTCDate()}</span><span class="ct">${n ? plural(n, "report") : "none"}</span>`;
        return jump ? `<a href="#d-${day}"${current}>${inner}</a>` : `<button type="button"${current}>${inner}</button>`;
      }).join("")}</div></div>`;
  const promisedItem = (c) => `<li><span class="when">${esc(c.iv)} · ${esc(c.ind)}</span><p class="promise">${promiseText(c.promise)}</p><span class="status">${LABEL[c.status]}</span> <span class="muted">${GLOSS[c.status]}</span></li>`;
  const recordLine = (r) => `<li><span class="when">${fmt(r.date)}${r.id ? ` · ${r.id}` : ""}</span><b>${r.label}.</b> <a href="${SITE + r.slug}" target="_blank" rel="noopener">${esc(bySlug[r.slug].iv)}</a> · ${esc(bySlug[r.slug].ind)}</li>`;
  function rail() {
    const reportsSince = claims.flatMap((c) => c.arts).filter((a) => isNew(a.d)).length;
    const recordsSince = M.recent.filter((r) => isNew(r.date)).length;
    const topics = Object.entries(claims.reduce((a, c) => ((a[c.topic] = (a[c.topic] ?? 0) + 1), a), {})).sort((a, b) => b[1] - a[1]).slice(0, 9);
    return `<aside class="rail">
      <div class="since"><h2>Since your last visit on 7 Nov 2026</h2><p>${plural(reportsSince, "news report")}, marked <span class="tagged">New</span>. ${recordsSince ? plural(recordsSince, "registry record") : "No registry record"} dated since.</p></div>
      <div><h2>Topics</h2><div class="chips">${topics.map(([t, n]) => `<a class="chip" href="#">${esc(t)} ${n}</a>`).join("")}</div></div>
    </aside>`;
  }

  // ---------- A. Briefing, then stream: the edition is the head, the stream is the body ----------
  function briefing() {
    const e = editionData();
    const sorts = { "This week": e.thisWeek, ...streamSorts() };
    const back = e.back;
    shell("Briefing, then stream", false, `<div class="wrap mix-a">
      ${editionHead(e)}
      <p class="jumps">Also today: <a href="#brief">${M.recent.length} registry records</a>, <a href="#brief">${e.upcoming.length} promised dates</a> and <a href="#brief">one from before</a>.</p>
      <section id="brief" class="brief3 side-col" aria-label="Today’s briefing">
        <div><h2>Dated on the registries lately</h2><ul>${M.recent.slice(0, 3).map(recordLine).join("")}</ul><p class="note"><a href="#">All ${M.recent.length} from the last 45 days</a></p></div>
        <div><h2>Promised dates coming up</h2><ul>${e.next.slice(0, 1).map(promisedItem).join("")}</ul><p class="note"><a href="#">All ${e.upcoming.length} with a date to come</a></p></div>
        <div><h2>One from before</h2><ul><li><span class="when">Picked by the date. First reported ${ago(back.first)}.</span>${quote(back)}<br><span class="status">${LABEL[back.status]}</span> <span class="muted">${back.quiet ? `No signal for ${back.quiet} years` : GLOSS[back.status]}</span></li></ul><p class="note">A different one each day.</p></div>
      </section>
      <div class="stream">
        <div>
          <div class="tabs" role="tablist">${Object.entries(sorts).map(([k, v], i) => `<button role="tab" aria-selected="${i === 0}">${k}<span>${v.length}</span></button>`).join("")}</div>
          <ol id="list"></ol><button class="pill more" type="button"></button>
          <div class="caught" id="end"><p><b>That is this week.</b></p><p>The registries are read again tomorrow morning. A claim you follow is listed first when its status changes.</p><p style="margin-top:.8rem"><button class="pill" type="button" id="earlier">Show earlier headlines</button></p></div>
        </div>
        ${rail()}
      </div></div>`);
    const list = document.getElementById("list"), end = document.getElementById("end");
    const tabs = [...document.querySelectorAll(".tabs button")];
    const pick = (i) => {
      tabs.forEach((t, j) => t.setAttribute("aria-selected", i === j));
      showMore(list, Object.values(sorts)[i], streamItem, 12);
      end.hidden = i !== 0;
    };
    tabs.forEach((t, i) => (t.onclick = () => pick(i)));
    document.getElementById("earlier").onclick = () => { pick(1); tabs[1].scrollIntoView({ block: "start" }); };
    pick(0);
  }

  // ---------- B. Day by day: one list of everything dated, with what is promised ahead of today ----------
  function days() {
    const e = editionData();
    const statusLine = (c) => `<p class="rr-now"><span class="status">${LABEL[c.status]}</span><span class="muted">${c.quiet ? `No signal for ${c.quiet} years` : GLOSS[c.status]}</span>${track(c.status)}</p>`;
    const rows = claims.map((c) => ({ date: c.art.d, order: 0, kind: "report", html: streamItem(c) }));
    for (const r of M.recent) {
      const c = bySlug[r.slug], i = c.hist.findIndex((h) => h.on === r.date);
      const changed = i > 0 ? `<span class="tagged">Changed</span><span>Was: ${LABEL[c.hist[i - 1].code]}. Now: ${LABEL[c.hist[i].code]}.</span>` : `<span>Status now: <span class="status">${LABEL[c.status]}</span></span>`;
      rows.push({ date: r.date, order: 1, kind: "record", html: `<li class="recrow"><div class="lab">Registry record${r.id ? ` · ${r.id}` : ""}</div>
        <p><b>${r.label}.</b> <a href="${c.url}" target="_blank" rel="noopener">${esc(c.iv)}</a> · ${esc(c.ind)}</p>
        <p class="rr-now">${changed}${track(i > 0 ? c.hist[i].code : c.status)}</p></li>` });
    }
    for (const c of e.dated) rows.push({ date: c.promise.date, order: 2, kind: "promise", html: `<li class="prow"><div class="lab">Promised by ${c.promise.date.slice(0, 4)} · ${esc(c.art.o)}, ${fmt(c.art.d)}</div>
        <h3>${quote(c)}</h3><p class="promise">${promiseText(c.promise)}</p>${statusLine(c)}</li>` });
    const a = e.anniv, annivYear = a.md >= TODAY.slice(5) ? +TODAY.slice(0, 4) : +TODAY.slice(0, 4) + 1;
    rows.push({ date: `${annivYear}-${a.md}`, order: 3, kind: "anniversary", html: `<li class="prow"><div class="lab">${+a.md.slice(3)} ${MONTHS[+a.md.slice(0, 2) - 1]} ${annivYear} · ${annivYear - +a.c.first.slice(0, 4)} years since the first report</div>
        <h3>${quote(a.c)}</h3>${statusLine(a.c)}</li>` });
    for (const day of e.week) if (!rows.some((r) => r.date === day)) rows.push({ date: day, order: 4, kind: "quiet", html: `<li class="quiet">Nothing is dated this day. The registries were read that morning.</li>` });
    rows.push({ date: TODAY, order: 5, kind: "before", html: `<li class="lead"><p class="note">One from before, picked by the date: a different one each day. First reported ${ago(e.back.first)}.</p></li>${streamItem(e.back)}` });

    const twoWeeks = shift(TODAY, -13);
    const keyOf = (d) => (d >= twoWeeks ? d : d.slice(0, 4) === TODAY.slice(0, 4) ? d.slice(0, 7) : d.slice(0, 4));
    const titleOf = (k) => k.length === 10 ? (k === TODAY ? "Today, " : k === shift(TODAY, -1) ? "Yesterday, " : "") + dayName(k) : k.length === 7 ? `${FULL_MONTHS[+k.slice(5) - 1]} ${k.slice(0, 4)}` : k;
    const counted = (items) => [["report", "report"], ["record", "registry record"], ["promise", "promised date"]]
      .map(([kind, word]) => [items.filter((r) => r.kind === kind).length, word]).filter(([n]) => n).map(([n, word]) => plural(n, word)).join(", ");
    const ahead = rows.filter((r) => r.date > TODAY).sort((x, y) => (x.date < y.date ? -1 : 1));
    const groups = [];
    for (const row of rows.filter((r) => r.date <= TODAY).sort((x, y) => (x.date === y.date ? x.order - y.order : x.date < y.date ? 1 : -1))) {
      const key = keyOf(row.date), last = groups[groups.length - 1];
      if (last && last.key === key) last.items.push(row); else groups.push({ key, items: [row] });
    }
    shell("Day by day", false, `<div class="wrap">
      ${editionHead(e, true)}
      <div class="stream">
        <div class="daylist">
          <section><div class="day"><h2>Ahead</h2><span>${plural(ahead.length, "date")} that reports promised or that mark a year. A promise is what a report said, not a record.</span></div>
            <p class="note" style="padding-top:.6rem">Next: ${fmt(ahead[0].date)}.</p><button class="rest" type="button">Show the ${ahead.length} dates ahead</button><ol hidden>${ahead.map((r) => r.html).join("")}</ol></section>
          ${groups.map((g) => `<section id="d-${g.key}"><div class="day"><h2>${titleOf(g.key)}</h2><span>${counted(g.items) || "Nothing dated"}</span></div><ol>${g.items.map((r) => r.html).join("")}</ol></section>`).join("")}
        </div>
        ${rail()}
      </div></div>`);
    document.querySelectorAll(".rest").forEach((b) => (b.onclick = () => { b.nextElementSibling.hidden = false; b.remove(); }));
  }

  ({ stream, wire, edition, promises, path, guess, briefing, days })[document.body.dataset.page]();
})();
