import type { WorkflowNode } from '../api/client';

const GAP = 34;
const PAD = 10;

// a small metro line: the start bar, one dot per station, and the train.
// stop is the index the train is at (0 = start). in arabic the whole svg is mirrored by css.
export function MiniLine({ nodes, stop, color, label }: {
  nodes: WorkflowNode[]; stop: number; color: string; label: string;
}) {
  const width = PAD * 2 + nodes.length * GAP;
  const x = (i: number) => PAD + i * GAP;
  return (
    <span className="mini-line">
      <svg viewBox={`0 0 ${width} 24`} width={width} height="24" role="img" aria-label={label}>
        <line x1={x(0)} y1="12" x2={x(nodes.length)} y2="12" stroke="var(--rule)" strokeWidth="3" strokeLinecap="round" />
        <line x1={x(0)} y1="12" x2={x(stop)} y2="12" stroke="var(--route)" strokeWidth="3" strokeLinecap="round"
          className="mini-reached" />
        <rect x={x(0) - 2.5} y="5" width="5" height="14" rx="2.5" fill="var(--route)" />
        {nodes.map((n, i) => (
          <circle key={n.id} cx={x(i + 1)} cy="12" r="4.5" fill="var(--card)"
            stroke={i + 1 <= stop ? 'var(--route)' : 'var(--rule)'} strokeWidth="2.5" />
        ))}
        <g className="mini-train" style={{ transform: `translateX(${x(stop)}px)` }}>
          <circle cx="0" cy="12" r="7" fill={color} stroke="var(--card)" strokeWidth="2" />
        </g>
      </svg>
    </span>
  );
}
