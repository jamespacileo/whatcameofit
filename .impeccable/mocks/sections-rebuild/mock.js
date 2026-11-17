// Mock only. Variants of every claim-page section below "At a glance", drawn from three
// real claims (data.js, cut from the published export). One rule runs through all of
// them, the one "At a glance" follows: in sight, a label and its value with a shape;
// one press, what it means and where it is from; a second press, why it is listed and
// how sure the reading is. The numbers under "The record in brief" are counted by this
// file's own simple rules, not by the site's.
(() => {
  const { icons: I, claims } = window.MOCK;
  const root = document.getElementById("mock");
  const STORE = "sections-rebuild";
  const kept = (() => {
    try {
      return JSON.parse(localStorage.getItem(STORE) || "{}");
    } catch {
      return {};
    }
  })();
  kept.pick ??= {};
  kept.note ??= {};
  kept.claim ??= 1;
  const keep = () => {
    try {
      localStorage.setItem(STORE, JSON.stringify(kept));
    } catch {}
  };
  let C = claims[kept.claim] ?? claims[1];

  // ---------- small helpers
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[ch]);
  const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const parts = (iso) => iso.slice(0, 10).split("-").map(Number);
  const day = (iso) => (iso ? `${parts(iso)[2]}&nbsp;${MONTHS[parts(iso)[1] - 1]}&nbsp;${parts(iso)[0]}` : "");
  const dayShort = (iso) => `${parts(iso)[2]}&nbsp;${MONTHS[parts(iso)[1] - 1]}`;
  const num = (x) => x.toLocaleString("en-GB");
  const count = (k, one, many) => `${num(k)} ${k === 1 ? one : many}`;
  const groupBy = (list, of) => {
    const map = new Map();
    for (const item of list) {
      const name = of(item);
      if (!map.has(name)) map.set(name, []);
      map.get(name).push(item);
    }
    return [...map];
  };
  let serial = 0;
  const uid = () => `m${++serial}`;

  // ---------- shared parts
  const chev = `<span class="chev" aria-hidden="true">${I.chev}</span>`;
  const c = (html, cls = "") => `<span class="c ${cls}">${html}</span>`;
  const quiet = (html) => `<span class="m-quiet">${html}</span>`;
  const stateMark = (state, extra = "") => `<span class="state-mark ${extra}" data-state="${state}" aria-hidden="true"></span>`;
  const bar = (k, of) => `<span class="m-bar" role="img" aria-label="${k} of ${of}"><span style="width:${of ? Math.max(k ? 3 : 0, (k / of) * 100) : 0}%"></span></span>`;
  const score = (x) => {
    const pct = Math.round(x * 100);
    const band = pct >= 80 ? "high" : pct >= 50 ? "medium" : "low";
    return `<span class="m-score${band === "high" ? "" : " low"}">${band}, <b>${pct}%</b></span>`;
  };
  const head = (title, note = "", about = false) =>
    `<div class="fold-head"><h2 class="bar"><button type="button" class="fold" aria-expanded="true"><span class="chev" aria-hidden="true">${I.chev}</span><span>${title}</span></button></h2>${about ? `<span class="m-info">${I.info}</span>` : ""}${note ? `<span class="fold-note">${note}</span>` : ""}</div>`;
  // A row that opens: its cells in sight, what it means one press in, why a press further.
  const row = (cols, cells, more = "", why = null, attrs = "") =>
    `<details class="m-row" ${attrs}><summary style="--cols:${cols}">${cells.join("")}${chev}</summary><div class="m-more">${more}${
      why ? `<details class="m-why"><summary>${why[0]}${I.chevS}</summary><div class="m-why-body">${why[1]}</div></details>` : ""
    }</div></details>`;
  const plain = (cols, cells) => `<div class="m-row m-plain"><div class="m-sum" style="--cols:${cols}">${cells.join("")}</div></div>`;
  const list = (html) => `<div class="m-list">${html}</div>`;
  const group = (label, body, sub = "") => `<div class="m-group"><h3>${label}${sub ? `<small>${sub}</small>` : ""}</h3><div class="m-group-body">${body}</div></div>`;
  const rest = (label, body) => `<details class="papers-rest m-rest"><summary>${label}${I.chevS}</summary>${body}</details>`;
  const pop = (trigger, body, cls = "m-term") => {
    const id = uid();
    return `<button type="button" class="${cls}" popovertarget="${id}" style="anchor-name:--${id}">${trigger}</button><div popover id="${id}" class="pop m-pop" role="note" style="position-anchor:--${id}">${body}</div>`;
  };
  const facts = (pairs) => `<dl class="m-facts">${pairs.filter(([, v]) => v).map(([k, v]) => `<div><dt>${k}</dt><dd>${v}</dd></div>`).join("")}</dl>`;
  const key = (items) => `<p class="m-key">${items.map(([mark, words]) => `<span>${mark}${words}</span>`).join("")}</p>`;
  const link = (href, text) => `<a href="${esc(href)}" target="_blank" rel="noopener">${text}</a>`;
  const LV = "var(--label-col) minmax(0, 1fr)";

  // ---------- words
  const STATE = { not_started: "Not started", under_way: "Under way", completed: "Finished", suspended: "Suspended", terminated: "Stopped early", withdrawn: "Withdrawn", unknown: "State not given" };
  const COMP = { placebo: "a placebo", active: "another treatment", no_treatment: "no treatment", dose: "another dose", sham: "a sham procedure" };
  const KIND = { effect: ["Effect", I.effect], safety: ["Safety", I.safety], how_it_works: ["How it acts", I.how] };
  const WHO = { article: ["The report", I.report], company: ["The company", I.company], researcher: ["A researcher", I.person] };
  const BASIS = { people: "Rests on a study in people.", animals: "Rests on a study in animals.", lab: "Rests on laboratory work.", not_said: "The report did not say what this rests on." };
  const PAPER_KIND = { randomised_trial: "Randomised trial", clinical_trial: "Clinical trial", review: "Review", article: "Article", observational: "Observational study", case_report: "Case report", meta_analysis: "Meta-analysis" };
  const words = (map, code, fallback) => map[code] ?? fallback ?? String(code ?? "").replace(/_/g, " ").replace(/^./, (ch) => ch.toUpperCase());
  const READING = { match: "Read as a study of this treatment for this condition.", not_what_is_tested: "Read as a study that tests something else.", not_a_match: "Read as not about this treatment or condition." };

  // ---------- 1. The record in brief
  const briefParts = () => {
    const b = C.brief;
    const where = `Read directly from ${count(b.trials, "ClinicalTrials.gov record", "ClinicalTrials.gov records")}. Records read ${day(C.checked)}.`;
    return [
      { label: "Tested in people", value: count(b.trials, "trial", "trials"), sub: b.largest ? `${num(b.largest.n)} people in the largest` : "", figure: num(b.trials), unit: "trials in people", viz: "", more: b.largest ? `The largest, ${b.largest.id}, enrolled ${num(b.largest.n)} people who took part, not a planned number.` : "No record states a size.", where },
      { label: "Against a placebo", value: `${b.placebo} of ${b.trials}`, sub: "", figure: `${b.placebo}<small>/${b.trials}</small>`, unit: "name a placebo", viz: bar(b.placebo, b.trials), more: `A placebo looks like the treatment and has no active ingredient. The other ${b.trials - b.placebo} records name no such comparison.`, where },
      { label: "Results posted", value: `${b.posted} of ${b.trials}`, sub: b.latestPosted ? `latest ${day(b.latestPosted)}` : "", figure: `${b.posted}<small>/${b.trials}</small>`, unit: "posted results", viz: bar(b.posted, b.trials), more: b.posted ? `Results are the numbers a sponsor posts to the registry. They are shown under each trial, as posted.` : "No trial has posted results to the registry.", where },
      { label: "Under way", value: `${b.underWay} of ${b.trials}`, sub: "", figure: `${b.underWay}<small>/${b.trials}</small>`, unit: "under way now", viz: bar(b.underWay, b.trials), more: `A trial is under way from its start date until its record says it has finished or stopped.`, where },
      { label: "Approved", value: b.approvals ? count(b.approvals, "decision", "decisions") : "None on record", sub: "", figure: b.approvals ? num(b.approvals) : "0", unit: "regulator decisions", viz: stateMark("not_started"), more: "No regulator’s decision is among this claim’s records. That says what is on record here, not what a regulator will decide.", where: "Read from this claim’s records. Regulators’ databases are not yet searched for every claim." },
    ];
  };
  const brief = {
    A: () =>
      list(
        briefParts()
          .map((p) =>
            row(`var(--label-col) minmax(0, 1fr) 9rem`, [c(p.label, "m-label"), c(`<b>${p.value}</b>${p.sub ? quiet(p.sub) : ""}`, "m-value"), c(p.viz, "m-viz")], `<p>${p.more}</p>`, ["Where this is read from", `<p>${p.where}</p>`]),
          )
          .join(""),
      ),
    B: () =>
      `<div class="m-cells">${briefParts()
        .map((p) => pop(`<span class="m-figure">${p.figure}</span><span class="m-unit">${p.unit}</span>${p.viz && p.viz.includes("m-bar") ? p.viz : ""}`, `<p>${p.more}</p><p class="pop-note">${p.where}</p>`, "m-cell"))
        .join("")}</div>`,
    C: () => {
      const [people, placebo, posted, going, approved] = briefParts();
      // A panel inside a sentence is made of spans: a block would end the paragraph.
      const term = (p, text) => {
        const id = uid();
        return `<button type="button" class="m-term" popovertarget="${id}" style="anchor-name:--${id}">${text}</button><span popover id="${id}" class="pop m-pop" role="note" style="position-anchor:--${id}"><span>${p.more}</span><span class="pop-note">${p.where}</span></span>`;
      };
      const b = C.brief;
      return `<p class="m-sentence">Tested in ${term(people, people.value)}${b.largest ? `, the largest with ${num(b.largest.n)} people` : ""}. ${term(placebo, `${b.placebo} of them`)} name a placebo. ${term(posted, `${b.posted}`)} have posted results${b.latestPosted ? `, the latest on ${day(b.latestPosted)}` : ""}; ${term(going, `${b.underWay}`)} ${b.underWay === 1 ? "is" : "are"} under way. ${term(approved, b.approvals ? "A regulator’s decision" : "No regulator’s decision")} is on record.</p><p class="entry-note m-foot">These describe the records, not the treatment, and are not advice.</p>`;
    },
  };

  // ---------- 2. What the report said
  const sure = (s) => `<span class="m-sure" title="How sure the reading of the report is">${Math.round(s.sure * 100)}%</span>`;
  const firm = (s) => `<span class="tie-mark${s.firm === "fact" ? " listed" : ""}" aria-hidden="true"></span>`;
  const saidMore = (s) => `<p>${words(BASIS, s.basis)} ${s.firm === "fact" ? "Said as a fact." : "Said as a possibility."}</p><p class="entry-note">“${esc(C.article.title)}”, ${esc(C.article.outlet)}, ${day(C.article.date)}</p>`;
  const saidWhy = (s) => ["How sure this reading is", `<p>${score(s.sure)} An automatic check of whether the report says this, as firmly as it is put here, from reading the report on ${day(s.read)}. It is about the reading of the report, not about the treatment.</p>`];
  const said = {
    A: () =>
      key([[`<span class="tie-mark listed"></span>`, "Said as a fact"], [`<span class="tie-mark"></span>`, "Said as a possibility"]]) +
      list(
        groupBy(C.statements, (s) => s.kind)
          .map(([kind, items]) =>
            group(
              `<span class="m-with-ico">${words(KIND, kind, [kind])[1] ?? ""}${words(KIND, kind, [kind.replace(/_/g, " ")])[0]}</span>`,
              items.map((s) => row(`minmax(0, 1fr) 8.5rem 2.6rem`, [c(`${firm(s)}<span>${esc(s.text)}</span>`, "m-stmt"), c(`<span class="m-with-ico">${words(WHO, s.who, ["Someone quoted", I.person])[1]}${words(WHO, s.who, ["Someone quoted"])[0]}</span>`, "m-quiet"), c(sure(s))], saidMore(s), saidWhy(s))).join(""),
            ),
          )
          .join(""),
      ),
    B: () =>
      list(
        groupBy(C.statements, (s) => s.who)
          .map(([who, items]) =>
            group(
              `<span class="m-with-ico">${words(WHO, who, ["Someone quoted", I.person])[1]}${words(WHO, who, ["Someone quoted"])[0]}</span>`,
              items.map((s) => row(`6.8rem minmax(0, 1fr)`, [c(`<span class="m-tag">${words(KIND, s.kind, [s.kind, ""])[1] ?? ""}${words(KIND, s.kind, [s.kind])[0]}</span>`), c(`<span>${esc(s.text)}</span>${s.firm === "fact" ? "" : ` ${quiet("as a possibility")}`}${s.sure < 0.8 ? ` ${score(s.sure)}` : ""}`, "m-stmt")], saidMore(s), saidWhy(s))).join(""),
              count(items.length, "statement", "statements"),
            ),
          )
          .join(""),
      ),
  };

  // ---------- 3. Recorded
  // The export says a trial "started"; the trials' own states call that "under way".
  const evKind = (e) => (e.t === "report" ? "report" : e.t === "trial_registered" ? "registered" : e.t === "trial_results_posted" ? "results" : e.s === "started" ? "under_way" : (e.s ?? "unknown"));
  const EVENT = { registered: "Trial registered", results: "Results posted", report: "News report", not_started: "Not yet started", under_way: "Trial started", completed: "Trial finished", terminated: "Trial stopped early", withdrawn: "Trial withdrawn", suspended: "Trial suspended", unknown: "Trial’s state changed" };
  const evMark = (kind) => (kind === "results" ? `<span class="ev-results" aria-hidden="true"></span>` : kind === "report" ? `<span class="ev-report" aria-hidden="true"></span>` : stateMark(kind === "registered" ? "not_started" : kind));
  const allEvents = () => [...C.events, ...(C.article ? [{ d: C.article.date, t: "report" }] : [])].sort((a, b) => (a.d < b.d ? 1 : -1));
  const eventLines = (events) =>
    `<ul class="m-lines">${events
      .map((e) => `<li>${evMark(evKind(e))}<span class="m-day">${dayShort(e.d)}</span><span>${EVENT[evKind(e)]}</span>${e.id ? link(`https://clinicaltrials.gov/study/${e.id}`, e.id) : quiet(esc(C.article.outlet))}</li>`)
      .join("")}</ul>`;
  const eventKey = () => key([[stateMark("not_started"), "Registered"], [stateMark("under_way"), "Started"], [stateMark("completed"), "Finished"], [stateMark("terminated"), "Stopped early"], [evMark("results"), "Results posted"], [evMark("report"), "News report"]]);
  const promise = () => (C.promises.length ? `<p class="m-promise"><b>Promised</b> ${esc(C.promises[0].text)} ${quiet(C.promises[0].date ? day(C.promises[0].date) : "No date was given, so nothing is held against it.")}</p>` : "");
  const ledger = (events) =>
    list(
      groupBy(events, (e) => e.d.slice(0, 4))
        .map(([year, items]) => row(`var(--label-col) minmax(0, 1fr) 5.5rem`, [c(`<b>${year}</b>`, "m-year"), c(items.slice().reverse().map((e) => evMark(evKind(e))).join(""), "m-marks"), c(count(items.length, "record", "records"), "m-quiet m-end")], eventLines(items), ["Where the dates are from", `<p>Each date is the registry’s own field: first posted, start date, completion date, results first posted. Read ${day(C.checked)}.</p>`]))
        .join(""),
    );
  const recorded = {
    A: () => promise() + eventKey() + ledger(allEvents()),
    B: () => {
      const events = allEvents();
      const first = (kind) => events.filter((e) => evKind(e) === kind).pop();
      const nodes = [
        [first("registered"), "First trial registered"],
        [first("under_way"), "First trial started"],
        [first("report"), "This report"],
        [first("results"), "First results posted"],
        [events[0], "Latest record"],
      ].filter(([e]) => e);
      const seen = new Set();
      const path = nodes
        .sort((a, b) => (a[0].d < b[0].d ? -1 : 1))
        .filter(([e]) => !seen.has(e) && seen.add(e))
        .map(([e, label]) => `<li>${evMark(evKind(e))}<b>${label}</b><span>${day(e.d)}</span></li>`)
        .join("");
      return `${promise()}<ol class="m-path">${path}${C.promises.length ? `<li class="m-path-promise"><span class="ev-promise"></span><b>Promised</b><span>no date given</span></li>` : ""}</ol>${rest(`All ${count(events.length, "record", "records")}, by year`, eventKey() + ledger(events))}`;
    },
    C: () => {
      const events = allEvents();
      const t0 = Date.parse(events[events.length - 1].d);
      const t1 = Date.parse(C.checked);
      const at = (iso) => (((Date.parse(iso) - t0) / (t1 - t0)) * 100).toFixed(2);
      const y0 = Number(events[events.length - 1].d.slice(0, 4)) + 1;
      const y1 = Number(C.checked.slice(0, 4));
      const step = Math.max(1, Math.ceil((y1 - y0 + 1) / 8));
      let years = "";
      for (let y = y0; y <= y1; y += step) years += `<span style="left:${at(`${y}-01-01`)}%">${y}</span>`;
      return `${promise()}<div class="m-axis" role="img" aria-label="${events.length} records by date">${events.map((e) => `<i class="k-${evKind(e)}" style="left:${at(e.d)}%"></i>`).join("")}<div class="m-axis-years">${years}</div></div>${key([[`<i class="m-axis-key k-registered"></i>`, "Registered, below the line"], [`<i class="m-axis-key k-completed"></i>`, "Started, finished or stopped"], [`<i class="m-axis-key k-results"></i>`, "Results posted"], [`<i class="m-axis-key k-report"></i>`, "News report"]])}<h3 class="m-sub">Latest</h3>${list(eventLines(events.slice(0, 3)))}${rest(`All ${count(events.length, "record", "records")}, by year`, ledger(events))}`;
    },
  };

  // ---------- 4. Trials on record
  const maxSize = () => Math.max(1, ...C.trials.map((t) => t.n ?? 0));
  const trialMore = (t) =>
    facts([
      ["Compared with", t.comp.length ? t.comp.map((code) => words(COMP, code)).join(" and ") : "None named in the record"],
      ["Main measure", esc(t.measure)],
      ["Design", [t.alloc === "randomised" ? "Assigned at random" : t.alloc ? "Not assigned at random" : null, t.mask && t.mask !== "none" ? "Blinded" : t.mask ? "Open label" : null].filter(Boolean).join(" · ")],
      ["Run by", esc(t.sponsor)],
      ["Registry’s title", esc(t.title)],
    ]);
  const trialWhy = (t) => ["Why it is listed", `<p>${t.score !== null ? score(t.score) : ""} Read as a study of this treatment for this condition. ${link(t.url, `${t.id} at ClinicalTrials.gov ${I.out}`)}, record read ${day(t.read)}.</p>`];
  const trialRow = (t) =>
    row(
      `8.2rem 4.6rem minmax(7rem, 1fr) minmax(8rem, 12.5rem) 5.4rem`,
      [
        c(`${stateMark(t.state, t.results ? "posted" : "")}${link(t.url, t.id)}`, "m-id"),
        c(t.phase ? `Phase ${t.phase}` : quiet("No phase")),
        c(t.n !== null ? `<b>${num(t.n)}</b> ${quiet(t.planned ? "planned" : "people")}${bar(t.n, maxSize())}` : quiet("Size not stated"), "m-size"),
        c(`${STATE[t.state]}${t.ended ? ` ${quiet(day(t.ended))}` : ""}`),
        c(t.results ? "Results" : "", "m-quiet"),
      ],
      trialMore(t),
      trialWhy(t),
      `id="t-${t.id}"`,
    );
  const trialKey = () => key([[stateMark("not_started"), "Not started"], [stateMark("under_way"), "Under way"], [stateMark("completed"), "Finished"], [stateMark("terminated"), "Halted"], [stateMark("unknown"), "Not given"], [stateMark("completed", "posted"), "Ringed: results posted"]]);
  const shown = (rows, n, label) => rows.slice(0, n).join("") + (rows.length > n ? rest(label(rows.length - n, rows.length), list(rows.slice(n).join(""))) : "");
  const trials = {
    A: () => {
      const order = ["1", "1/2", "2", "2/3", "3", "4", null];
      const columns = order
        .map((phase) => [phase, C.trials.filter((t) => t.phase === phase)])
        .filter(([, items]) => items.length)
        .map(([phase, items]) => `<div class="m-matrix-col"><b>${phase ? `Phase ${phase}` : "No phase"}</b>${quiet(items.length)}<div class="m-dots">${items.map((t) => `<a href="#t-${t.id}" title="${t.id}: ${t.n !== null ? `${num(t.n)} people, ` : ""}${STATE[t.state]}${t.results ? ", results posted" : ""}">${stateMark(t.state, t.results ? "posted" : "")}</a>`).join("")}</div></div>`)
        .join("");
      const rows = C.trials.slice().sort((a, b) => ((a.registered ?? "") < (b.registered ?? "") ? 1 : -1)).map(trialRow);
      return `<div class="m-matrix">${columns}</div>${trialKey()}${list(shown(rows, 5, (k, of) => `The other ${k} of ${of} trials`))}`;
    },
    B: () => {
      const lanes = [["completed"], ["under_way"], ["not_started"], ["terminated", "withdrawn", "suspended"], ["unknown"]];
      const names = ["Finished", "Under way", "Not started", "Halted", "State not given"];
      return (
        key([[`<span class="m-chip m-chip-key"><b>433</b> P3</span>`, "One trial: people, phase"], [stateMark("completed", "posted"), "Ringed: results posted"]]) +
        list(
          lanes
            .map((states, at) => [names[at], states, C.trials.filter((t) => states.includes(t.state)).sort((a, b) => (b.n ?? 0) - (a.n ?? 0))])
            .filter(([, , items]) => items.length)
            .map(([name, states, items]) =>
              group(
                `<span class="m-with-ico">${stateMark(states[0])}${name}</span>`,
                `<div class="m-chips">${items.map((t) => pop(`${t.results ? stateMark(t.state, "posted") : ""}<b>${t.n !== null ? num(t.n) : "?"}</b> ${t.phase ? `P${t.phase}` : "–"}`, `<p><b>${t.id}</b> · ${STATE[t.state]}${t.ended ? ` ${day(t.ended)}` : ""}${t.results ? " · results posted" : ""}</p>${trialMore(t)}<p class="pop-note">${t.score !== null ? score(t.score) : ""} ${link(t.url, `${t.id} at ClinicalTrials.gov`)}</p>`, "m-chip")).join("")}</div>`,
                count(items.length, "trial", "trials"),
              ),
            )
            .join(""),
        )
      );
    },
    C: () => {
      const rows = C.trials.slice().sort((a, b) => (b.n ?? -1) - (a.n ?? -1)).map(trialRow);
      return trialKey() + list(shown(rows, 5, (k, of) => `The other ${k} of ${of} trials, smaller`));
    },
  };

  // ---------- 5. Possible registry records
  const possibleRows = () =>
    C.possible.map((m) => row(`8.2rem minmax(0, 1fr) auto`, [c(`${stateMark("unknown")}${link(m.url, m.id)}`, "m-id"), c(m.title ? esc(m.title) : quiet("Not read from the registry yet"), "m-clamp"), c(score(m.score))], `<p>${words(READING, m.reading)}</p>`, ["Why it is not counted", `<p>A record counts only when it is read as this treatment for this condition and its match is 80% or more. No person has checked these.</p>`]));
  const none = `<p class="m-empty">This claim has no possible records, so the section is not drawn. Try another claim above.</p>`;
  const possible = {
    A: () => (C.possible.length ? `<p class="entry-note m-lede">Not counted in the status.</p>${list(possibleRows().join(""))}` : none),
    B: () => (C.possible.length ? `<p class="m-ghost">… the last rows of “Trials on record” …</p>${rest(`${count(C.possible.length, "possible record", "possible records")}, not counted in the status`, list(possibleRows().join("")))}` : none),
  };

  // ---------- 6. Papers on record
  const tiesOf = (p) => {
    const tied = p.roles.filter((r) => r.role === "trial_result");
    const listed = tied.filter((r) => r.listed === "listed_by_sponsor").length;
    const related = p.roles.find((r) => r.role === "related" && r.score !== null);
    return `${listed ? `<span class="tie"><span class="tie-mark listed"></span>${listed}</span>` : ""}${tied.length - listed ? `<span class="tie"><span class="tie-mark"></span>${tied.length - listed}</span>` : ""}${related ? score(related.score) : ""}`;
  };
  const paperMore = (p) =>
    `<p>${[p.journal ? esc(p.journal) : null, p.year].filter(Boolean).join(" · ")}</p>${p.roles
      .filter((r) => r.role === "trial_result")
      .map((r) => `<p class="m-tie-line"><span class="tie-mark${r.listed === "listed_by_sponsor" ? " listed" : ""}"></span>${r.listed === "listed_by_sponsor" ? "Listed by the sponsor as reporting results of" : "Linked by the registry from PubMed to"} <a href="#t-${r.trial}">${r.trial}</a></p>`)
      .join("")}${p.roles.some((r) => r.role === "related") ? `<p>Found by the literature search.</p>` : ""}`;
  const paperWhy = (p) => ["Its index record", `<p>Europe PMC record read ${day(p.read)}.${p.oa ? " Open access." : ""}</p>`];
  const paperKey = () => key([[`<span class="tie-mark listed"></span>`, "Listed by a trial’s sponsor as its results"], [`<span class="tie-mark"></span>`, "Linked by the registry from PubMed: may or may not be about the study"]]);
  const papers = {
    A: () => {
      const years = groupBy(C.papers.slice().sort((a, b) => (b.year ?? 0) - (a.year ?? 0)), (p) => p.year ?? "No year");
      const groups = years.map(([year, items]) =>
        group(
          `<b class="m-year">${year}</b>`,
          items.slice(0, 3).map((p) => row(`minmax(0, 1fr) 8.2rem 6.4rem`, [c(link(p.url, esc(p.title)), "m-clamp m-title"), c(words(PAPER_KIND, p.kind, "Paper"), "m-quiet"), c(tiesOf(p), "m-ties")], paperMore(p), paperWhy(p))).join("") + (items.length > 3 ? `<p class="m-plus">+ ${items.length - 3} more from ${year}</p>` : ""),
          count(items.length, "paper", "papers"),
        ),
      );
      return paperKey() + list(shown(groups, 4, (k) => `Papers from ${k} earlier years`));
    },
    B: () => {
      const byTrial = new Map();
      for (const p of C.papers) for (const r of p.roles.filter((each) => each.role === "trial_result")) (byTrial.get(r.trial) ?? byTrial.set(r.trial, []).get(r.trial)).push([p, r]);
      const related = C.papers.filter((p) => p.roles.some((r) => r.role === "related"));
      const groups = [...byTrial]
        .sort((a, b) => b[1].length - a[1].length)
        .map(([id, items]) => {
          const trial = C.trials.find((t) => t.id === id);
          return group(
            `<span class="m-with-ico">${trial ? stateMark(trial.state, trial.results ? "posted" : "") : ""}<a href="#t-${id}">${id}</a></span>`,
            items
              .sort((a, b) => (b[0].year ?? 0) - (a[0].year ?? 0))
              .slice(0, 3)
              .map(([p, r]) => row(`minmax(0, 1fr) 3rem 1.2rem`, [c(link(p.url, esc(p.title)), "m-clamp m-title"), c(p.year ?? "", "m-quiet"), c(`<span class="tie-mark${r.listed === "listed_by_sponsor" ? " listed" : ""}"></span>`, "m-ties")], paperMore(p), paperWhy(p)))
              .join("") + (items.length > 3 ? `<p class="m-plus">+ ${items.length - 3} more for this trial</p>` : ""),
            `${trial?.phase ? `Phase ${trial.phase} · ` : ""}${count(items.length, "paper", "papers")}`,
          );
        });
      if (related.length) groups.push(group("Literature search", related.slice(0, 3).map((p) => row(`minmax(0, 1fr) 3rem 6.4rem`, [c(link(p.url, esc(p.title)), "m-clamp m-title"), c(p.year ?? "", "m-quiet"), c(tiesOf(p), "m-ties")], paperMore(p), paperWhy(p))).join("") + (related.length > 3 ? `<p class="m-plus">+ ${related.length - 3} more</p>` : ""), count(related.length, "paper", "papers")));
      return paperKey() + list(shown(groups, 4, (k) => `Papers of ${k} more trials`));
    },
  };

  // ---------- 7. Organisations named
  const roleWords = (r) => (r.role === "sponsor" ? `Sponsor of ${count(r.trials.length, "trial", "trials")}` : "Named in the report");
  const orgBody = (o) => `<p><b>${esc(o.name)}</b></p>${o.roles.map((r) => `<p>${roleWords(r)}${r.trials.length ? `: ${r.trials.map((id) => `<a href="#t-${id}">${id}</a>`).join(", ")}` : ""}</p>`).join("")}<p class="pop-note">${o.known ? "Matched to an open registry’s record of the organisation." : "Not matched to a registry record. Shown by the name its source gave."}</p>`;
  const orgs = {
    A: () => {
      const sorted = C.orgs.slice().sort((a, b) => a.name.localeCompare(b.name));
      const of = (role) => sorted.filter((o) => o.roles.some((r) => r.role === role));
      const chips = (items, role) => `<span class="m-chips">${items.map((o) => pop(`${esc(o.name)}${role === "sponsor" ? ` <b>${o.roles.find((r) => r.role === role).trials.length}</b>` : ""}`, orgBody(o), "m-chip m-chip-name")).join("")}</span>`;
      return list(
        [["named_in_report", "Named in the report", I.report], ["sponsor", "Sponsors", I.trial]]
          .filter(([role]) => of(role).length)
          .map(([role, label, ico]) => plain(LV, [c(`<span class="m-with-ico">${ico}${label}</span>`, "m-label"), c(chips(of(role), role))]))
          .join(""),
      ) + `<p class="entry-note m-foot">In order of name. The figure is how many of this claim’s trials name it as lead sponsor.</p>`;
    },
    B: () =>
      list(
        C.orgs
          .slice()
          .sort((a, b) => a.name.localeCompare(b.name))
          .map((o) => row(`minmax(0, calc(var(--stop-2) - 2.5rem)) minmax(0, 1fr)`, [c(`<b>${esc(o.name)}</b>`), c(o.roles.map((r) => `<span class="tie">${r.role === "sponsor" ? I.trial : I.report}${roleWords(r)}</span>`).join(""), "m-ties m-ties-start")], orgBody(o).replace(/^<p><b>.*?<\/b><\/p>/, "")))
          .join(""),
      ),
  };

  // ---------- 8. Other claims
  const PLACES = ["preclinical_only", "trial_registered", "phase_1", "phase_2", "phase_3", "approved"];
  const stage = (code) => (PLACES.includes(code) ? `<span class="m-stage" aria-hidden="true">${PLACES.map((place) => `<i${place === code ? ' class="on"' : ""}></i>`).join("")}</span>` : `<span class="m-stage m-stage-none" aria-hidden="true"></span>`);
  const others = {
    A: () => list(C.others.map((o) => plain(`minmax(0, 1fr) 14.5rem 6.6rem`, [c(`<a href="#">${esc(o.name)}</a> ${quiet(esc(o.indication))}`, "m-clamp"), c(`${stage(o.code)}${o.status}`, "m-status"), c(day(o.first), "m-quiet m-end")])).join("")) + `<p class="m-foot"><a href="#">All claims in ${esc(C.topic.toLowerCase())}</a></p>`,
    B: () =>
      list(
        groupBy(C.others.slice().sort((a, b) => PLACES.indexOf(b.code) - PLACES.indexOf(a.code)), (o) => o.code)
          .map(([code, items]) => plain(`calc(var(--label-col) + 4rem) minmax(0, 1fr)`, [c(`${stage(code)}${items[0].status}`, "m-status"), c(items.map((o) => `<a href="#">${esc(o.name)}</a> ${quiet(esc(o.indication))}`).join(`<span class="m-dot-sep"> · </span>`))]))
          .join(""),
      ) + `<p class="m-foot"><a href="#">All claims in ${esc(C.topic.toLowerCase())}</a></p>`,
  };

  // ---------- 9. Pass it on, and check again later
  const pill = (ico, text) => `<button type="button" class="share">${ico}${text}</button>`;
  const keepIt = {
    A: () =>
      list(
        [
          ["Share", `${pill(I.copy, "Copy sentence")}${pill(I.copy, "Copy link")}${pill(I.image, "Image")}${pill(I.share, "Post")}`],
          ["Remind me", `${pill(I.clock, "In six months")}${pill(I.clock, "In a year")}${pill(I.clock, `On the anniversary, ${dayShort(C.first)}`)}`],
          ["Follow", `${pill(I.bookmark, "Follow")}${quiet("Lists it on the home page. Kept in this browser only.")}`],
          ["Embed", `${pill(I.code, "Show the status on your page")}`],
        ]
          .map(([label, body]) => plain(LV, [c(label, "m-label"), c(body, "m-actions")]))
          .join(""),
      ),
    B: () => {
      const menu = (ico, text, items) => pop(`${ico}${text}`, `<div class="m-menu">${items.map((item) => `<button type="button">${item}</button>`).join("")}</div>`, "share");
      return `<div class="m-actions m-actions-bar">${pill(I.bookmark, "Follow")}${menu(I.share, "Share", ["Copy sentence", "Copy link", "Square image", "Tall image", "Post to a network"])}${menu(I.clock, "Remind me", ["In six months", "In a year", `On the anniversary, ${dayShort(C.first)}`])}${menu(I.code, "Embed", ["Copy the snippet"])}</div><p class="entry-note m-foot">Following and reminders stay in this browser: no account, nothing sent.</p>`;
    },
  };

  // ---------- the sections
  const SECTIONS = [
    {
      id: "brief",
      title: "The record in brief",
      head: () => head("The record in brief"),
      now: "Six questions written as sentences, answers as prose, in two named groups. A reader must read to find a number.",
      variants: [
        { key: "A", name: "Fact rows", funnel: ["Label, count, a bar for “how many of them”", "What the count means, in one sentence", "Which records it was read from, and when"], render: brief.A },
        { key: "B", name: "Counts strip", funnel: ["Five figures in a row, each with its unit and a bar", "Press a figure: its sentence", "Under the sentence: where it is read from"], render: brief.B },
        { key: "C", name: "One sentence", funnel: ["One plain sentence; each figure is underlined", "Press a figure: its sentence", "Under the sentence: where it is read from"], render: brief.C },
      ],
    },
    {
      id: "said",
      title: "What the report said",
      head: () => head(C.statements.length === 1 ? "What the report said" : "What the report said", count(C.statements.length, "statement", "statements")),
      now: "Each statement is a block of three lines with “The report said:” before it, a sentence about its basis under it and a wide chip. Twelve statements run long.",
      variants: [
        { key: "A", name: "By kind", funnel: ["Kind at the left; the statement; a mark for fact or possibility; who said it", "What it rests on; the report", "How sure the reading is, and what that means"], render: said.A },
        { key: "B", name: "By who said it", funnel: ["Who said it at the left; a kind tag; the statement. A score only when it is not high", "What it rests on; the report", "How sure the reading is"], render: said.B },
      ],
    },
    {
      id: "recorded",
      title: "Recorded",
      head: () => head(C.promises.length ? "Promised and recorded" : "Recorded", `${count(allEvents().length, "record", "records")} · newest first`),
      now: "A strip, two keys, a filter and a table, with the two newest years written out record by record. The strip shows everything but is not what you press.",
      variants: [
        { key: "A", name: "Year ledger", funnel: ["One row a year: a shape for every record, and the count", "That year’s records, one line each", "Where the dates are from"], render: recorded.A },
        { key: "B", name: "Milestones", funnel: ["Five moments on one line: first trial, this report, first results, latest", "All records, by year", "A year’s records, then where dates are from"], render: recorded.B },
        { key: "C", name: "Time axis", funnel: ["Every record on one axis, and the three latest in words", "All records, by year", "A year’s records, then where dates are from"], render: recorded.C },
      ],
    },
    {
      id: "trials",
      title: "Trials on record",
      head: () => head("Trials on record", `${count(C.trials.length, "trial", "trials")} · ${C.brief.posted} with posted results`, true),
      now: "Five columns of two lines each, led by a head count; phase and results are group rows; the measure is cut mid-word. Hard to see how the trials are spread.",
      variants: [
        { key: "A", name: "Matrix, then rows", funnel: ["A shape per trial under its phase; then one line a trial: state, number, phase, size as a bar", "Compared with, main measure, design, who ran it", "Its match score and its registry record"], render: trials.A },
        { key: "B", name: "By state", funnel: ["Trials grouped by state; each a chip: people and phase", "Press a chip: the trial’s facts", "In the same panel: its score and record"], render: trials.B },
        { key: "C", name: "Largest first", funnel: ["The five largest, one line each, sized by a bar", "Compared with, main measure, design, who ran it", "Its match score and its registry record"], render: trials.C },
      ],
    },
    {
      id: "possible",
      title: "Possible registry records",
      head: () => head("Possible registry records", `${C.possible.length} possible`, true),
      now: "A section of its own with a paragraph over it and three lines a record, for records that count for nothing.",
      variants: [
        { key: "A", name: "Quiet rows", funnel: ["A dotted ring, the record’s number, what it is, its score", "How it was read", "Why it is not counted"], render: possible.A },
        { key: "B", name: "Folded into trials", funnel: ["One line at the foot of “Trials on record”; no section", "The rows of variant A", "How it was read; why it is not counted"], render: possible.B },
      ],
    },
    {
      id: "papers",
      title: "Papers on record",
      head: () => head("Papers on record", count(C.papers.length, "paper", "papers"), true),
      now: "Built last pass as rows of title, kind and journal with tie marks. Titles run to four lines, and the list has no order a reader can use.",
      variants: [
        { key: "A", name: "By year", funnel: ["Year at the left; title on one line; kind; how many trials it is tied to, by mark", "Journal; each tie in words", "Its index record and when it was read"], render: papers.A },
        { key: "B", name: "By trial", funnel: ["The trial at the left with its state; its papers, title and year, a mark for the tie", "Journal; each tie in words", "Its index record and when it was read"], render: papers.B },
      ],
    },
    {
      id: "orgs",
      title: "Organisations named",
      head: () => head("Organisations named", `${C.orgs.length} named`, true),
      now: "Built last pass as one row an organisation. Eighteen rows to say “seventeen sponsors and one name in the report”.",
      variants: [
        { key: "A", name: "Two rows of names", funnel: ["Two labels, the names beside them, a sponsor’s number of trials", "Press a name: its part and its trials", "In the same panel: whether a registry knows the name"], render: orgs.A },
        { key: "B", name: "A row each", funnel: ["Name; its part with the drawing of its source", "Its trials; whether a registry knows the name", "None"], render: orgs.B },
      ],
    },
    {
      id: "others",
      title: "Other claims",
      head: () => head(`Other claims in ${C.topic.toLowerCase()}`),
      now: "The home page’s table, with a summary, a column of prose and a strip per claim: a second page inside this one.",
      variants: [
        { key: "A", name: "Slim rows", funnel: ["Treatment and condition; where it stands, as the six places; first reported", "The claim’s own page", "None"], render: others.A },
        { key: "B", name: "By status", funnel: ["A status at the left; the claims at that status beside it", "The claim’s own page", "None"], render: others.B },
      ],
    },
    {
      id: "keep",
      title: "Pass it on · Check again later",
      head: () => head("Keep or pass on"),
      now: "Two sections, a preview image, a paragraph each, and “Follow” a third time.",
      variants: [
        { key: "A", name: "Four labelled rows", funnel: ["Share, Remind me, Follow, Embed: a label and its buttons", "The button does the thing", "None"], render: keepIt.A },
        { key: "B", name: "One bar", funnel: ["Four buttons on one line", "Press one: its choices", "None"], render: keepIt.B },
      ],
    },
  ];

  // ---------- the page
  const picked = (section) => section.variants.find((v) => v.key === kept.pick[section.id]) ?? section.variants[0];
  const sectionHtml = (section, at) => {
    const variant = picked(section);
    return `<header class="mock-head"><p class="mock-n">${at + 1}</p><div><h2>${section.title}</h2><p class="mock-now"><b>Now</b> ${section.now}</p></div></header>
<div class="mock-tabs" role="group" aria-label="Variant of ${section.title}">${section.variants.map((v) => `<button type="button" data-pick="${section.id}:${v.key}" aria-pressed="${v === variant}"><b>${v.key}</b> ${v.name}</button>`).join("")}</div>
<ol class="mock-funnel">${["In sight", "One press", "Second press"].map((step, level) => `<li><b>${step}</b> ${variant.funnel[level]}</li>`).join("")}</ol>
<div class="mock-page"><article class="sheet"><section class="m-sec m-${section.id}">${section.head()}${variant.render()}</section></article></div>
<label class="mock-note"><span>Notes on “${section.title}”</span><textarea data-note="${section.id}" rows="2" placeholder="What to keep, what to change">${esc(kept.note[section.id] ?? "")}</textarea></label>`;
  };
  const render = () => {
    serial = 0;
    root.innerHTML = `<div class="mock-bar">
  <p class="mock-title">Claim page sections: variants</p>
  <fieldset class="mock-set"><legend>Claim</legend>${claims.map((claim, at) => `<label title="${esc(claim.note)}"><input type="radio" name="claim" value="${at}"${claim === C ? " checked" : ""}> ${esc(claim.treatment)}</label>`).join("")}</fieldset>
  <fieldset class="mock-set"><legend>Theme</legend>${[["", "Device"], ["light", "Light"], ["dark", "Dark"]].map(([value, name]) => `<label><input type="radio" name="theme" value="${value}"${(document.documentElement.dataset.theme ?? "") === value ? " checked" : ""}> ${name}</label>`).join("")}</fieldset>
  <button type="button" class="mock-copy" data-copy>Copy my picks and notes</button>
</div>
<div class="mock-intro">
  <h1>Below “At a glance”: nine sections, rebuilt</h1>
  <p>${esc(C.headline)}. <span class="m-quiet">${esc(C.note)}.</span></p>
  <p><b>One rule for every section</b>, the one “At a glance” follows. <b>In sight:</b> a label and its value, a number or a shape where words can go. <b>One press:</b> what it means and where it is from. <b>A second press:</b> why it is listed and how sure the reading is. Nothing is removed from the page; it moves down the funnel.</p>
  ${key([[stateMark("not_started"), "Not started / registered"], [stateMark("under_way"), "Under way"], [stateMark("completed"), "Finished"], [stateMark("terminated"), "Halted"], [stateMark("completed", "posted"), "Ringed: results posted"], [`<span class="tie-mark listed"></span>`, "Tie made by a sponsor; a statement of fact"], [`<span class="tie-mark"></span>`, "Tie made by the registry; a possibility"], [bar(1, 3), "So many of them"]])}
  <p class="m-quiet">Every shape is grey in every state and stands beside words or a number: it says a kind or a state, never a verdict. Pick a variant in each section, write notes under it, then “Copy my picks and notes”.</p>
</div>
${SECTIONS.map((section, at) => `<section class="mock-sec" id="sec-${section.id}">${sectionHtml(section, at)}</section>`).join("")}
<p class="mock-end">Mock data: three claims from the published export. The counts under “The record in brief” are this mock’s own simple sums.</p>`;
  };

  const summary = () =>
    `Section picks (claim page, below “At a glance”):\n${SECTIONS.map((section, at) => {
      const variant = picked(section);
      const note = (kept.note[section.id] ?? "").trim();
      return `${at + 1}. ${section.title}: ${variant.key} (${variant.name})${kept.pick[section.id] ? "" : " [not picked, default]"}${note ? `\n   Notes: ${note}` : ""}`;
    }).join("\n")}`;

  root.addEventListener("click", (event) => {
    const tab = event.target.closest("[data-pick]");
    if (tab) {
      const [id, variantKey] = tab.dataset.pick.split(":");
      kept.pick[id] = variantKey;
      keep();
      const at = SECTIONS.findIndex((section) => section.id === id);
      document.getElementById(`sec-${id}`).innerHTML = sectionHtml(SECTIONS[at], at);
      return;
    }
    const copy = event.target.closest("[data-copy]");
    if (copy) {
      const text = summary();
      const done = () => {
        copy.textContent = "Copied: paste it in the chat";
        setTimeout(() => (copy.textContent = "Copy my picks and notes"), 2500);
      };
      (navigator.clipboard?.writeText(text) ?? Promise.reject()).then(done, () => {
        window.prompt("Copy this and paste it in the chat", text);
      });
    }
  });
  root.addEventListener("input", (event) => {
    const note = event.target.closest("[data-note]");
    if (note) {
      kept.note[note.dataset.note] = note.value;
      keep();
    }
  });
  root.addEventListener("change", (event) => {
    if (event.target.name === "claim") {
      kept.claim = Number(event.target.value);
      C = claims[kept.claim];
      keep();
      const y = scrollY;
      render();
      scrollTo(0, y);
    }
    if (event.target.name === "theme") {
      if (event.target.value) document.documentElement.dataset.theme = event.target.value;
      else delete document.documentElement.dataset.theme;
    }
  });
  window.mockSummary = summary;
  render();
})();
