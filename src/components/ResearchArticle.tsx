import ReactMarkdown from "react-markdown";
import rehypeSlug from "rehype-slug";
import remarkGfm from "remark-gfm";
import { documentHref, researchDocuments } from "@/lib/research-documents";
import { publicAsset } from "@/lib/research";

/** Resolve original repository-relative links into deployed publications/assets. */
function publicationLink(href: string): string {
  if (/^(https?:|mailto:|#)/.test(href)) return href;
  const [file, hash] = href.split("#");
  const slug = file?.split("/").at(-1)?.replace(/\.md$/, "");
  if (file?.endsWith(".md") && researchDocuments.some((doc) => doc.slug === slug)) {
    return documentHref(slug!) + (hash ? `#${hash}` : "");
  }
  if (file?.includes("research/")) return publicAsset(file.slice(file.indexOf("research/")));
  if (href === "/" || href === "/docs" || href === "/targets" || href === "/network")
    return publicAsset(href);
  if (href.startsWith("/research/")) return publicAsset(href);
  return `https://github.com/autological-eu/grid-conductor/blob/public-v1/${href.replace(/^(\.\.\/)+/, "")}`;
}

export function ResearchArticle({ content }: { content: string }) {
  return (
    <article className="research-prose min-w-0">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeSlug]}
        components={{
          a: ({ href, children }) => <a href={publicationLink(href ?? "")}>{children}</a>,
          img: ({ src, alt }) => (
            <img src={publicationLink(src ?? "")} alt={alt ?? ""} loading="lazy" />
          ),
          table: ({ children }) => (
            <div className="overflow-x-auto" tabIndex={0}>
              <table>{children}</table>
            </div>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </article>
  );
}
