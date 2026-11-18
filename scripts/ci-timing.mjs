#!/usr/bin/env node
// How long CI takes, judged from GitHub's own records of past runs against the limits and
// targets in scripts/ci-budgets.json (change `fast-ci-and-deploy`, requirement "Time is
// measured from GitHub's records by one command").
//
//   node scripts/ci-timing.mjs                 the report for all four scenarios
//   node scripts/ci-timing.mjs --run <id>      one run's deciding path, step by step
//   node scripts/ci-timing.mjs --since 2026-11-18T00:00:00Z
//                                              only runs created after the change being judged
//   node scripts/ci-timing.mjs --json          the same figures as JSON
//   node scripts/ci-timing.mjs --recorded answers.json
//                                              read recorded API answers instead of asking GitHub
//
// It asks GitHub through `gh api`, so `gh` must be signed in. It exits with status 1 when a
// scenario with a full window of runs misses a limit, and 0 when only targets are missed.
//
// Wall-clock time runs from the run's creation (or, for a re-run, the attempt's start) to
// the completion of its last job. The deciding path is found by walking back from the job
// that finished last: GitHub creates a job when the jobs it needs have finished, so its
// predecessor is the job that finished last at or before that moment. On that path every
// second belongs to exactly one entry: waiting between jobs (the predecessor finished, the
// job was not yet created), waiting for a runner (created, not yet started), or a step
// (from its start to the next step's start; the first step also takes the job's own start).
// The entries of one run therefore add up to its wall-clock time.
//
// The workflow, job and step names below are part of this script's contract with
// .github/workflows/. Renaming one means changing it here and in
// scripts/tests/fixtures/ci-timing/ in the same commit.

import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

export const NAMES = {
  ciWorkflowFile: 'ci.yml',
  ciWorkflow: 'CI and deploy',
  deployJob: 'Deploy production',
  deployStep: 'Deploy reviewed public snapshot',
  lookupJob: 'Look for a tested tree',
  rehearsalJob: 'Production build rehearsal',
  previewWorkflowFile: 'pr-preview.yml',
  previewWorkflow: 'Pull request preview',
  previewJob: 'Publish preview',
  previewBuildStep: 'Build and publish',
};

const WAIT_BETWEEN = 'Waiting between jobs';
const WAIT_RUNNER = 'Waiting for a runner';
// GitHub records times to the second; a job created in the same second its predecessor
// finished can read as one second early.
const TOLERANCE_S = 1;

const here = dirname(fileURLToPath(import.meta.url));

const seconds = (iso) => Date.parse(iso) / 1000;

// ---------------------------------------------------------------- classification

// The scenario a run belongs to, or null. Needs the run's jobs only for a successful run of
// "CI and deploy" or "Pull request preview".
export function classify(run, jobs) {
  const byName = (name) => (jobs ?? []).find((job) => job.name === name);
  const succeeded = run.conclusion === 'success';
  if (run.name === NAMES.ciWorkflow) {
    if (run.event === 'pull_request') {
      if (!succeeded) return 'pull-request-checks';
      const lookup = byName(NAMES.lookupJob);
      const rehearsal = byName(NAMES.rehearsalJob);
      // An earlier pass for the same inputs answered the checks: the lookup found it, and
      // the suites and the rehearsal were skipped.
      if (lookup?.conclusion === 'success' && rehearsal?.conclusion === 'skipped') {
        return 'unchanged-inputs';
      }
      return 'pull-request-checks';
    }
    if ((run.event === 'push' || run.event === 'workflow_dispatch') && run.head_branch === 'main') {
      if (!succeeded) return 'deploying';
      const step = byName(NAMES.deployJob)?.steps?.find((s) => s.name === NAMES.deployStep);
      // A push that passed and did not deploy, because a newer revision existed, is no
      // deploying run.
      return step?.conclusion === 'success' ? 'deploying' : null;
    }
    return null;
  }
  if (run.name === NAMES.previewWorkflow) {
    if (!succeeded) return run.event === 'pull_request' ? 'preview-published' : null;
    const job = byName(NAMES.previewJob);
    if (job?.conclusion !== 'success') return null; // a closed pull request, a fork
    const build = job.steps?.find((s) => s.name === NAMES.previewBuildStep);
    // A copy already made from this commit's inputs is left as it is: nothing is built.
    if (build?.conclusion === 'skipped') return 'unchanged-inputs';
    return 'preview-published';
  }
  return null;
}

// Every scenario a successful run could turn out to be, before its jobs are read.
function possibleScenarios(run) {
  const id = classify({ ...run, conclusion: 'failure' }, null);
  if (id === 'pull-request-checks' || id === 'preview-published') return [id, 'unchanged-inputs'];
  return id ? [id] : [];
}

