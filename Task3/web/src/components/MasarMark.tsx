// the letter meem as it starts the word مسار (مـ): a small teardrop head on the right,
// the joining stroke runs left from its bottom like a route, with 2 stations on it.
export function MasarMark({ size = 32 }: { size?: number }) {
  return (
    <svg className="icon" width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <path d="M19.4 19C21.6 15.8 23.4 12.4 25.6 12.4C27.6 12.4 28.8 14.3 28.8 16.2C28.8 18.2 27.3 19 25.4 19H3.3"
        fill="none" stroke="var(--route)" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="11.6" cy="19" r="2.5" fill="var(--card)" stroke="var(--route)" strokeWidth="1.8" />
      <circle cx="3.3" cy="19" r="2.5" fill="var(--card)" stroke="var(--route)" strokeWidth="1.8" />
    </svg>
  );
}
