import Link from "next/link";
import { CreateBoardForm, LocalPinList } from "@/components/pin-button";
import { listBoards } from "@/lib/boards";

export const metadata = { title: "Boards" };
export const dynamic = "force-dynamic";

export default async function BoardsPage() {
  const { boards, persist, source } = await listBoards();

  return (
    <div className="space-y-10">
      <header>
        <p className="eyebrow">{persist ? "Postgres" : "Offline stub"}</p>
        <h1 className="mt-2 font-serif text-4xl text-ink">Boards</h1>
        <p className="mt-3 max-w-2xl text-muted">
          {persist
            ? "Pinboards persist in Postgres. Create a board, then pin a hearing, person, or excerpt from its page."
            : "Postgres is not reachable, so seed boards are read-only and “Pin” falls back to this browser."}
        </p>
        <p className="mt-2 text-xs text-muted">
          Serving boards from <span className="font-mono">{source}</span>
          {persist ? " · writes enabled" : " · writes disabled"}.
        </p>
      </header>

      {persist ? <CreateBoardForm /> : null}

      {!boards.length ? (
        <p className="border border-dashed border-rule bg-paper-2/50 px-5 py-6 text-sm leading-relaxed text-muted">
          No boards in the current store. Create one when Postgres is up, or
          run <span className="font-mono">make db-apply</span> to seed the demo
          board. Empty is correct — it is not a finding.
        </p>
      ) : null}

      <section className="grid gap-4 md:grid-cols-2">
        {boards.map((board) => (
          <article key={board.id} className="border border-rule bg-card p-5">
            <p className="eyebrow">
              {board.pinCount} pin{board.pinCount === 1 ? "" : "s"}
            </p>
            <h2 className="mt-2 font-serif text-2xl text-navy">
              <Link href={`/boards/${board.slug}`} className="hover:text-ochre">
                {board.title}
              </Link>
            </h2>
            <p className="mt-2 text-sm text-muted">{board.description}</p>
          </article>
        ))}
      </section>

      {!persist ? (
        <section>
          <p className="eyebrow">This browser</p>
          <h2 className="mt-2 font-serif text-2xl text-navy">Local pins</h2>
          <div className="mt-4">
            <LocalPinList />
          </div>
        </section>
      ) : null}
    </div>
  );
}
