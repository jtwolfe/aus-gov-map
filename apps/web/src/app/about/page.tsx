export const metadata = { title: "About" };

export default function AboutPage() {
  return (
    <article className="prose-none max-w-2xl space-y-6">
      <p className="eyebrow">Project</p>
      <h1 className="font-serif text-4xl text-ink">About aus-gov-map</h1>
      <p className="leading-relaxed text-muted">
        A continuously updated map of Australian federal government public
        data. Stage 1 is Senate committee and Estimates hearings, with
        keyword + vector search and a graph of who was involved.
      </p>
      <h2 className="font-serif text-2xl text-navy">Attribution</h2>
      <p className="leading-relaxed text-muted">
        Official parliamentary material — including Senate Hansard, committee
        transcripts, Estimates programs, and questions on notice — is typically
        © Commonwealth of Australia. Many of those records are published under
        Creative Commons Attribution-NonCommercial-NoDerivs (CC BY-NC-ND) or
        equivalent parliamentary terms. This project is framed as research /
        non-commercial. Always attribute the Parliament of Australia.
      </p>
      <p className="leading-relaxed text-muted">
        The fixture seed in <span className="font-mono">data/fixtures/seed.json</span>{" "}
        is invented sample dialogue so the interface works offline. It is not
        official Hansard.
      </p>
      <h2 className="font-serif text-2xl text-navy">Sources we point at</h2>
      <ul className="list-disc space-y-2 pl-5 text-muted">
        <li>
          <a className="link" href="https://www.aph.gov.au/Parliamentary_Business/Senate_estimates">
            Senate Estimates
          </a>
        </li>
        <li>
          <a className="link" href="https://parlinfo.aph.gov.au/">
            ParlInfo
          </a>
        </li>
        <li>
          <a className="link" href="https://handbook.aph.gov.au">
            Parliamentary Handbook
          </a>{" "}
          (Stage 2 stub — tenure / electorate / roles, no invented rows)
        </li>
        <li>
          <a className="link" href="http://data.openaustralia.org.au/">
            OpenAustralia data (XML hook, later)
          </a>
        </li>
      </ul>
      <h2 className="font-serif text-2xl text-navy">Current coverage</h2>
      <p className="leading-relaxed text-muted">
        The home page coverage strip counts hearings, people, and chunks from
        Postgres when <span className="font-mono">DATABASE_URL</span> is up.
        Live Officials use <span className="font-mono">hansard:</span> source
        keys; the bundled seed does not. After{" "}
        <span className="font-mono">make db-up</span> and{" "}
        <span className="font-mono">make ingest-live-files</span>, expect the
        three committed Estimates Officials (29617 / 29625 / 29629) plus the
        fixture hearings if you also ran <span className="font-mono">make seed</span>.
      </p>
    </article>
  );
}
