/**
 * Markdown viewer.
 *
 * Document bodies are user input, so the parsed HTML is sanitised before it
 * reaches the DOM - marked does not escape HTML embedded in the source.
 */

import DOMPurify from "dompurify";
import { marked } from "marked";
import { useMemo } from "react";

marked.setOptions({ gfm: true, breaks: false });

export function Markdown({ content }: { content: string }) {
  const html = useMemo(() => {
    const parsed = marked.parse(content ?? "", { async: false }) as string;
    return DOMPurify.sanitize(parsed, { USE_PROFILES: { html: true } });
  }, [content]);

  if (!content.trim()) {
    return <p className="muted">This document is empty.</p>;
  }

  return <div className="markdown" dangerouslySetInnerHTML={{ __html: html }} />;
}
