import fs from 'node:fs';

import { WorkflowError } from './errors.mjs';
import { lint, orderedNodes } from './lint.mjs';

export class Workflow {
  constructor({ id, version, allowedLanguages, nodes, raw }) {
    Object.assign(this, { id, version, allowedLanguages, nodes, raw });  // nodes in run order
  }
}

export function parseWorkflow(raw) {
  const errors = lint(raw);
  if (errors.length) throw new WorkflowError(errors);
  const langs = (raw.allowed_languages ?? ['en']).map(x => x.trim().toLowerCase());
  return new Workflow({ id: raw.id, version: raw.version ?? '', allowedLanguages: langs,
    nodes: orderedNodes(raw), raw });
}

export function readJson(file) {
  // strip the BOM: powershell often saves files with one
  return JSON.parse(fs.readFileSync(file, 'utf8').replace(/^﻿/, ''));
}

export function loadWorkflow(file) {
  let raw;
  try {
    raw = readJson(file);
  } catch (ex) {
    if (ex.code === 'ENOENT') throw new WorkflowError([`workflow file not found: ${file}`]);
    if (ex instanceof SyntaxError) throw new WorkflowError([`workflow file is not valid JSON: ${ex.message}`]);
    throw ex;
  }
  return parseWorkflow(raw);
}

export function toMermaid(wf) {
  // short ids so odd characters in node ids cannot break the diagram
  const lines = ['flowchart LR', '  trigger(["manual trigger"])'];
  let prev = 'trigger';
  wf.nodes.forEach((node, i) => {
    const label = `${node.id}<br/>${node.type}`.replaceAll('"', '#quot;');
    lines.push(`  n${i + 1}["${label}"]`);
    lines.push(`  ${prev} --> n${i + 1}`);
    prev = `n${i + 1}`;
  });
  return lines.join('\n');
}
