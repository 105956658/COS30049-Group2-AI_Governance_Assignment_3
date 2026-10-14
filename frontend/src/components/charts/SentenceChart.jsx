/**
 * SentenceChart – answers "WHICH PARTS of this text look AI-written?"
 *
 * One bar per sentence, in reading order; height = the classifier's P(AI) for that
 * sentence. Bars above the dashed line lean AI. Hover or focus a bar for the sentence;
 * click it (or press Enter) to highlight it in the text below – the two views share
 * the `selected` index.
 *
 * D3 only does the maths (scales, ticks); React renders the SVG, so user text in the
 * tooltip is escaped like everywhere else.
 */
import { useMemo, useState } from 'react';
import * as d3 from 'd3';

import useElementSize from '../../hooks/useElementSize.js';
import { AI_THRESHOLD } from '../../config.js';
import { leaning, percent, preview } from '../../lib/format.js';
import { ChartLegend, ChartTooltip, barPath } from './ChartParts.jsx';

const HEIGHT = 240;
const MARGIN = { top: 12, right: 12, bottom: 36, left: 44 };
const UNSCORED_HEIGHT = 4; // px – a stub so short sentences still have a visible slot
const MAX_BAR_WIDTH = 40; // px – a short text should not turn into a few giant blocks

const LEGEND = [
  { key: 'ai', label: 'Leans AI (≥ 50%)', className: 'swatch-ai' },
  { key: 'human', label: 'Leans human (< 50%)', className: 'swatch-human' },
  { key: 'none', label: 'Too short to score', className: 'swatch-none' },
];

export default function SentenceChart({ sentences, selected, onSelect }) {
  const [ref, { width }] = useElementSize();
  const [hover, setHover] = useState(null); // index of the bar under the pointer / focus

  const innerW = Math.max(0, width - MARGIN.left - MARGIN.right);
  const innerH = HEIGHT - MARGIN.top - MARGIN.bottom;

  const { x, y, xTicks } = useMemo(() => {
    const xScale = d3
      .scaleBand()
      .domain(sentences.map((_, i) => i))
      .range([0, innerW])
      .paddingInner(sentences.length > 40 ? 0.1 : 0.2)
      .paddingOuter(0.1);
    const yScale = d3.scaleLinear().domain([0, 1]).range([innerH, 0]);
    // Show at most ~12 sentence numbers on the axis, whatever the text length.
    const step = Math.max(1, Math.ceil(sentences.length / 12));
    const ticks = sentences.map((_, i) => i).filter((i) => i % step === 0);
    return { x: xScale, y: yScale, xTicks: ticks };
  }, [sentences, innerW, innerH]);

  const hovered = hover !== null ? sentences[hover] : null;

  function handleKey(event, i) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      onSelect(selected === i ? null : i);
    }
  }

  return (
    <figure className="chart">
      <figcaption>
        <h3 className="chart-title">Which sentences look AI-written?</h3>
        <p className="chart-subtitle">
          AI probability for each sentence, in reading order. Select a bar to find the sentence in the text.
        </p>
      </figcaption>
      <ChartLegend items={LEGEND} />

      <div ref={ref} className="chart-area">
        {width > 0 && (
          <svg width={width} height={HEIGHT} role="group" aria-label="Bar chart of AI probability per sentence">
            <g transform={`translate(${MARGIN.left},${MARGIN.top})`}>
              {/* Gridlines + y axis labels */}
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
                P(AI)
              </text>

              {/* Bars */}
              {sentences.map((s, i) => {
                const side = leaning(s.p_ai);
                const top = side === 'none' ? innerH - UNSCORED_HEIGHT : y(s.p_ai);
                const barW = Math.min(x.bandwidth(), MAX_BAR_WIDTH);
                const bx = x(i) + (x.bandwidth() - barW) / 2;
                const active = hover === i || selected === i;
                const label =
                  side === 'none'
                    ? `Sentence ${i + 1}: too short to score`
                    : `Sentence ${i + 1}: ${percent(s.p_ai)} AI probability`;
                return (
                  <g
                    key={i}
                    className={`bar-group${active ? ' is-active' : ''}${selected === i ? ' is-selected' : ''}`}
                    tabIndex={0}
                    role="button"
                    aria-pressed={selected === i}
                    aria-label={label}
                    onMouseEnter={() => setHover(i)}
                    onMouseLeave={() => setHover(null)}
                    onFocus={() => setHover(i)}
                    onBlur={() => setHover(null)}
                    onClick={() => onSelect(selected === i ? null : i)}
                    onKeyDown={(e) => handleKey(e, i)}
                  >
                    {/* Invisible full-height hit target, bigger than the bar itself */}
                    <rect x={x(i)} y={0} width={x.bandwidth()} height={innerH} className="hit-target" />
                    <path d={barPath(bx, top, barW, innerH)} className={`bar bar-${side}`} />
                  </g>
                );
              })}

              {/* Threshold line, drawn over the bars */}
              <line x2={innerW} y1={y(AI_THRESHOLD)} y2={y(AI_THRESHOLD)} className="threshold-line" />
              <text x={innerW} y={y(AI_THRESHOLD) - 6} textAnchor="end" className="threshold-label">
                AI threshold
              </text>

              {/* Baseline + x axis */}
              <line x2={innerW} y1={innerH} y2={innerH} className="axis-line" />
              {xTicks.map((i) => (
                <text
                  key={i}
                  x={x(i) + x.bandwidth() / 2}
                  y={innerH + 16}
                  textAnchor="middle"
                  className="axis-label"
                >
                  {i + 1}
                </text>
              ))}
              <text x={innerW / 2} y={innerH + 32} textAnchor="middle" className="axis-title">
                Sentence number
              </text>
            </g>
          </svg>
        )}

        {hovered && (
          <ChartTooltip
            x={MARGIN.left + x(hover) + x.bandwidth() / 2}
            y={MARGIN.top + (hovered.p_ai === null ? innerH : y(hovered.p_ai))}
            width={width}
          >
            <strong>Sentence {hover + 1}</strong>
            <span>
              {hovered.p_ai === null ? 'Too short to score (under 4 words)' : `${percent(hovered.p_ai)} AI probability`}
            </span>
            <span className="tooltip-quote">“{preview(hovered.text, 90)}”</span>
          </ChartTooltip>
        )}
      </div>
    </figure>
  );
}
