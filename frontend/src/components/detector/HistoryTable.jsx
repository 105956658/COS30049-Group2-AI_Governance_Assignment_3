/**
 * HistoryTable – the same session history as HistoryChart, as a table. It gives screen
 * reader and keyboard users the exact numbers, and is the easiest way to pick a check
 * on a phone, where the chart's dots are small.
 */
import { VERDICT, clockTime, percent, preview } from '../../lib/format.js';

export default function HistoryTable({ history, selectedId, onSelect }) {
  // Newest first: the check someone just made is the one they most likely want.
  const rows = history.map((h, i) => ({ ...h, n: i + 1 })).reverse();

  return (
    // tabIndex lets keyboard users scroll the table sideways on a narrow screen.
    <div className="table-wrap" tabIndex={0} role="region" aria-label="Session history table">
      <table className="table">
        <caption className="sr-only">Checks made in this session, newest first</caption>
        <thead>
          <tr>
            <th scope="col">#</th>
            <th scope="col">Time</th>
            <th scope="col">Text</th>
            <th scope="col">Verdict</th>
            <th scope="col" className="num">
              AI score
            </th>
            <th scope="col">
              <span className="sr-only">Action</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((h) => {
            const isSelected = h.id === selectedId;
            return (
              <tr key={h.id} className={isSelected ? 'is-selected' : undefined}>
                <td>{h.n}</td>
                <td className="nowrap">{clockTime(h.checkedAt)}</td>
                <td className="cell-text">{preview(h.text, 70)}</td>
                <td className="nowrap">
                  <span className={`badge badge-${h.result.label}`}>{VERDICT[h.result.label].short}</span>
                </td>
                <td className="num">{percent(h.result.ai_score)}</td>
                <td>
                  <button
                    type="button"
                    className="btn btn-sm"
                    onClick={() => onSelect(h.id)}
                    aria-pressed={isSelected}
                    aria-label={`View check ${h.n}`}
                  >
                    {isSelected ? 'Viewing' : 'View'}
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
