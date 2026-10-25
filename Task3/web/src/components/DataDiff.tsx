import { useDetails } from '../lib/details';
import { diffFields, plainRows, show } from '../lib/diff';

// two columns, field by field. changed, added and removed fields are marked.
export function DataDiff({ before, after, beforeLabel, afterLabel, hideSame = false }: {
  before: unknown; after: unknown; beforeLabel: string; afterLabel: string; hideSame?: boolean;
}) {
  const details = useDetails();
  const all = diffFields(before, after);
  const rows = all && !details ? plainRows(all) : all;
  if (!rows) {
    return (
      <div className="diff-raw">
        <div><span className="diff-head">{beforeLabel}</span><pre className="json">{JSON.stringify(before, null, 2)}</pre></div>
        {after !== undefined && (
          <div><span className="diff-head">{afterLabel}</span><pre className="json">{JSON.stringify(after, null, 2)}</pre></div>
        )}
      </div>
    );
  }
  // a step that failed has no "after": show the data it got, nothing struck through
  if (after === undefined) {
    return (
      <div className="diff diff-one" role="table">
        <div className="diff-row diff-top" role="row">
          <span role="columnheader" />
          <span className="diff-head" role="columnheader">{beforeLabel}</span>
        </div>
        {rows.map(r => (
          <div key={r.key} className="diff-row" role="row">
            <span className="diff-key" role="cell">{r.key}</span>
            <span className="diff-val" role="cell" dir="auto">{show(r.before)}</span>
          </div>
        ))}
        <div className="diff-row diff-note" role="row"><span role="cell">{afterLabel}</span></div>
      </div>
    );
  }
  const shown = hideSame ? rows.filter(r => r.change !== 'same') : rows;
  return (
    <div className="diff" role="table">
      <div className="diff-row diff-top" role="row">
        <span role="columnheader" />
        <span className="diff-head" role="columnheader">{beforeLabel}</span>
        <span className="diff-head" role="columnheader">{afterLabel}</span>
      </div>
      {shown.map(r => (
        <div key={r.key} className={`diff-row is-${r.change}`} role="row">
          <span className="diff-key" role="cell">{r.key}</span>
          <span className="diff-val" role="cell" dir="auto">{show(r.before)}</span>
          <span className="diff-val" role="cell" dir="auto">{show(r.after)}</span>
        </div>
      ))}
    </div>
  );
}
