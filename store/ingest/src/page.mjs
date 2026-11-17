// The progress page: one file, nothing loaded from anywhere, no count in it. It is the
// same for everyone and is served without a token; the counts come from GET /progress,
// which the page asks with the token typed into it. The token is kept for the tab's
// session only (sessionStorage) and is sent as a header, never in an address. What the
// page shows is put there as text, never as markup. Its words say what was counted and
// nothing more: no verdict on a trial, and a set's name is shown as the pipeline gave it.
export const PAGE = String.raw`<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Store progress</title>
<style>
  :root { color-scheme: light dark; --bg: #f6f5f1; --card: #ffffff; --ink: #1c1b18; --soft: #6b675e; --line: #dcd8cd; --track: #e9e6dd; --fill: #2f6f5e; --part: #9cc5b8; --warn: #9a4a1f; }
  @media (prefers-color-scheme: dark) { :root { --bg: #141412; --card: #1e1d1a; --ink: #eceae3; --soft: #a19c90; --line: #34322d; --track: #2b2925; --fill: #6fbfa8; --part: #3f6f62; --warn: #e0a070; } }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--ink); font: 16px/1.45 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
  main { max-width: 60rem; margin: 0 auto; padding: 1.25rem 1rem 3rem; }
  h1 { font-size: 1.35rem; margin: 0 0 .25rem; }
  h2 { font-size: 1.1rem; margin: 0 0 .5rem; overflow-wrap: anywhere; }
  h3 { font-size: .8rem; margin: 1.1rem 0 .4rem; color: var(--soft); text-transform: uppercase; letter-spacing: .06em; font-weight: 600; }
  p { margin: .25rem 0; }
  .soft { color: var(--soft); font-size: .9rem; }
  .card { background: var(--card); border: 1px solid var(--line); border-radius: .6rem; padding: 1rem; margin-top: 1rem; }
  form { display: flex; gap: .5rem; flex-wrap: wrap; align-items: center; }
  input[type=password] { flex: 1 1 14rem; min-width: 0; font: inherit; padding: .55rem .7rem; border: 1px solid var(--line); border-radius: .4rem; background: var(--bg); color: var(--ink); }
  button { font: inherit; padding: .55rem .9rem; border: 1px solid var(--line); border-radius: .4rem; background: var(--fill); color: var(--card); cursor: pointer; }
  button.plain { background: transparent; color: var(--ink); }
  button:focus-visible, input:focus-visible { outline: 2px solid var(--fill); outline-offset: 2px; }
  .bar { display: grid; grid-template-columns: minmax(7rem, 11rem) 1fr; gap: .15rem .75rem; align-items: center; margin: .45rem 0; }
  .bar .name { font-size: .95rem; }
  .bar .num { grid-column: 2; font-size: .85rem; color: var(--soft); font-variant-numeric: tabular-nums; }
  .track { height: .8rem; background: var(--track); border-radius: .4rem; overflow: hidden; }
  .track > i { display: block; height: 100%; background: var(--fill); width: 0; transition: width .4s ease; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(2.6rem, 1fr)); gap: .35rem; }
  .cell { border: 1px solid var(--line); border-radius: .3rem; padding: .25rem; background: var(--bg); }
  .cell b { display: block; font-size: .7rem; font-weight: 600; color: var(--soft); text-align: center; font-variant-numeric: tabular-nums; }
  .cell i { display: block; height: .22rem; margin-top: .14rem; background: var(--track); border-radius: .1rem; overflow: hidden; }
  .cell i > u { display: block; height: 100%; background: var(--fill); }
  .cell.done { border-color: var(--fill); }
  table { border-collapse: collapse; width: 100%; font-size: .9rem; }
  th, td { text-align: left; padding: .3rem .4rem; border-bottom: 1px solid var(--line); }
  td.n, th.n { text-align: right; font-variant-numeric: tabular-nums; }
  .cols { display: grid; grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr)); gap: 0 1.5rem; }
  .warn { color: var(--warn); }
  .row { display: flex; gap: .75rem; flex-wrap: wrap; align-items: center; justify-content: space-between; }
  [hidden] { display: none !important; }
  @media (prefers-reduced-motion: reduce) { .track > i { transition: none; } }
</style>
</head>
<body>
<main>
  <h1>Store progress</h1>
  <p class="soft">Counts of what has been loaded into the store. Nothing here says anything about a trial or a treatment.</p>

  <section class="card" id="ask">
    <form id="form" autocomplete="off">
      <label for="token" class="soft" style="flex-basis:100%">A token for this service. It stays in this tab and is sent only to this address.</label>
      <input id="token" type="password" inputmode="text" autocapitalize="off" autocorrect="off" spellcheck="false" required>
      <button type="submit">Show progress</button>
    </form>
    <p id="said" class="warn" role="status" aria-live="polite"></p>
  </section>

  <section id="view" hidden>
    <div class="card row">
      <p class="soft" id="when" role="status" aria-live="polite"></p>
      <span>
        <button class="plain" id="again" type="button">Refresh</button>
        <button class="plain" id="forget" type="button">Forget token</button>
      </span>
    </div>
    <div id="sets"></div>
    <div class="card">
      <h2>The store</h2>
      <div class="cols">
        <div><h3>Last merged run, by writer</h3><table id="runs"><thead><tr><th>Writer</th><th class="n">Runs</th><th>Last merged</th></tr></thead><tbody></tbody></table></div>
        <div><h3>Rows, by table</h3><table id="rows"><thead><tr><th>Table</th><th class="n">Rows</th></tr></thead><tbody></tbody></table></div>
      </div>
    </div>
  </section>
</main>
<script>
(function () {
  "use strict";
  var KEY = "thenwhat-store-token";
  var LABELS = { record: "Record fetched", registry_papers: "Registry papers looked for", pubmed_papers: "PubMed asked", in_store: "In the store", page: "Page built" };
  var $ = function (id) { return document.getElementById(id); };
  var el = function (tag, cls, text) { var node = document.createElement(tag); if (cls) node.className = cls; if (text !== undefined) node.textContent = text; return node; };
  var num = function (n) { return typeof n === "number" ? n.toLocaleString("en-GB") : "–"; };
  var share = function (part, whole) { return whole > 0 ? Math.min(100, (100 * part) / whole) : 0; };
  var timer = null;

  function token() { try { return sessionStorage.getItem(KEY); } catch (e) { return null; } }
  function keep(value) { try { if (value) sessionStorage.setItem(KEY, value); else sessionStorage.removeItem(KEY); } catch (e) {} }

  function ask(message) {
    if (timer) { clearInterval(timer); timer = null; }
    $("view").hidden = true; $("ask").hidden = false; $("said").textContent = message || ""; $("token").value = ""; $("token").focus();
  }

  function bar(name, done, of, note) {
    var row = el("div", "bar");
    row.appendChild(el("span", "name", name));
    var track = el("div", "track"); var fill = el("i"); fill.style.width = share(done, of) + "%"; track.appendChild(fill); row.appendChild(track);
    row.appendChild(el("span", "num", num(done) + " of " + num(of) + " trials (" + share(done, of).toFixed(1) + "%)" + (note ? ". " + note : "")));
    return row;
  }

  function draw(data) {
    var sets = $("sets"); sets.textContent = "";
    if (!data.sets.length) { var none = el("div", "card"); none.appendChild(el("p", "soft", "No slice has been reported yet.")); sets.appendChild(none); }
    data.sets.forEach(function (set) {
      var card = el("section", "card");
      card.appendChild(el("h2", "", set.rule + ", " + set.year));
      var of = set.total_trials || set.trials_reported;
      card.appendChild(el("p", "soft", num(set.slices_reported) + " of " + num(set.total_slices) + " slices reported, holding " + num(set.trials_reported) + " of " + num(set.total_trials) + " trials. Last report " + (set.updated_at || "–").slice(0, 19).replace("T", " ") + " UTC."));
      card.appendChild(el("h3", "", "By stage: trials in the slices that have reached it"));
      var notes = {
        registry_papers: num(set.counts.registry_papers) + " trials with a paper the registry lists",
        pubmed_papers: num(set.counts.pubmed_asked) + " trials asked of PubMed, a paper found for " + num(set.counts.pubmed_found),
        in_store: num(set.counts.in_store) + " trials merged into the store"
      };
      data.stages.forEach(function (stage) { card.appendChild(bar(LABELS[stage] || stage, stage === "in_store" ? set.counts.in_store : set.stages[stage].trials, of, stage === "in_store" ? "" : notes[stage])); });
      if (set.groups.length) {
        card.appendChild(el("h3", "", "By group, as the registry describes the trials"));
        set.groups.forEach(function (group) { card.appendChild(bar(group.grp, group.in_store, group.trials, num(group.slices) + " slices; the bar is trials in the store")); });
      }
      card.appendChild(el("h3", "", "By slice (one line a stage, in the order above)"));
      var grid = el("div", "grid");
      set.slices.forEach(function (slice) {
        var part = function (stage) { return stage === "in_store" ? share(slice.in_store, slice.trials) : (slice[stage + "_at"] ? 100 : 0); };
        var whole = data.stages.every(function (stage) { return part(stage) >= 100; });
        var cell = el("div", "cell" + (whole ? " done" : ""));
        cell.title = "Slice " + slice.number + " (" + slice.grp + "), " + num(slice.trials) + " trials: " + data.stages.map(function (stage) { return (LABELS[stage] || stage) + (stage === "in_store" ? " " + num(slice.in_store) : (slice[stage + "_at"] ? " reached" : " not yet")); }).join("; ");
        cell.setAttribute("aria-label", cell.title);
        cell.appendChild(el("b", "", String(slice.number)));
        data.stages.forEach(function (stage) { var line = el("i"); var filled = el("u"); filled.style.width = part(stage) + "%"; line.appendChild(filled); cell.appendChild(line); });
        grid.appendChild(cell);
      });
      card.appendChild(grid);
      sets.appendChild(card);
    });
    var runs = $("runs").tBodies[0]; runs.textContent = "";
    data.runs.forEach(function (run) { var tr = el("tr"); tr.appendChild(el("td", "", run.writer)); tr.appendChild(el("td", "n", num(run.runs))); tr.appendChild(el("td", "", (run.last_merged_at || "–").slice(0, 19).replace("T", " "))); runs.appendChild(tr); });
    var rows = $("rows").tBodies[0]; rows.textContent = "";
    Object.keys(data.rows).filter(function (name) { return data.rows[name] > 0; }).forEach(function (name) { var tr = el("tr"); tr.appendChild(el("td", "", name)); tr.appendChild(el("td", "n", num(data.rows[name]))); rows.appendChild(tr); });
    $("when").textContent = "As of " + (data.at || "").slice(0, 19).replace("T", " ") + " UTC. Refreshed every 30 seconds while this tab is open.";
    $("ask").hidden = true; $("view").hidden = false;
  }

  function load() {
    var held = token();
    if (!held) return ask("");
    fetch("/progress", { headers: { authorization: "Bearer " + held }, cache: "no-store", credentials: "omit" }).then(function (answer) {
      if (answer.status === 401 || answer.status === 403) { keep(null); return ask(answer.status === 401 ? "That token was not accepted." : "That token may not read the progress."); }
      if (answer.status === 429) { $("when").textContent = "Asked too often; trying again shortly."; return null; }
      if (!answer.ok) { $("when").textContent = "The service answered " + answer.status + "; trying again shortly."; return null; }
      return answer.json().then(function (data) { draw(data); if (!timer) timer = setInterval(load, 30000); });
    }).catch(function () { if ($("view").hidden) ask("The service could not be reached."); else $("when").textContent = "The service could not be reached; trying again shortly."; });
  }

  $("form").addEventListener("submit", function (event) { event.preventDefault(); keep($("token").value.trim()); $("said").textContent = ""; load(); });
  $("again").addEventListener("click", load);
  $("forget").addEventListener("click", function () { keep(null); ask("The token was forgotten."); });
  load();
})();
</script>
</body>
</html>
`;
