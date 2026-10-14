/**
 * HistoryChart – answers "HOW DO THE TEXTS I CHECKED THIS SESSION COMPARE?"
 *
 * One column per check, in the order they were made. The dot is the document's AI
 * score, coloured by verdict; the vertical line is the model range (how much the trees
 * disagreed), so an uncertain result is visibly "taller" than a confident one.
 * Select a check to show its full result above.
 */
import { useMemo, useState } from 'react';
import * as d3 from 'd3';

import useElementSize from '../../hooks/useElementSize.js';
import { AI_THRESHOLD } from '../../config.js';
import { VERDICT, clockTime, percent, preview } from '../../lib/format.js';
import { ChartLegend, ChartTooltip } from './ChartParts.jsx';

const HEIGHT = 260;
const MARGIN = { top: 16, right: 16, bottom: 36, left: 44 };

const LEGEND = [
  { key: 'ai', label: 'AI-generated', className: 'swatch-ai swatch-dot' },
  { key: 'human', label: 'Human-written', className: 'swatch-human swatch-dot' },
  { key: 'range', label: 'Model range', className: 'swatch-range' },
];

export default function HistoryChart({ history, selectedId, onSelect }) {
  const [ref, { width }] = useElementSize();
  const [hover, setHover] = useState(null);

  const innerW = Math.max(0, width - MARGIN.left - MARGIN.right);
  const innerH = HEIGHT - MARGIN.top - MARGIN.bottom;

  const { x, y, xTicks } = useMemo(() => {
    const xScale = d3
      .scalePoint()
      .domain(history.map((h) => h.id))
      .range([0, innerW])
      .padding(0.6);
    const yScale = d3.scaleLinear().domain([0, 1]).range([innerH, 0]);
    const step = Math.max(1, Math.ceil(history.length / 10));
    const ticks = history.map((h, i) => ({ id: h.id, n: i + 1 })).filter((_, i) => i % step === 0);
    return { x: xScale, y: yScale, xTicks: ticks };
  }, [history, innerW, innerH]);

  // Wide enough hit target per column, even with a single check.
  const hitW = Math.min(48, x.step() || innerW);
  const hoverIndex = history.findIndex((h) => h.id === hover);
  const hovered = hoverIndex >= 0 ? history[hoverIndex] : null;

  function handleKey(event, id) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      onSelect(id);
    }
  }

  return (
    <figure className="chart">
      <figcaption>
        <h3 className="chart-title">How do this session&apos;s checks compare?</h3>
        <p className="chart-subtitle">
          AI score for every text checked in this tab, oldest first. Select a check to view its result.
        </p>
      </figcaption>
      <ChartLegend items={LEGEND} />

      <div ref={ref} className="chart-area">
        {width > 0 && (
          <svg width={width} height={HEIGHT} role="group" aria-label="Dot chart of AI score for each check">
            <g transform={`translate(${MARGIN.left},${MARGIN.top})`}>
              {y.ticks(4).map((t) => (
                <g key={t} transform={`translate(0,${y(t)})`}>
                  <line x2={innerW} className="grid-line" />
                  <text x={-8} dy="0.32em" textAnchor="end" className="axis-label">
                    {percent(t)}
                  </text>
                </g>
              ))}
              <text
                transform={`translate(${-36},${innerH / 2}) rotate(-90)`}
                textAnchor="middle"
                className="axis-title"
              >
                AI score
              </text>

              <line x2={innerW} y1={y(AI_THRESHOLD)} y2={y(AI_THRESHOLD)} className="threshold-line" />
              <text x={innerW} y={y(AI_THRESHOLD) - 6} textAnchor="end" className="threshold-label">
                AI threshold
              </text>

              {history.map((h, i) => {
                const { label, ai_score: score, score_range: range } = h.result;
                const cx = x(h.id);
                const isSelected = h.id === selectedId;
                return (
                  <g
                    key={h.id}
                    className={`point-group${hover === h.id ? ' is-active' : ''}${isSelected ? ' is-selected' : ''}`}
                    tabIndex={0}
                    role="button"
                    aria-pressed={isSelected}
                    aria-label={`Check ${i + 1} at ${clockTime(h.checkedAt)}: ${VERDICT[label].short}, AI score ${percent(score)}`}
                    onMouseEnter={() => setHover(h.id)}
                    onMouseLeave={() => setHover(null)}
                    onFocus={() => setHover(h.id)}
                    onBlur={() => setHover(null)}
                    onClick={() => onSelect(h.id)}
                    onKeyDown={(e) => handleKey(e, h.id)}
                  >
                    <rect x={cx - hitW / 2} y={0} width={hitW} height={innerH} className="hit-target" />
                    <line x1={cx} x2={cx} y1={y(range.low)} y2={y(range.high)} className="range-line" />
                    {isSelected && <circle cx={cx} cy={y(score)} r={11} className="selection-ring" />}
                    <circle cx={cx} cy={y(score)} r={6} className={`point point-${label}`} />
                  </g>
                );
              })}

              <line x2={innerW} y1={innerH} y2={innerH} className="axis-line" />
              {xTicks.map((t) => (
                <text key={t.id} x={x(t.id)} y={innerH + 16} textAnchor="middle" className="axis-label">
                  {t.n}
                </text>
              ))}
              <text x={innerW / 2} y={innerH + 32} textAnchor="middle" className="axis-title">
                Check number
              </text>
            </g>
          </svg>
        )}

        {hovered && (
          <ChartTooltip
            x={MARGIN.left + x(hovered.id)}
            y={MARGIN.top + y(hovered.result.ai_score)}
            width={width}
          >
            <strong>
              Check {hoverIndex + 1} · {clockTime(hovered.checkedAt)}
            </strong>
            <span>
              {VERDICT[hovered.result.label].long}, {percent(hovered.result.confidence)} confidence
            </span>
            <span>
              AI score {percent(hovered.result.ai_score)} (range {percent(hovered.result.score_range.low)}–
              {percent(hovered.result.score_range.high)})
            </span>
            <span className="tooltip-quote">“{preview(hovered.text, 80)}”</span>
          </ChartTooltip>
        )}
      </div>
    </figure>
  );
}
