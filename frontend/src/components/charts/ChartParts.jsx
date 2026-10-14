/**
 * Small pieces shared by both charts: the hover/focus tooltip, the legend, and the
 * path for a bar with rounded data-end and a square baseline.
 */

/**
 * Tooltip positioned inside the chart's wrapper (which is position: relative).
 * `x`, `y` are pixels inside the chart; the tooltip flips to the left near the right edge.
 * Children are React nodes, so any user text in them is escaped.
 */
export function ChartTooltip({ x, y, width, children }) {
  const flip = x > width - 200;
  return (
    <div
      className="chart-tooltip"
      role="presentation"
      style={{
        left: x,
        top: y,
        transform: `translate(${flip ? 'calc(-100% - 12px)' : '12px'}, -50%)`,
      }}
    >
      {children}
    </div>
  );
}

/** items: [{ key, label, className }] – className sets the swatch colour/shape. */
export function ChartLegend({ items }) {
  return (
    <ul className="chart-legend" aria-label="Legend">
      {items.map((item) => (
        <li key={item.key}>
          <span className={`legend-swatch ${item.className}`} aria-hidden="true" />
          {item.label}
        </li>
      ))}
    </ul>
  );
}

/** A vertical bar from the baseline up to `top`, with only the top corners rounded. */
export function barPath(x, top, width, baseline, radius = 4) {
  const h = baseline - top;
  const r = Math.max(0, Math.min(radius, width / 2, h));
  return [
    `M${x},${baseline}`,
    `V${top + r}`,
    `Q${x},${top} ${x + r},${top}`,
    `H${x + width - r}`,
    `Q${x + width},${top} ${x + width},${top + r}`,
    `V${baseline}`,
    'Z',
  ].join('');
}
