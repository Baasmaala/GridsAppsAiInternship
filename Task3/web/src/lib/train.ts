import type { Item, WorkflowNode } from '../api/client';

// where the train is on the line: the index of the station (0 is the start),
// after `tick` steps of the animation
export function trainStop(item: Item, nodes: WorkflowNode[], tick: number): number {
  const reached = Math.min(tick, item.trace.length);
  if (reached === 0) return 0;
  const node = item.trace[reached - 1].node;
  const i = nodes.findIndex(n => n.id === node);
  return i === -1 ? 0 : i + 1;
}

export const arrived = (item: Item, tick: number) => tick >= item.trace.length;

// the longest trace decides how long the animation runs
export const ticksNeeded = (items: Item[]) => items.reduce((n, i) => Math.max(n, i.trace.length), 0);
