import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="mt-20 border-t border-rule">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-5 py-10 text-sm text-muted md:flex-row md:justify-between">
        <p className="max-w-xl">
          Research / non-commercial scaffold. Official Hansard and committee
          records are typically © Commonwealth of Australia (often CC BY-NC-ND) —
          attribute the Parliament. Fixture text in this repo is sample dialogue,
          not a transcript.
        </p>
        <div className="flex gap-5">
          <Link href="/accountability" className="hover:text-navy">
            Accountability
          </Link>
          <Link href="/atlas" className="hover:text-navy">
            Atlas
          </Link>
          <Link href="/about" className="hover:text-navy">
            Attribution
          </Link>
          <a
            href="https://www.aph.gov.au/Parliamentary_Business/Senate_estimates"
            className="hover:text-navy"
          >
            Senate Estimates
          </a>
          <a href="https://github.com/jtwolfe/aus-gov-map" className="hover:text-navy">
            GitHub
          </a>
        </div>
      </div>
    </footer>
  );
}
