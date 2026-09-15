import Link from "next/link";
import { SearchForm } from "@/components/search-form";
import { searchCatalog } from "@/lib/search";
import type { SearchMode } from "@/lib/types";

export const metadata = { title: "Search" };

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; mode?: string }>;
}) {
  const params = await searchParams;
  const q = params.q ?? "";
  const mode = (["keyword", "semantic", "combined"].includes(params.mode ?? "")
    ? params.mode
    : "combined") as SearchMode;
  const result = await searchCatalog(q, mode);

  return (
    <div className="space-y-8">
      <header className="max-w-3xl">
        <p className="eyebrow">Find in the record</p>
        <h1 className="mt-2 font-serif text-4xl text-ink">Search</h1>
        <p className="mt-3 text-muted">
          Keyword uses titles, summaries, and transcript excerpts. Semantic is
          a vector placeholder — fixture mode ranks token overlap; Postgres mode
          prefers chunks that already have embeddings from ingest.
        </p>
        <div className="mt-6">
          <SearchForm initialQuery={q} initialMode={mode} />
        </div>
      </header>

      {q ? (
        <p className="text-sm text-muted">
          {result.hits.length} result{result.hits.length === 1 ? "" : "s"} from{" "}
          <span className="font-mono">{result.source}</span> · {result.mode}
        </p>
      ) : (
        <p className="text-sm text-muted">Try “FOI”, “procurement”, or “Paterson”.</p>
      )}

      <ol className="space-y-4">
        {result.hits.map((hit) => (
          <li key={`${hit.mode}-${hit.id}`} className="border-b border-rule/70 pb-4">
            <p className="eyebrow">
              {hit.kind} · {hit.mode}
              {hit.subtitle ? ` · ${hit.subtitle}` : ""}
            </p>
            <h2 className="mt-1 font-serif text-xl text-navy">
              <Link href={hit.href} className="hover:text-ochre">
                {hit.title}
              </Link>
            </h2>
            <p className="mt-1 text-sm leading-relaxed text-muted">{hit.excerpt}</p>
          </li>
        ))}
      </ol>
    </div>
  );
}
