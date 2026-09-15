import Link from "next/link";
import { notFound } from "next/navigation";
import { getBoardBySlug } from "@/lib/boards";
import { loadCatalog, resolvePinTarget } from "@/lib/data";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const result = await getBoardBySlug(slug);
  return { title: result?.board.title ?? "Board" };
}

export default async function BoardPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const result = await getBoardBySlug(slug);
  if (!result) notFound();
  const { board, pins, persist } = result;
  const catalog = await loadCatalog();
  const resolved = await Promise.all(
    pins.map(async (pin) => ({ pin, ...(await resolvePinTarget(pin, catalog)) })),
  );

  return (
    <article className="space-y-8">
      <header>
        <p className="eyebrow">{persist ? "Persisted board" : "Seed board"}</p>
        <h1 className="mt-2 font-serif text-4xl text-ink">{board.title}</h1>
        <p className="mt-3 max-w-2xl text-muted">{board.description}</p>
        <p className="mt-2">
          <Link href="/boards" className="text-sm text-navy hover:text-ochre">
            ← All boards
          </Link>
        </p>
      </header>
      <ul className="divide-y divide-rule border-y border-rule">
        {resolved.length ? (
          resolved.map(({ pin, href, label, excerpt }) => (
            <li key={pin.id} className="py-4">
              <p className="eyebrow">{pin.pinType}</p>
              <Link href={href} className="mt-1 block font-serif text-xl text-navy hover:text-ochre">
                {label}
              </Link>
              {excerpt ? <p className="mt-1 text-sm text-muted">{excerpt}</p> : null}
              {pin.note ? <p className="mt-1 text-sm text-muted">{pin.note}</p> : null}
            </li>
          ))
        ) : (
          <li className="py-6 text-sm text-muted">No pins on this board yet.</li>
        )}
      </ul>
    </article>
  );
}
