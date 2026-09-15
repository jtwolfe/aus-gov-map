import Link from "next/link";
import { SourceBadge } from "@/components/source-badge";
import { SearchForm } from "@/components/search-form";
import { loadCatalog } from "@/lib/data";
import { filtersFromSearchParams, searchCatalog } from "@/lib/search";
import type { SearchMode } from "@/lib/types";

export const metadata = { title: "Search" };
export const dynamic = "force-dynamic";

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | undefined>>;
}) {
  const params = await searchParams;
  const q = params.q ?? "";
  const mode = (["keyword", "semantic", "combined"].includes(params.mode ?? "")
    ? params.mode
    : "combined") as SearchMode;
  const filters = filtersFromSearchParams(params);
  const [result, catalog] = await Promise.all([
    searchCatalog(q, mode, filters),
    loadCatalog(),
  ]);

  return (
    <div className="space-y-8">
      <header className="max-w-3xl">
        <p className="eyebrow">Find in the record</p>
        <h1 className="mt-2 font-serif text-4xl text-ink">Search</h1>
        <p className="mt-3 text-muted">
          Keyword uses Postgres full-text over hearings, documents, chunks, and
          people. Semantic ranks pgvector cosine when ingest has written
          embeddings (same hash embedder as the CLI). Filters apply to the
          hearing a hit belongs to.
        </p>
        <div className="mt-6">
          <SearchForm
            initialQuery={q}
            initialMode={mode}
            initialFilters={filters}
            committees={catalog.committees}
          />
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
          <li key={`${hit.mode}-${hit.kind}-${hit.id}`} className="border-b border-rule/70 pb-4">
            <p className="flex flex-wrap items-center gap-2 eyebrow">
              {hit.kind} · {hit.mode}
              {hit.subtitle ? ` · ${hit.subtitle}` : ""}
              {hit.sourceKey ? <SourceBadge sourceKey={hit.sourceKey} /> : null}
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
