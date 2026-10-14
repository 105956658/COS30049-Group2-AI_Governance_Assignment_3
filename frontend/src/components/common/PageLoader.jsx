/** PageLoader – shown by <Suspense> while a lazily-loaded page is downloading. */
export default function PageLoader() {
  return (
    <div className="page-loader" role="status">
      <span className="spinner" aria-hidden="true" />
      <span>Loading…</span>
    </div>
  );
}
