// Project adapter around the unchanged, pinned Meterless H-MEM reference.
// This process has no network or inference operations. stdout is JSON only.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { tsImport } from 'tsx/esm/api';

const here = path.dirname(fileURLToPath(import.meta.url));
const revision = fs.readFileSync(path.join(here, 'PINNED_REVISION'), 'utf8').trim();
const manifest = JSON.parse(fs.readFileSync(path.join(here, 'UPSTREAM.json'), 'utf8'));
if (!/^[a-f0-9]{40}$/.test(revision) || manifest.revision !== revision) throw new Error('Invalid H-MEM revision pin');
for (const [name, expected] of Object.entries(manifest.files_sha256)) {
  const actual = createHash('sha256').update(fs.readFileSync(path.join(here, name))).digest('hex');
  if (actual !== expected) throw new Error(`Pinned H-MEM source changed: ${name}`);
}
const { HMEM } = await tsImport('./reference/src/index.ts', import.meta.url);
const constraintFields = new Set(['cash_budget_usd', 'time_budget_weeks', 'team_size', 'technical_skill', 'devops_capacity']);
const canonical = (value) => JSON.stringify(value, function (_key, item) {
  return item && typeof item === 'object' && !Array.isArray(item)
    ? Object.fromEntries(Object.entries(item).sort(([a], [b]) => a.localeCompare(b))) : item;
});
const assert = (condition, message) => { if (!condition) throw new Error(message); };

function exportRecord(record, scope) {
  return {
    memory_id: `${scope}:${record.id}`, project_scope: scope,
    payload: JSON.parse(record.content), source: record.source,
    provenance: record.provenance,
    superseded_by: record.supersededBy ? `${scope}:${record.supersededBy}` : null,
  };
}

async function dispatch(request) {
  const { operation, project_scope: scope, payload = {}, storage } = request;
  assert(['remember_confirmed', 'recall', 'audit'].includes(operation), 'Unsupported operation');
  assert(typeof scope === 'string' && /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(scope), 'Invalid project scope');
  assert(payload && typeof payload === 'object' && !Array.isArray(payload), 'Payload must be an object');
  assert(typeof storage === 'string' && path.isAbsolute(storage), 'Storage must be an absolute path');
  const directory = path.join(storage, scope);
  fs.mkdirSync(directory, { recursive: true, mode: 0o700 });
  assert(!fs.lstatSync(directory).isSymbolicLink(), 'Project storage cannot be a symlink');
  for (const name of ['state.json', 'ledger.jsonl']) {
    const filename = path.join(directory, name);
    assert(!fs.existsSync(filename) || !fs.lstatSync(filename).isSymbolicLink(), 'Memory files cannot be symlinks');
  }
  const lock = path.join(directory, '.writer-lock');
  const deadline = Date.now() + 5000;
  for (;;) {
    try { fs.mkdirSync(lock); break; }
    catch (error) {
      if (error.code !== 'EEXIST' || Date.now() >= deadline) throw new Error('Memory storage is locked');
      await new Promise((resolve) => setTimeout(resolve, 25));
    }
  }
  try {
    const engine = new HMEM({ persistDir: directory, actor: 'cost-optimizer' });
    let selected = [];
    let context = '';
    let retrievalTrace = null;
    if (operation === 'remember_confirmed') {
      assert(['confirmed_constraint', 'accepted_finding'].includes(payload.kind), 'Only confirmed constraints or accepted findings can be captured');
      if (payload.kind === 'accepted_finding') {
        assert(payload.confirmed === true && payload.source, 'A finding needs explicit acceptance and provenance');
      }
      if (payload.field !== undefined) {
        assert(payload.kind === 'confirmed_constraint' && constraintFields.has(payload.field), 'Unsupported constraint field');
        assert(payload.value !== undefined && payload.value !== null, 'Constraint value is missing');
      }
      assert(payload.field || (typeof payload.text === 'string' && payload.text.trim()), 'Memory needs a field or text');
      const content = canonical(payload);
      assert(content.length <= 12000, 'Memory payload is too large');
      const active = engine.store.all().filter((record) => !record.supersededBy);
      let record = active.find((item) => item.content === content);
      if (!record) {
        const previous = payload.field ? active.filter((item) => {
          const old = JSON.parse(item.content);
          return old.kind === payload.kind && old.field === payload.field;
        }) : [];
        const source = typeof payload.source === 'string' ? payload.source : payload.source ? canonical(payload.source) : `founder_confirmation:${scope}`;
        record = engine.add({
          content, type: 'factual', layer: 'long_term',
          tags: [`project:${scope}`, `kind:${payload.kind}`, ...(payload.field ? [`field:${payload.field}`] : [])],
          source, provenance: { origin: 'manual', learnedAt: Date.now(), label: 'Explicit confirmed input', refs: [source] },
          supersedes: previous.at(-1)?.id,
        });
        for (const old of previous) engine.store.update(old.id, { supersededBy: record.id });
      }
      selected = [record];
    } else if (operation === 'recall') {
      // Exact kind recall enumerates all confirmed constraints, ranked by the
      // reference. A lexical threshold must not hide a hard constraint.
      const result = engine.query(payload.text || payload.kind || 'confirmed_constraint', payload.kind
        ? { threshold: 0, topN: engine.store.all().length } : undefined);
      const matches = result.memories.filter(({ memory }) => !memory.supersededBy
        && (!payload.kind || JSON.parse(memory.content).kind === payload.kind));
      assert(matches.length <= 100, 'Too many memories; narrow the recall query');
      selected = matches.map(({ memory }) => memory);
      context = engine.retrieval.formatReinjection(matches);
      retrievalTrace = result.trace;
      engine.store.persist();
    }
    const entries = engine.ledger.all();
    const ids = new Set(selected.map((record) => record.id));
    const audit = entries.map((entry, index) => ({
      ref: `${scope}:ledger:${index + 1}`, memory_id: `${scope}:${entry.memoryId}`,
      action: entry.action, actor: entry.actor, timestamp: entry.timestamp,
    })).filter((entry, index) => operation === 'audit' || ids.has(entries[index].memoryId)).slice(-100);
    for (const name of ['state.json', 'ledger.jsonl']) {
      const filename = path.join(directory, name);
      if (fs.existsSync(filename)) fs.chmodSync(filename, 0o600);
    }
    return {
      status: 'ok', engine_revision: revision, project_scope: scope,
      memory_ids: selected.map((record) => `${scope}:${record.id}`),
      records: selected.map((record) => exportRecord(record, scope)), context,
      audit_refs: audit.map((entry) => entry.ref),
      ...(operation === 'audit' ? { entries: audit, entry_count: entries.length } : {}),
      ...(retrievalTrace ? { retrieval: retrievalTrace } : {}),
    };
  } finally { fs.rmdirSync(lock); }
}

