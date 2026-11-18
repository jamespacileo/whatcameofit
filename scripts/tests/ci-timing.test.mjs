// Tests for scripts/ci-timing.mjs against synthetic recorded API answers
// (scripts/tests/fixtures/ci-timing/answers.mjs). No network: every answer is read from a
// file, and a path with no recorded answer fails the test.
//
//   node --test scripts/tests/ci-timing.test.mjs
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';

import {
  classify,
  collect,
  decidingPath,
  main,
  percentile,
  recordedSource,
  report,
  verdict,
} from '../ci-timing.mjs';
import {
  REPO,
  answers,
  deployingRun,
  job,
  previewRun,
  pullRequestRun,
  reusedRun,
  run,
  simpleJob,
} from './fixtures/ci-timing/answers.mjs';

const budgets = {
  window: 20,
  scenarios: [
    { id: 'deploying', title: 'Deploying', limit: { p50: 120, p90: 180 }, target: { p50: 15 } },
    { id: 'pull-request-checks', title: 'Pull request checks', limit: { p50: 120, p90: 150 }, target: { p50: 15 } },
    { id: 'preview-published', title: 'Preview', limit: { p50: 60, p90: 90 }, target: { p50: 15 } },
    { id: 'unchanged-inputs', title: 'Unchanged', limit: { p50: 30, p90: 45 }, target: { p50: 10 } },
  ],
};

const total = (path) => path.entries.reduce((sum, e) => sum + e.seconds, 0);

