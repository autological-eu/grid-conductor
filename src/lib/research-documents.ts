/** Markdown is the publication source. Vite ships these documents as text;
 * offline research generation remains entirely outside the browser build. */
const sources = import.meta.glob<string>("../../docs/*.md", {
  query: "?raw",
  import: "default",
  eager: true,
});

export const researchDocuments = Object.entries(sources)
  .map(([path, content]) => ({
    slug: path.split("/").at(-1)!.replace(/\.md$/, ""),
    title: content.match(/^#\s+(.+)$/m)?.[1] ?? path,
    content,
  }))
  .sort((a, b) => a.title.localeCompare(b.title));

export function documentHref(slug: string): string {
  return `${import.meta.env.BASE_URL}docs/${encodeURIComponent(slug)}`;
}