function selftest() {
  const storage = fs.mkdtempSync(path.join(os.tmpdir(), 'cost-optimizer-hmem-'));
  const call = (operation, scope, payload = {}) => {
    const child = spawnSync(process.execPath, [fileURLToPath(import.meta.url)], {
      input: JSON.stringify({ operation, project_scope: scope, payload, storage }),
      encoding: 'utf8', timeout: 10000, env: { ...process.env, TSX_DISABLE_CACHE: '1' },
    });
    assert(child.status === 0, 'Fresh-process H-MEM self-test failed');
    return JSON.parse(child.stdout);
  };
  try {
    const saved = call('remember_confirmed', 'selftest-A', { kind: 'confirmed_constraint', field: 'devops_capacity', value: 'none' });
    const recalled = call('recall', 'selftest-A', { kind: 'confirmed_constraint' });
    assert(recalled.memory_ids.includes(saved.memory_ids[0]), 'Restart recall failed');
    const other = call('recall', 'selftest-B', { kind: 'confirmed_constraint' });
    assert(other.memory_ids.length === 0, 'Project isolation failed');
    const audit = call('audit', 'selftest-A');
    assert(audit.entries.some((entry) => entry.action === 'create') && audit.entries.some((entry) => entry.action === 'read'), 'Audit round trip failed');
    return { status: 'ok', engine_revision: revision, checks: ['fresh_process_recall', 'project_isolation', 'create_read_audit'] };
  } finally { fs.rmSync(storage, { recursive: true }); }
}

try {
  let result;
  if (process.argv.includes('--selftest')) result = selftest();
  else {
    let input = '';
    for await (const chunk of process.stdin) {
      input += chunk;
      assert(input.length <= 64000, 'Request is too large');
    }
    result = await dispatch(JSON.parse(input));
  }
  process.stdout.write(JSON.stringify(result) + '\n');
} catch (error) {
  process.stderr.write(`H-MEM bridge: ${error.message}\n`);
  process.exitCode = 1;
}
