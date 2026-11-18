// Synthetic GitHub API answers for scripts/tests/ci-timing.test.mjs, in the shape of
// `GET /repos/{repo}/actions/workflows/{file}/runs` and `GET /repos/{repo}/actions/runs/{id}/jobs`.
// Run and job ids are made up; only the fields the timing report reads are kept. Times are
// given in seconds after a fixed origin so each case reads as a timeline.

export const REPO = 'example/thenwhat';
const ORIGIN = Date.parse('2026-11-01T00:00:00Z');

export const at = (s) => new Date(ORIGIN + s * 1000).toISOString().replace('.000Z', 'Z');

let nextId = 1000;

// steps: [[name, start, end, conclusion?], ...] in seconds.
export function job(name, { created, started, completed, conclusion = 'success', steps = [] }) {
  return {
    id: nextId++,
    name,
    status: 'completed',
    conclusion,
    created_at: at(created),
    started_at: at(started),
    completed_at: at(completed),
    steps: steps.map(([stepName, from, to, stepConclusion = 'success'], i) => ({
      name: stepName,
      status: 'completed',
      conclusion: stepConclusion,
      number: i + 1,
      started_at: at(from),
      completed_at: at(to),
    })),
  };
}

export function skippedJob(name, created) {
  return {
    id: nextId++,
    name,
    status: 'completed',
    conclusion: 'skipped',
    created_at: at(created),
    started_at: at(created),
    completed_at: at(created),
  };
}

export function run({ name, event, branch = 'main', created, conclusion = 'success', attempt = 1, startedAt }) {
  return {
    id: nextId++,
    name,
    event,
    status: 'completed',
    conclusion,
    head_branch: branch,
    run_attempt: attempt,
    created_at: at(created),
    run_started_at: at(startedAt ?? created),
  };
}

// A simple job: set-up 2 s, one working step, complete 1 s.
export function simpleJob(name, created, started, work, extra = {}) {
  return job(name, {
    created,
    started,
    completed: started + 3 + work,
    steps: [
      ['Set up job', started, started + 2],
      [extra.step ?? 'Run suite', started + 2, started + 2 + work],
      ['Complete job', started + 2 + work, started + 3 + work],
    ],
  });
}

// A push to main that checks and deploys: two parallel check jobs, the gate, the deploy.
// `checks` is the longer check job's work; the deploy step concludes `deployConclusion`.
export function deployingRun(created, { checks = 60, deployConclusion = 'success', conclusion = 'success' } = {}) {
  const r = run({ name: 'CI and deploy', event: 'push', created, conclusion });
  const t0 = created;
  const long = simpleJob('Production build rehearsal', t0 + 1, t0 + 2, checks, { step: 'Rehearse production build' });
  const short = simpleJob('Pipeline tests 1', t0 + 1, t0 + 2, Math.max(1, checks - 40));
  const gateCreated = t0 + 2 + 3 + checks;
  const gate = simpleJob('Tests and build', gateCreated, gateCreated + 2, 1, { step: 'Require every suite to pass' });
  const deployCreated = gateCreated + 2 + 4;
  const ds = deployCreated + 3;
  const deploy = job('Deploy production', {
    created: deployCreated,
    started: ds,
    completed: ds + 20,
    steps: [
      ['Set up job', ds, ds + 2],
      ['Check this is still the latest main revision', ds + 2, ds + 3],
      ['Deploy reviewed public snapshot', ds + 3, deployConclusion === 'success' ? ds + 15 : ds + 3, deployConclusion],
      ['Check live site', deployConclusion === 'success' ? ds + 15 : ds + 3, ds + 19, deployConclusion],
      ['Complete job', ds + 19, ds + 20],
    ],
  });
  return { run: r, jobs: [skippedJob('Look for a tested tree', t0 + 1), long, short, gate, deploy] };
}

// Pull request checks lasting about `wall` seconds: lookup, one suite, the gate.
export function pullRequestRun(created, wall, { conclusion = 'success' } = {}) {
  const r = run({ name: 'CI and deploy', event: 'pull_request', branch: 'feature', created, conclusion });
  const lookup = simpleJob('Look for a tested tree', created + 1, created + 2, 1, { step: 'Fingerprint the checked inputs' });
  const suiteStart = created + 7;
  const work = Math.max(1, wall - 7 - 3 - 6);
  const suite = simpleJob('Site build tests 1', created + 6, suiteStart, work);
  const gateCreated = suiteStart + 3 + work;
  const gate = simpleJob('Tests and build', gateCreated, gateCreated + 2, 1, { step: 'Require every suite to pass' });
  const rehearsal = simpleJob('Production build rehearsal', created + 6, suiteStart, 5, { step: 'Rehearse production build' });
  return { run: r, jobs: [lookup, suite, rehearsal, gate] };
}

// Pull request checks answered by an earlier pass: the suites and rehearsal are skipped.
export function reusedRun(created) {
  const r = run({ name: 'CI and deploy', event: 'pull_request', branch: 'feature', created });
  const lookup = simpleJob('Look for a tested tree', created + 1, created + 2, 4, { step: 'Verify the prior workflow passed' });
  const gate = simpleJob('Tests and build', created + 9, created + 11, 1, { step: 'Require every suite to pass' });
  return { run: r, jobs: [lookup, skippedJob('Site build tests 1', created + 9), skippedJob('Production build rehearsal', created + 9), gate] };
}

export function previewRun(created, { rebuilt = true } = {}) {
  const r = run({ name: 'Pull request preview', event: 'pull_request', branch: 'feature', created });
  const s = created + 3;
  const buildEnd = rebuilt ? s + 40 : s + 5;
  const publish = job('Publish preview', {
    created: created + 1,
    started: s,
    completed: buildEnd + 3,
    steps: [
      ['Set up job', s, s + 2],
      ['See whether the copy is already this commit\'s', s + 2, s + 5],
      ['Build and publish', s + 5, buildEnd, rebuilt ? 'success' : 'skipped'],
      ['Update the pull request\'s comment', buildEnd, buildEnd + 2],
      ['Complete job', buildEnd + 2, buildEnd + 3],
    ],
  });
  return { run: r, jobs: [publish, skippedJob('Remove preview', created + 1)] };
}

// The recorded answers for a set of runs, as `--recorded` reads them.
export function answers(runsByWorkflow) {
  const out = {};
  for (const [file, cases] of Object.entries({ 'ci.yml': [], 'pr-preview.yml': [], ...runsByWorkflow })) {
    const sorted = [...cases].sort((a, b) => Date.parse(b.run.created_at) - Date.parse(a.run.created_at));
    out[`repos/${REPO}/actions/workflows/${file}/runs?status=completed&per_page=100&page=1`] = {
      total_count: sorted.length,
      workflow_runs: sorted.map((c) => c.run),
    };
    for (const c of sorted) {
      out[`repos/${REPO}/actions/runs/${c.run.id}`] = c.run;
      out[`repos/${REPO}/actions/runs/${c.run.id}/jobs?filter=latest&per_page=100`] = { jobs: c.jobs };
    }
  }
  return out;
}
