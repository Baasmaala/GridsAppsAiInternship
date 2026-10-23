import fs from 'node:fs';
import path from 'node:path';
import { randomBytes } from 'node:crypto';

import { StoreError } from './errors.mjs';
import { readJson } from './loader.mjs';

export function readStore(file) {
  if (!fs.existsSync(file)) return [];
  let saved;
  try {
    saved = readJson(file);
  } catch (ex) {
    if (ex instanceof SyntaxError) throw new StoreError(`drafts file is not valid JSON: ${file} (${ex.message})`);
    throw ex;
  }
  if (!Array.isArray(saved)) throw new StoreError(`drafts file must contain a JSON array: ${file}`);
  return saved;
}

export function atomicJsonWrite(file, value) {
  // write a temp file next to it, then rename. no half-written json.
  const dir = path.dirname(file);
  fs.mkdirSync(dir, { recursive: true });
  const tmp = path.join(dir, `.tmp-${randomBytes(6).toString('hex')}.json`);
  try {
    const fd = fs.openSync(tmp, 'wx');
    try {
      fs.writeSync(fd, JSON.stringify(value, null, 2) + '\n');
      fs.fsyncSync(fd);
    } finally {
      fs.closeSync(fd);
    }
    fs.renameSync(tmp, file);
  } catch (ex) {
    fs.rmSync(tmp, { force: true });
    throw ex;
  }
}
