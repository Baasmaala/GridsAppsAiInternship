// what a node gives back
export function step(data, { status = null, stop = false, note = null } = {}) {
  return { data, status, stop, note };
}

// shared by all lessons in one run
export function makeRun({ reviewer, dryRun, allowedLanguages, now, knownIds = [] }) {
  return { reviewer, dryRun, allowedLanguages, now,
    knownIds: new Set(knownIds), seenIds: new Set(), newDrafts: [] };
}