// ---------------------------------------------------------------- the deciding path

function ranJobs(jobs) {
  return jobs.filter(
    (job) =>
      job.conclusion !== 'skipped' &&
      job.started_at &&
      job.completed_at &&
      seconds(job.completed_at) >= seconds(job.started_at),
  );
}

export function runStart(run) {
  return run.run_attempt > 1 && run.run_started_at ? run.run_started_at : run.created_at;
}

// One run's wall-clock time, split into entries along the path of jobs that decided it.
export function decidingPath(run, jobs) {
  const ran = ranJobs(jobs);
  const start = seconds(runStart(run));
  if (ran.length === 0) return { wall: 0, entries: [], onPath: [], offPath: [] };
  const finish = (job) => seconds(job.completed_at);
  const last = ran.reduce((a, b) =>
    finish(b) > finish(a) || (finish(b) === finish(a) && seconds(b.started_at) > seconds(a.started_at)) ? b : a,
  );
  const chain = [last];
  for (let current = last; ; ) {
    const created = seconds(current.created_at ?? current.started_at);
    const before = ran.filter(
      (job) =>
        !chain.includes(job) &&
        finish(job) <= created + TOLERANCE_S &&
        finish(job) <= seconds(current.started_at) &&
        finish(job) > start,
    );
    if (before.length === 0) break;
    current = before.reduce((a, b) => (finish(b) > finish(a) ? b : a));
    chain.unshift(current);
  }

  const entries = [];
  let cursor = start;
  for (const job of chain) {
    const begun = Math.max(seconds(job.started_at), cursor);
    const created = Math.min(Math.max(seconds(job.created_at ?? job.started_at), cursor), begun);
    entries.push({ label: WAIT_BETWEEN, job: job.name, kind: 'waiting', seconds: created - cursor });
    entries.push({ label: WAIT_RUNNER, job: job.name, kind: 'waiting', seconds: begun - created });
    const steps = [...(job.steps ?? [])]
      .filter((s) => s.started_at && s.completed_at)
      .sort((a, b) => a.number - b.number);
    const end = finish(job);
    if (steps.length === 0) {
      entries.push({ label: `${job.name} › (no steps recorded)`, job: job.name, kind: 'step', seconds: end - begun });
    }
    steps.forEach((step, i) => {
      const from = i === 0 ? begun : Math.max(seconds(step.started_at), begun);
      const next = i + 1 < steps.length ? seconds(steps[i + 1].started_at) : end;
      const to = Math.min(Math.max(next, from), end);
      entries.push({ label: `${job.name} › ${step.name}`, job: job.name, kind: 'step', seconds: to - from });
    });
    cursor = Math.max(end, cursor);
  }
  const wall = finish(last) - start;
  const onPath = chain.map((job) => job.name);
  const offPath = ran
    .filter((job) => !chain.includes(job))
    .map((job) => ({ name: job.name, seconds: finish(job) - seconds(job.started_at), endedBeforeLast: finish(last) - finish(job) }));
  return { wall, entries: entries.filter((e) => e.seconds > 0), onPath, offPath };
}

// ---------------------------------------------------------------- figures

// Nearest rank: the smallest value with at least p% of the values at or below it.
export function percentile(values, p) {
  if (values.length === 0) return null;
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.max(0, Math.ceil((p / 100) * sorted.length) - 1)];
}

export function verdict(budget, walls, window) {
  const p50 = percentile(walls, 50);
  const p90 = percentile(walls, 90);
  if (walls.length < window) {
    return { runs: walls.length, p50, p90, limit: null, target: null, reason: `${walls.length} of ${window} runs` };
  }
  const missed = [];
  if (p50 > budget.limit.p50) missed.push('p50');
  if (p90 > budget.limit.p90) missed.push('p90');
  return {
    runs: walls.length,
    p50,
    p90,
    limit: missed.length === 0 ? 'met' : 'missed',
    limitMissedAt: missed,
    target: p50 <= budget.target.p50 ? 'met' : 'missed',
  };
}

// The median of every entry over the runs it appeared in, largest first. Waiting is summed
// within a run first, so it reads as one figure.
export function whereTheTimeWent(paths) {
  const perLabel = new Map();
  for (const path of paths) {
    const totals = new Map();
    for (const entry of path.entries) totals.set(entry.label, (totals.get(entry.label) ?? 0) + entry.seconds);
    for (const [label, value] of totals) {
      if (!perLabel.has(label)) perLabel.set(label, []);
      perLabel.get(label).push(value);
    }
  }
  return [...perLabel]
    .map(([label, values]) => ({ label, median: percentile(values, 50), runs: values.length }))
    .sort((a, b) => b.median - a.median || a.label.localeCompare(b.label));
}

