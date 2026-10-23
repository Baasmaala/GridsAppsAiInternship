// the only icons in the app. same 1.5 stroke, round ends.
export type IconName = 'dot' | 'check' | 'cross' | 'pause' | 'arrow';

const PATHS: Record<IconName, string> = {
  dot: 'M8 4.5a3.5 3.5 0 1 1 0 7a3.5 3.5 0 1 1 0-7',
  check: 'M3.5 8.5l3 3l6-7',
  cross: 'M4.5 4.5l7 7M11.5 4.5l-7 7',
  pause: 'M6 4v8M10 4v8',
  arrow: 'M3 8h10M9 4l4 4l-4 4',
};

export function Icon({ name, size = 16, label }: { name: IconName; size?: number; label?: string }) {
  return (
    <svg className={`icon${name === 'arrow' ? ' icon-flip' : ''}`} width={size} height={size} viewBox="0 0 16 16"
      fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"
      role={label ? 'img' : undefined} aria-label={label} aria-hidden={label ? undefined : true}>
      <path d={PATHS[name]} />
    </svg>
  );
}
