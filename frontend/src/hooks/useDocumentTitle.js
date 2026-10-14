import { useEffect } from 'react';

/** useDocumentTitle – sets the text shown in the browser tab for the current page. */
export default function useDocumentTitle(title) {
  useEffect(() => {
    document.title = title ? `${title} · TextTrace` : 'TextTrace · AI Text Detector';
  }, [title]);
}