// ---------------------------------------------------------------- asking GitHub

export function ghSource() {
  return (path) => JSON.parse(execFileSync('gh', ['api', path], { encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 }));
}

export function recordedSource(file) {
  const answers = JSON.parse(readFileSync(file, 'utf8'));
  return (path) => {
    if (!(path in answers)) throw new Error(`No recorded answer for ${path}`);
    return answers[path];
  };
}

const runsPath = (repo, file, page) =>
  `repos/${repo}/actions/workflows/${file}/runs?status=completed&per_page=100&page=${page}`;
const jobsPath = (repo, id) => `repos/${repo}/actions/runs/${id}/jobs?filter=latest&per_page=100`;

export function collect({ api, repo, budgets, since, maxPages = 5 }) {
  const window = budgets.window;
  const found = Object.fromEntries(budgets.scenarios.map((s) => [s.id, { runs: [], unsuccessful: [] }]));
  const workflows = [
    { file: NAMES.ciWorkflowFile, ids: ['deploying', 'pull-request-checks', 'unchanged-inputs'] },
    { file: NAMES.previewWorkflowFile, ids: ['preview-published', 'unchanged-inputs'] },
  ];
  let superseded = 0;
  for (const workflow of workflows) {
    // Runs come newest first; a scenario two workflows feed takes the newest of both below.
    const seen = Object.fromEntries(workflow.ids.map((id) => [id, 0]));
    const full = () => workflow.ids.every((id) => seen[id] >= window);
    for (let page = 1; page <= maxPages && !full(); page++) {
      const runs = api(runsPath(repo, workflow.file, page)).workflow_runs ?? [];
      for (const run of runs) {
        if (full()) break;
        if (run.status !== 'completed') continue;
        if (since && seconds(run.created_at) < seconds(since)) continue;
        if (run.conclusion !== 'success') {
          const id = classify(run, null);
          if (id) found[id].unsuccessful.push({ id: run.id, created_at: run.created_at, conclusion: run.conclusion });
          continue;
        }
        // Ask for the jobs only when the run could still fill a scenario.
        const could = possibleScenarios(run).filter((id) => id in seen);
        if (could.length === 0 || could.every((id) => seen[id] >= window)) continue;
        const jobs = api(jobsPath(repo, run.id)).jobs ?? [];
        const id = classify(run, jobs);
        if (!id) {
          if (run.name === NAMES.ciWorkflow && run.head_branch === 'main') superseded++;
          continue;
        }
        if (seen[id] >= window) continue;
        seen[id]++;
        found[id].runs.push({ id: run.id, created_at: run.created_at, ...decidingPath(run, jobs) });
      }
      if (runs.length < 100) break;
    }
  }
  const newestFirst = (a, b) => seconds(b.created_at) - seconds(a.created_at);
  const scenarios = budgets.scenarios.map((budget) => {
    const runs = found[budget.id].runs.sort(newestFirst).slice(0, window);
    // Failed and cancelled runs over the same span as the counted ones.
    const oldest = runs.length >= window ? seconds(runs.at(-1).created_at) : -Infinity;
    const unsuccessful = found[budget.id].unsuccessful.filter((r) => seconds(r.created_at) >= oldest);
    const cancelled = unsuccessful.filter((r) => r.conclusion === 'cancelled' || r.conclusion === 'skipped').length;
    return { budget, runs, cancelled, failed: unsuccessful.length - cancelled };
  });
  return { scenarios, superseded };
}

export function report({ scenarios, superseded }, window) {
  const results = scenarios.map(({ budget, runs, failed, cancelled }) => ({
    id: budget.id,
    title: budget.title,
    budget,
    failed,
    cancelled,
    ...verdict(
      budget,
      runs.map((r) => r.wall),
      window,
    ),
    breakdown: whereTheTimeWent(runs),
    runs_judged: runs.map((r) => ({ id: r.id, wall: r.wall })),
  }));
  const limitMissed = results.some((r) => r.limit === 'missed');
  return { results, superseded, exitCode: limitMissed ? 1 : 0 };
}

// ---------------------------------------------------------------- text

