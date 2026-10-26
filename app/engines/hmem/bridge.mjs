// Local adapter for the unmodified Meterless H-MEM TypeScript reference.
// The reference is loaded with its pinned tsx development dependency.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { tsImport } from './reference/node_modules/tsx/dist/esm/api/index.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const revision = fs.readFileSync(path.join(here, 'PINNED_REVISION'), 'utf8').trim();
const { HMEM } = await tsImport('./reference/src/index.ts', import.meta.url);

function object(value, label) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error(`${label} must be an object`);
  return value;
}

function identity(scope) {
  if (typeof scope !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/.test(scope) || scope === '.' || scope === '..') {
    throw new Error('project_scope must be a nonempty project ID (letters, digits, period, underscore, colon or hyphen)');
  }
  return crypto.createHash('sha256').update(scope, 'utf8').digest('hex');
}

function run(request) {
  object(request, 'request');
  const { operation, project_scope: scope } = request;
  const scopeId = identity(scope);
  const root = request.storage;
  if (typeof root !== 'string' || !path.isAbsolute(root)) throw new Error('storage must be an absolute path');
  const persistDir = path.join(root, scopeId);
  const engine = new HMEM({ persistDir, actor: 'cost-optimizer' });
  const payload = object(request.payload, 'payload');
  const base = { status: 'ok', engine_revision: revision, memory_ids: [], context: [], audit_refs: [] };

  if (operation === 'remember_confirmed') {
    const kind = payload.kind;
    if (typeof kind !== 'string' || !/^[a-z][a-z0-9_]{0,63}$/.test(kind)) throw new Error('payload.kind is invalid');
    const content = typeof payload.text === 'string' && payload.text.trim()
      ? payload.text.trim() : JSON.stringify(payload);
    if (!content || content.length > 20000) throw new Error('memory content is empty or too long');
    const record = engine.add({
      content, type: 'factual', layer: 'long_term', tags: [`kind:${kind}`],
      source: `confirmed:${kind}`,
      provenance: { origin: 'manual', learnedAt: Date.now(), label: `confirmed ${kind}` },
    });
    return { ...base, memory_ids: [`${scopeId}:${record.id}`],
      context: [{ id: `${scopeId}:${record.id}`, kind, text: record.content, source: record.source }],
      audit_refs: [`${scopeId}:ledger:${engine.ledger.all().length}`] };
  }
  if (operation === 'recall') {
    const kind = payload.kind;
    if (kind !== undefined && (typeof kind !== 'string' || !/^[a-z][a-z0-9_]{0,63}$/.test(kind))) throw new Error('query.kind is invalid');
    const text = typeof payload.text === 'string' && payload.text.trim() ? payload.text.trim() : (kind || 'confirmed memory');
    // Retrieval and scoring are supplied by H-MEM. Threshold zero allows an exact
    // kind filter to return confirmed items even when a short query has low similarity.
    const result = engine.query(text, { topN: 10000, threshold: 0 });
    const items = result.memories.filter(({ memory }) => !kind || memory.tags.includes(`kind:${kind}`));
    const foundIds = new Set(items.map(({ memory }) => memory.id));
    const auditRefs = engine.ledger.all().flatMap((entry, index) =>
      foundIds.has(entry.memoryId) ? [`${scopeId}:ledger:${index + 1}`] : []);
    return { ...base, memory_ids: items.map(({ memory }) => `${scopeId}:${memory.id}`),
      context: items.map(({ memory, relevance }) => ({ id: `${scopeId}:${memory.id}`,
        kind: memory.tags.find(tag => tag.startsWith('kind:'))?.slice(5) ?? null,
        text: memory.content, source: memory.source, relevance,
        provenance: memory.provenance })),
      audit_refs: auditRefs };
  }
  if (operation === 'audit') {
    const entries = engine.ledger.all();
    return { ...base, audit_refs: entries.map((_, index) => `${scopeId}:ledger:${index + 1}`),
      context: entries.map((entry, index) => ({ audit_ref: `${scopeId}:ledger:${index + 1}`,
        memory_id: `${scopeId}:${entry.memoryId}`, action: entry.action,
        timestamp: entry.timestamp, actor: entry.actor })) };
  }
  throw new Error(`unsupported H-MEM operation: ${operation}`);
}

function selftest() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'cost-optimizer-hmem-'));
  try {
    const make = (operation, scope, payload = {}) => run({ operation, project_scope: scope, payload, storage: root });
    const saved = make('remember_confirmed', 'selftest-A', { kind: 'confirmed_constraint', text: 'monthly budget 300 USD' });
    const found = make('recall', 'selftest-A', { kind: 'confirmed_constraint' });
    const other = make('recall', 'selftest-B', { kind: 'confirmed_constraint' });
    const audit = make('audit', 'selftest-A');
    if (!saved.memory_ids.length || !found.memory_ids.includes(saved.memory_ids[0]) ||
        other.memory_ids.length || !audit.audit_refs.length) throw new Error('H-MEM persistence/isolation/audit self-test failed');
    return { status: 'ok', engine_revision: revision };
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
}

try {
  let result;
  if (process.argv.includes('--selftest')) {
    result = selftest();
  } else {
    let input = '';
    for await (const chunk of process.stdin) input += chunk;
    result = run(JSON.parse(input));
  }
  process.stdout.write(JSON.stringify(result) + '\n');
} catch (error) {
  process.stderr.write(`H-MEM bridge: ${error instanceof Error ? error.message : String(error)}\n`);
  process.exitCode = 1;
}
