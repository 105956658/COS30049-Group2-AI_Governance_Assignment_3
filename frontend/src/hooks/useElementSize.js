import { useEffect, useState } from 'react';

/**
 * useElementSize – measures an element and re-renders when its size changes.
 * Charts use it to fit their container (phone, laptop, projector…).
 *
 *   const [ref, { width, height }] = useElementSize();
 *   return <div ref={ref}>{width > 0 && <Chart width={width} />}</div>;
 *
 * `ref` is a "callback ref" (a function React calls with the DOM node).
 * The size is 0 × 0 until the first measurement, and while the element is
 * hidden (display: none) – so always check `width > 0` before drawing.
 */
export default function useElementSize() {
  const [node, setNode] = useState(null);
  const [size, setSize] = useState({ width: 0, height: 0 });

  useEffect(() => {
    if (!node) return undefined;

    // ResizeObserver calls us whenever the element's box changes size.
    const observer = new ResizeObserver(([entry]) => {
      const width = Math.round(entry.contentRect.width);
      const height = Math.round(entry.contentRect.height);
      // Only update state when something actually changed (avoids extra renders).
      setSize((prev) => (prev.width === width && prev.height === height ? prev : { width, height }));
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, [node]);

  return [setNode, size];
}