export function formatReport({ results, superseded }, window) {
  const lines = [];
  for (const r of results) {
    const notCounted = [r.failed && `${r.failed} failed`, r.cancelled && `${r.cancelled} cancelled`]
      .filter(Boolean)
      .join(', ');
    lines.push(`${r.title}`);
    lines.push(`  ${r.runs} successful runs${notCounted ? ` (${notCounted}, not counted)` : ''}`);
    if (r.runs > 0) lines.push(`  p50 ${r.p50} s, p90 ${r.p90} s`);
    const { limit, target } = r.budget;
    if (r.limit === null) {
      lines.push(`  No verdict: ${r.runs} of the ${window} runs needed.`);
    } else {
      const why = r.limit === 'missed' ? ` at ${r.limitMissedAt.join(' and ')}` : '';
      lines.push(`  Limit ${limit.p50} s at p50, ${limit.p90} s at p90: ${r.limit}${why}`);
      lines.push(`  Target ${target.p50} s at p50: ${r.target}`);
    }
    if (r.breakdown.length > 0) {
      lines.push(`  Where the time went (median seconds on the deciding path, runs it appeared in):`);
      for (const b of r.breakdown) lines.push(`    ${String(b.median).padStart(4)}  ${b.label}  (${b.runs})`);
    }
    lines.push('');
  }
  if (superseded) lines.push(`${superseded} push(es) to main passed and did not deploy; not counted.`);
  return lines.join('\n').trimEnd();
}

export function formatRun(run, path, scenario) {
  const lines = [`Run ${run.id} (${run.name}, ${run.event}): ${path.wall} s wall-clock`];
  lines.push(`  Scenario: ${scenario ?? 'none'}`);
  lines.push(`  Deciding path: ${path.onPath.join(' → ')}`);
  for (const e of [...path.entries].sort((a, b) => b.seconds - a.seconds)) {
    const label = e.kind === 'waiting' ? `${e.label} (before ${e.job})` : e.label;
    lines.push(`    ${String(e.seconds).padStart(4)}  ${label}`);
  }
  const total = path.entries.reduce((sum, e) => sum + e.seconds, 0);
  lines.push(`  Entries add up to ${total} s`);
  for (const job of path.offPath) {
    lines.push(`  Not on the deciding path: ${job.name} (${job.seconds} s, ended ${job.endedBeforeLast} s before the last job)`);
  }
  return lines.join('\n');
}

// ---------------------------------------------------------------- command

function repoFromGit() {
  const url = execFileSync('git', ['remote', 'get-url', 'origin'], { encoding: 'utf8', cwd: here }).trim();
  const match = url.match(/([^/:]+)\/([^/]+?)(?:\.git)?$/);
  if (!match) throw new Error(`Cannot read owner and repository from ${url}; pass --repo owner/name`);
  return `${match[1]}/${match[2]}`;
}

export function parseArgs(argv) {
  const args = { json: false };
  for (let i = 0; i < argv.length; i++) {
    const flag = argv[i];
    const value = () => {
      if (i + 1 >= argv.length) throw new Error(`${flag} needs a value`);
      return argv[++i];
    };
    if (flag === '--json') args.json = true;
    else if (flag === '--run') args.run = value();
    else if (flag === '--since') args.since = value();
    else if (flag === '--repo') args.repo = value();
    else if (flag === '--recorded') args.recorded = value();
    else if (flag === '--budgets') args.budgets = value();
    else if (flag === '--max-pages') args.maxPages = Number(value());
    else throw new Error(`Unknown option ${flag}`);
  }
  if (args.since && Number.isNaN(Date.parse(args.since))) throw new Error(`--since is not a date: ${args.since}`);
  return args;
}

export function main(argv, out = console.log) {
  const args = parseArgs(argv);
  const budgets = JSON.parse(readFileSync(args.budgets ?? join(here, 'ci-budgets.json'), 'utf8'));
  const api = args.recorded ? recordedSource(args.recorded) : ghSource();
  const repo = args.repo ?? repoFromGit();
  if (args.run) {
    const run = api(`repos/${repo}/actions/runs/${args.run}`);
    const jobs = api(jobsPath(repo, run.id)).jobs ?? [];
    const path = decidingPath(run, jobs);
    const scenario = classify(run, jobs);
    out(args.json ? JSON.stringify({ run: run.id, scenario, ...path }, null, 2) : formatRun(run, path, scenario));
    return 0;
  }
  const result = report(collect({ api, repo, budgets, since: args.since, maxPages: args.maxPages }), budgets.window);
  out(args.json ? JSON.stringify(result, null, 2) : formatReport(result, budgets.window));
  return result.exitCode;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  try {
    process.exitCode = main(process.argv.slice(2));
  } catch (error) {
    console.error(error.message);
    process.exitCode = 2;
  }
}
