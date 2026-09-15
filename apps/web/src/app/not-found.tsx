import Link from "next/link";

export default function NotFound() {
  return (
    <div className="max-w-lg">
      <p className="eyebrow">404</p>
      <h1 className="mt-2 font-serif text-4xl text-ink">Not in this map</h1>
      <p className="mt-3 text-muted">
        That hearing or person is not in the current seed. Try search, or return
        home.
      </p>
      <Link href="/" className="mt-6 inline-block text-navy hover:text-ochre">
        ← Home
      </Link>
    </div>
  );
}
