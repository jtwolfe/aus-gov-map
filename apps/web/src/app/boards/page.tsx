import Link from "next/link";
import { LocalPinList } from "@/components/pin-button";
import { loadCatalog } from "@/lib/data";

export const metadata = { title: "Boards" };

export default async function BoardsPage() {
  const catalog = await loadCatalog();

  return (
    <div className="space-y-10">
      <header>
        <p className="eyebrow">Stage 1 stub</p>
        <h1 className="mt-2 font-serif text-4xl text-ink">Boards</h1>
        <p className="mt-3 max-w-2xl text-muted">
          Pinboards are a researcher workspace stub — seed boards live in
          Postgres/fixtures; “Pin to board” also stores a private list in this
          browser until auth lands in a later stage.
        </p>
      </header>

      <section className="grid gap-4 md:grid-cols-2">
        {catalog.boards.map((board) => {
          const count = catalog.pins.filter((p) => p.boardId === board.id).length;
          return (
            <article key={board.id} className="border border-rule bg-card p-5">
              <p className="eyebrow">{count} pin{count === 1 ? "" : "s"}</p>
              <h2 className="mt-2 font-serif text-2xl text-navy">
                <Link href={`/boards/${board.slug}`} className="hover:text-ochre">
                  {board.title}
                </Link>
              </h2>
              <p className="mt-2 text-sm text-muted">{board.description}</p>
            </article>
          );
        })}
      </section>

      <section>
        <p className="eyebrow">This browser</p>
        <h2 className="mt-2 font-serif text-2xl text-navy">Local pins</h2>
        <div className="mt-4">
          <LocalPinList />
        </div>
      </section>
    </div>
  );
}
