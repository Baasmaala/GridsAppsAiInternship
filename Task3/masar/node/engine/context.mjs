// what a node gives back
export function step(data, { status = null, stop = false, note = null } = {}) {
  return { data, status, stop, note };
}

// shared by all lessons in one run
export function makeRun({ reviewer, dryRun, allowedLanguages, now, knownIds = [], knownPrints = new Map() }) {
  return { reviewer, dryRun, allowedLanguages, now,
    knownIds: new Set(knownIds), seenIds: new Set(),
    knownPrints, seenPrints: new Map(),  // fingerprint -> source_id
    explicitItems: new Set(),  // python fills this in a resume, node has no resume
    newDrafts: [] };
}
