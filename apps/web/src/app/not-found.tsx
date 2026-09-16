import Link from "next/link";

export default function NotFound() {
  return (
    <div className="max-w-lg">
      <p className="eyebrow">404</p>
      <h1 className="mt-2 font-serif text-4xl text-ink">Not in this map</h1>
      <p className="mt-3 text-muted">
        That hearing, person, agency, instrument, or board is not in the
        current store. Empty is correct until ingest writes the row — it is
        not a finding.
      </p>
      <nav className="mt-6 flex flex-wrap gap-x-4 gap-y-1 text-sm">
        <Link href="/" className="link">
          Home
        </Link>
        <Link href="/search" className="link">
          Search
        </Link>
        <Link href="/accountability" className="link">
          Accountability
        </Link>
        <Link href="/atlas" className="link">
          Atlas
        </Link>
      </nav>
    </div>
  );
}