function withRecorded(cases, fn) {
  const dir = mkdtempSync(join(tmpdir(), 'ci-timing-'));
  try {
    const file = join(dir, 'answers.json');
    writeFileSync(file, JSON.stringify(answers(cases)));
    writeFileSync(join(dir, 'budgets.json'), JSON.stringify(budgets));
    return fn(file, join(dir, 'budgets.json'));
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

function runMain(args) {
  const lines = [];
  const code = main(args, (line) => lines.push(line));
  return { code, output: lines.join('\n') };
}

test('a deploying run is classified and its path walks back through the jobs it needed', () => {
  const { run: r, jobs } = deployingRun(0, { checks: 60 });
  assert.equal(classify(r, jobs), 'deploying');
  const path = decidingPath(r, jobs);
  assert.deepEqual(path.onPath, ['Production build rehearsal', 'Tests and build', 'Deploy production']);
  assert.equal(path.wall, 94);
  assert.equal(total(path), path.wall);
});

test('a push that passed and did not deploy because a newer revision existed is not a deploying run', () => {
  const superseded = deployingRun(0, { deployConclusion: 'skipped' });
  assert.equal(classify(superseded.run, superseded.jobs), null);
  const deployed = deployingRun(500);
  const found = collect({ api: recordedSource(fileFor({ 'ci.yml': [superseded, deployed] })), repo: REPO, budgets });
  const deploying = found.scenarios.find((s) => s.budget.id === 'deploying');
  assert.deepEqual(
    deploying.runs.map((r) => r.id),
    [deployed.run.id],
  );
  assert.equal(found.superseded, 1);
});

test('of two jobs side by side, the longer decides the run and the shorter is shown off the path', () => {
  const { run: r, jobs } = deployingRun(0, { checks: 60 });
  const path = decidingPath(r, jobs);
  assert.ok(path.onPath.includes('Production build rehearsal'));
  const shorter = path.offPath.find((j) => j.name === 'Pipeline tests 1');
  assert.ok(shorter, 'the shorter job is listed as not on the deciding path');
  assert.equal(shorter.seconds, 23);
  assert.ok(path.entries.every((e) => e.job !== 'Pipeline tests 1'));
});

test('seconds between one job finishing and the next starting are waiting, not inside a step', () => {
  const r = run({ name: 'CI and deploy', event: 'pull_request', branch: 'feature', created: 0 });
  const first = simpleJob('Site build tests 1', 1, 2, 30); // finishes at 35
  const next = simpleJob('Tests and build', 47, 47, 1); // created 12 s later, starts at once
  const path = decidingPath(r, [first, next]);
  const between = path.entries.filter((e) => e.label === 'Waiting between jobs' && e.job === 'Tests and build');
  assert.deepEqual(
    between.map((e) => e.seconds),
    [12],
  );
  const step = path.entries.find((e) => e.label === 'Tests and build › Set up job');
  assert.equal(step.seconds, 2);
  assert.equal(total(path), path.wall);
  assert.equal(path.wall, 51);
});

test('a runner that starts late is waiting for a runner, and a re-run is timed from its attempt', () => {
  const r = run({ name: 'CI and deploy', event: 'pull_request', branch: 'feature', created: 0, attempt: 2, startedAt: 1000 });
  const only = simpleJob('Site build tests 1', 1001, 1010, 20);
  const path = decidingPath(r, [only]);
  assert.equal(path.wall, 33);
  assert.equal(path.entries.find((e) => e.label === 'Waiting for a runner').seconds, 9);
  assert.equal(total(path), path.wall);
});

test('a step on a job with steps out of order still tiles the job exactly', () => {
  const r = run({ name: 'CI and deploy', event: 'pull_request', branch: 'feature', created: 0 });
  const j = job('Odd', {
    created: 0,
    started: 1,
    completed: 20,
    steps: [
      ['Set up job', 2, 4],
      ['Work', 4, 18],
      ['Complete job', 19, 20],
    ],
  });
  j.steps.reverse();
  const path = decidingPath(r, [j]);
  assert.equal(total(path), 20);
  assert.equal(path.entries.find((e) => e.label === 'Odd › Set up job').seconds, 3);
});

test('fewer than 20 runs give a count and no verdict, and do not fail the command', () => {
  const slow = Array.from({ length: 5 }, (_, i) => deployingRun(i * 1000, { checks: 400 }));
  withRecorded({ 'ci.yml': slow, 'pr-preview.yml': [] }, (file, budgetsFile) => {
    const { code, output } = runMain(['--recorded', file, '--repo', REPO, '--budgets', budgetsFile]);
    assert.equal(code, 0);
    assert.match(output, /Deploying\n {2}5 successful runs\n.*\n {2}No verdict: 5 of the 20 runs needed\./);
  });
});

test('a limit missed at p90 only is reported with p90 as the reason and fails the command', () => {
  assert.deepEqual(
    verdict(budgets.scenarios[0], [...Array(17).fill(100), 200, 200, 200], 20),
    { runs: 20, p50: 100, p90: 200, limit: 'missed', limitMissedAt: ['p90'], target: 'missed' },
  );
  // Fourteen quick deploys, six slow ones: p50 near 100 s, p90 over 180 s.
  const cases = [
    ...Array.from({ length: 14 }, (_, i) => deployingRun(i * 1000, { checks: 66 })),
    ...Array.from({ length: 6 }, (_, i) => deployingRun(20000 + i * 1000, { checks: 166 })),
  ];
  withRecorded({ 'ci.yml': cases, 'pr-preview.yml': [] }, (file, budgetsFile) => {
    const { code, output } = runMain(['--recorded', file, '--repo', REPO, '--budgets', budgetsFile]);
    assert.equal(code, 1);
    assert.match(output, /p50 100 s, p90 200 s/);
    assert.match(output, /Limit 120 s at p50, 180 s at p90: missed at p90/);
  });
});

test('a limit met with its target missed are two results, and the command succeeds', () => {
  assert.deepEqual(verdict(budgets.scenarios[1], Array(20).fill(40), 20), {
    runs: 20,
    p50: 40,
    p90: 40,
    limit: 'met',
    limitMissedAt: [],
    target: 'missed',
  });
  const cases = Array.from({ length: 20 }, (_, i) => pullRequestRun(i * 1000, 40));
  withRecorded({ 'ci.yml': cases, 'pr-preview.yml': [] }, (file, budgetsFile) => {
    const { code, output } = runMain(['--recorded', file, '--repo', REPO, '--budgets', budgetsFile]);
    assert.equal(code, 0);
    assert.match(output, /Pull request checks\n {2}20 successful runs\n {2}p50 40 s, p90 40 s/);
    assert.match(output, /Limit 120 s at p50, 150 s at p90: met\n {2}Target 15 s at p50: missed/);
  });
});

test('a limit is met at p50 110 s and p90 140 s', () => {
  const walls = [...Array(9).fill(100), 110, ...Array(7).fill(120), 140, 140, 140];
  assert.equal(percentile(walls, 50), 110);
  assert.equal(percentile(walls, 90), 140);
  assert.equal(verdict(budgets.scenarios[1], walls, 20).limit, 'met');
});

test('failed and cancelled runs are counted and kept out of the percentiles', () => {
  const cases = [
    ...Array.from({ length: 20 }, (_, i) => pullRequestRun(i * 1000, 60)),
    pullRequestRun(500, 900, { conclusion: 'failure' }),
    pullRequestRun(1500, 900, { conclusion: 'cancelled' }),
  ];
  const result = report(
    collect({ api: recordedSource(fileFor({ 'ci.yml': cases, 'pr-preview.yml': [] })), repo: REPO, budgets }),
    20,
  );
  const checks = result.results.find((r) => r.id === 'pull-request-checks');
  assert.equal(checks.failed, 1);
  assert.equal(checks.cancelled, 1);
  assert.equal(checks.p90, 60);
});

test('runs answered by a recorded pass, from either workflow, are the unchanged-inputs scenario', () => {
  const reused = reusedRun(0);
  const kept = previewRun(100, { rebuilt: false });
  const rebuilt = previewRun(200);
  assert.equal(classify(reused.run, reused.jobs), 'unchanged-inputs');
  assert.equal(classify(kept.run, kept.jobs), 'unchanged-inputs');
  assert.equal(classify(rebuilt.run, rebuilt.jobs), 'preview-published');
  const result = report(
    collect({
      api: recordedSource(fileFor({ 'ci.yml': [reused], 'pr-preview.yml': [kept, rebuilt] })),
      repo: REPO,
      budgets,
    }),
    20,
  );
  const unchanged = result.results.find((r) => r.id === 'unchanged-inputs');
  assert.deepEqual(
    unchanged.runs_judged.map((r) => r.id),
    [kept.run.id, reused.run.id],
  );
});

test('one run is shown step by step, with its entries adding up to its wall-clock time', () => {
  const deploy = deployingRun(0);
  withRecorded({ 'ci.yml': [deploy] }, (file, budgetsFile) => {
    const { code, output } = runMain(['--recorded', file, '--repo', REPO, '--budgets', budgetsFile, '--run', String(deploy.run.id)]);
    assert.equal(code, 0);
    assert.match(output, /94 s wall-clock/);
    assert.match(output, /Scenario: deploying/);
    assert.match(output, /Entries add up to 94 s/);
    assert.match(output, /Not on the deciding path: Pipeline tests 1/);
  });
});

test('a path with no recorded answer is refused, so nothing is asked of the network', () => {
  withRecorded({ 'ci.yml': [] }, (file) => {
    assert.throws(() => recordedSource(file)('repos/example/thenwhat/actions/runs/1'), /No recorded answer/);
  });
});

// A recorded-answers file that lives for the rest of the test process.
function fileFor(cases) {
  const dir = mkdtempSync(join(tmpdir(), 'ci-timing-'));
  const file = join(dir, 'answers.json');
  writeFileSync(file, JSON.stringify(answers(cases)));
  process.on('exit', () => rmSync(dir, { recursive: true, force: true }));
  return file;
}
