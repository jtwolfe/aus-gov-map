import Link from "next/link";
import { notFound } from "next/navigation";
import { getBoard } from "@/lib/data";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const result = await getBoard(slug);
  return { title: result?.board.title ?? "Board" };
}

export default async function BoardPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const result = await getBoard(slug);
  if (!result) notFound();
  const { board, pins, catalog } = result;

  return (
    <article className="space-y-8">
      <header>
        <p className="eyebrow">Board stub</p>
        <h1 className="mt-2 font-serif text-4xl text-ink">{board.title}</h1>
        <p className="mt-3 max-w-2xl text-muted">{board.description}</p>
      </header>
      <ul className="divide-y divide-rule border-y border-rule">
        {pins.map((pin) => {
          const hearing =
            pin.pinType === "hearing"
              ? catalog.hearings.find((h) => h.id === pin.targetId)
              : undefined;
          const person =
            pin.pinType === "person"
              ? catalog.people.find((p) => p.id === pin.targetId)
              : undefined;
          const href = hearing
            ? `/hearings/${hearing.slug}`
            : person
              ? `/people/${person.slug}`
              : "/boards";
          const label = hearing?.title ?? person?.name ?? pin.targetId;
          return (
            <li key={pin.id} className="py-4">
              <p className="eyebrow">{pin.pinType}</p>
              <Link href={href} className="mt-1 block font-serif text-xl text-navy hover:text-ochre">
                {label}
              </Link>
              {pin.note ? <p className="mt-1 text-sm text-muted">{pin.note}</p> : null}
            </li>
          );
        })}
      </ul>
    </article>
  );
}
