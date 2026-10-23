import { NODES } from './registry.mjs';
import { isObject, isText } from './nodes/lesson_nodes.mjs';

const TOP_KEYS = new Set(['id', 'version', 'trigger', 'allowed_languages', 'nodes', 'edges']);
const NODE_KEYS = new Set(['id', 'type']);
const TRIGGER_KEYS = new Set(['type']);
const TRIGGERS = new Set(['manual']);
// keys that try to run code. any unknown key is refused, these get a clearer message
const CODE_KEYS = new Set(['code', 'script', 'exec', 'eval', 'command', 'cmd', 'shell', 'function',
  'python', 'javascript', 'js', 'module', 'import', 'run']);

const VALIDATORS = ['validate_lesson', 'validate_question'];
// node type -> [one of these must come before it, message]
const NEEDS_BEFORE = {
  normalize_lesson: [[['validate_lesson'], 'normalize_lesson needs a validate_lesson node before it']],
  normalize_question: [[['validate_question'], 'normalize_question needs a validate_question node before it']],
  check_duplicate: [[VALIDATORS, 'check_duplicate needs a validate node before it']],
  save_draft: [
    [VALIDATORS, 'save_draft needs a validate node before it (nothing unchecked is saved)'],
    [['check_duplicate'], 'save_draft needs a check_duplicate node before it'],
    [['manual_approval'], 'save_draft needs a manual_approval node before it (no human approval, no save)'],
  ],
};

// like python repr, so messages read the same in both engines
const show = v => (typeof v === 'string' ? `'${v}'` : v === undefined || v === null ? 'None' : JSON.stringify(v));

export function lint(wf) {
  if (!isObject(wf)) return ['workflow must be a JSON object'];
  const errors = keyErrors(wf, TOP_KEYS, 'workflow');
  if (!isText(wf.id)) errors.push("workflow: 'id' must be a non-empty string");
  if ('version' in wf && typeof wf.version !== 'string') errors.push("workflow: 'version' must be a string");
  errors.push(...triggerErrors('trigger' in wf ? wf.trigger : { type: 'manual' }));
  const langs = 'allowed_languages' in wf ? wf.allowed_languages : ['en'];
  if (!(Array.isArray(langs) && langs.length && langs.every(isText))) {
    errors.push('allowed_languages must be a non-empty list of language codes, like ["en"]');
  }

  const nodes = wf.nodes;
  if (!Array.isArray(nodes) || !nodes.length) {
    errors.push("workflow: 'nodes' must be a non-empty list");
    return errors;
  }
  const [nodeErrs, ids] = nodeErrors(nodes);
  errors.push(...nodeErrs);
  if (nodeErrs.length) return errors;
  errors.push(...edgeErrors(wf.edges, ids));
  if (!errors.length) errors.push(...orderErrors(orderedNodes(wf).map(n => n.type)));
  return errors;
}

export function orderedNodes(wf) {
  // only call this after lint() found no errors
  const byId = new Map(wf.nodes.map(n => [n.id, n]));
  const next = new Map((wf.edges ?? []).map(([a, b]) => [a, b]));
  const targets = new Set(next.values());
  let id = [...byId.keys()].find(i => !targets.has(i));
  const order = [];
  while (id !== undefined) {
    order.push(byId.get(id));
    id = next.get(id);
  }
  return order;
}

function keyErrors(obj, allowed, where) {
  const errors = [];
  for (const key of Object.keys(obj)) {
    if (CODE_KEYS.has(key.toLowerCase())) {
      errors.push(`${where}: key '${key}' is not allowed. workflow.json is a description, not code`);
    } else if (!allowed.has(key)) {
      errors.push(`${where}: unknown key '${key}'`);
    }
  }
  return errors;
}

function triggerErrors(trigger) {
  if (!isObject(trigger)) return ['trigger must be an object'];
  const errors = keyErrors(trigger, TRIGGER_KEYS, 'trigger');
  if (!TRIGGERS.has(trigger.type)) errors.push(`trigger: type must be 'manual' (got ${show(trigger.type)})`);
  return errors;
}

function nodeErrors(nodes) {
  const errors = [];
  const ids = [];
  const allowed = Object.keys(NODES).join(', ');
  nodes.forEach((node, i) => {
    let where = `node ${i + 1}`;
    if (!isObject(node)) {
      errors.push(`${where}: must be an object`);
      return;
    }
    if (isText(node.id)) where = `node '${node.id}'`;
    errors.push(...keyErrors(node, NODE_KEYS, where));
    if (!isText(node.id)) errors.push(`${where}: 'id' must be a non-empty string`);
    else if (ids.includes(node.id)) errors.push(`${where}: duplicate node id`);
    else ids.push(node.id);
    if (typeof node.type !== 'string' || !Object.hasOwn(NODES, node.type)) {
      errors.push(`${where}: unknown node type ${show(node.type)}. allowed: ${allowed}`);
    }
  });
  return [errors, ids];
}

function edgeErrors(edges, ids) {
  if (!Array.isArray(edges)) return ["workflow: 'edges' must be a list of [from, to] pairs"];
  const errors = [];
  const pairs = [];
  edges.forEach((edge, i) => {
    if (!(Array.isArray(edge) && edge.length === 2 && edge.every(x => typeof x === 'string'))) {
      errors.push(`edge ${i + 1}: must be a [from, to] pair of node ids`);
      return;
    }
    for (const end of edge) {
      if (!ids.includes(end)) {
        errors.push(`edge ${i + 1} (${edge[0]} -> ${edge[1]}): points to a missing node '${end}'`);
      }
    }
    pairs.push(edge);
  });
  if (errors.length) return errors;
  return shapeErrors(pairs, ids);
}

function shapeErrors(pairs, ids) {
  const errors = [];
  const next = new Map();
  const prev = new Map();
  for (const [a, b] of pairs) {
    if (a === b) {
      errors.push(`cycle found: ${a} -> ${a}`);
      continue;
    }
    if (next.has(a)) errors.push(`node '${a}' has more than one next node. only a straight line is supported`);
    if (prev.has(b)) {
      errors.push(`node '${b}' has more than one node before it. only a straight line is supported`);
    }
    if (!next.has(a)) next.set(a, b);
    if (!prev.has(b)) prev.set(b, a);
  }
  if (errors.length) return errors;
  const cycle = findCycle(next);
  if (cycle) return [`cycle found: ${cycle.join(' -> ')}`];
  const starts = ids.filter(i => !prev.has(i));
  if (starts.length !== 1) {
    // no cycle and max one in/out each, so more starts = separate pieces
    return [`workflow must be one straight line, but it has ${starts.length} separate parts ` +
      `starting at: ${starts.join(', ')}`];
  }
  return [];
}

function findCycle(next) {
  for (const start of next.keys()) {
    const path = [];
    let node = start;
    while (node !== undefined && !path.includes(node)) {
      path.push(node);
      node = next.get(node);
    }
    if (node !== undefined) return [...path.slice(path.indexOf(node)), node];
  }
  return null;
}

function orderErrors(types) {
  const errors = [];
  types.forEach((type, i) => {
    for (const [anyOf, msg] of NEEDS_BEFORE[type] ?? []) {
      if (!anyOf.some(t => types.slice(0, i).includes(t)) && !errors.includes(msg)) errors.push(msg);
    }
  });
  return errors;
}
