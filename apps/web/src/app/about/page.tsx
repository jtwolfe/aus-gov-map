import Link from "next/link";

export const metadata = { title: "About" };

export default function AboutPage() {
  return (
    <article className="prose-none max-w-2xl space-y-6">
      <p className="eyebrow">Project</p>
      <h1 className="font-serif text-4xl text-ink">About aus-gov-map</h1>
      <p className="leading-relaxed text-muted">
        A continuously updated map of Australian federal government public
        data. Stage 1 is Senate committee and Estimates hearings. Stage 2
        adds a sourced decision / duty map — occupancies, instruments,
        scrutiny, and outcomes — without automated guilt labels.
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
          (live OData ingest — parliamentarians, tenure, ministries; APS secretaries via directory /{" "}
          <span className="font-mono">aps_leaders</span>)
        </li>
        <li>
          <a className="link" href="https://www.anao.gov.au">
            ANAO
          </a>
          ,{" "}
          <a className="link" href="https://budget.gov.au">
            Budget / PBS
          </a>
          ,{" "}
          <a className="link" href="https://www.tenders.gov.au">
            AusTender
          </a>
          ,{" "}
          <a className="link" href="https://www.grants.gov.au">
            GrantConnect
          </a>
          ,{" "}
          <a className="link" href="https://www.legislation.gov.au">
            legislation
          </a>
          ,{" "}
          <a className="link" href="https://theyvoteforyou.org.au/help/api">
            TheyVoteForYou
          </a>
        </li>
        <li>
          <a className="link" href="http://data.openaustralia.org.au/">
            OpenAustralia data (XML hook, later)
          </a>
        </li>
        <li>
          <a className="link" href="https://www.aph.gov.au/Parliamentary_Business/Senate_Estimates/eqon">
            Senate Estimates Questions on Notice
          </a>{" "}
          (best-effort public search API / committed fixtures)
        </li>
        <li>
          <a className="link" href="https://www.directory.gov.au/">
            directory.gov.au
          </a>{" "}
          and official department executive pages (APS secretaries / agency heads)
        </li>
      </ul>
      <h2 className="font-serif text-2xl text-navy">Duty map (Stage 2)</h2>
      <p className="leading-relaxed text-muted">
        Accountability lenses read foundation tables. Handbook people and
        Estimates Officials are real public records. Structured hearing
        segments are derived from those Officials. QoN rows come from the APH
        EQON search or committed examples.{" "}
        <strong> Instruments</strong> extracted from Estimates text are{" "}
        <strong>proposed candidates only</strong> — low confidence, not asserted
        facts. Agency stubs use official department names. Secretaries come from
        the{" "}
        <span className="font-mono">aps_leaders</span> adapter (directory.gov.au
        / executive pages / cited fixtures). Hansard is a citation of what was said, not ground
        truth. See{" "}
        <span className="font-mono">docs/accountability-map.md</span>.
        The temporal reading room is the{" "}
        <a className="link" href="/atlas">
          Responsibility Atlas
        </a>{" "}
        (<span className="font-mono">docs/responsibility-atlas.md</span>).
        Stage 3a puts Bills and Acts on that spine —{" "}
        <Link className="link" href="/laws">
          /laws
        </Link>{" "}
        (<span className="font-mono">docs/laws-and-precedent.md</span>). Votes
        are sourced divisions only. Judgments are court holdings, not guilt
        labels.
      </p>
      <h2 className="font-serif text-2xl text-navy">Current coverage</h2>
      <p className="leading-relaxed text-muted">
        The home page coverage strip counts hearings, people, and chunks from
        Postgres when <span className="font-mono">DATABASE_URL</span> is up.
        Live Officials use <span className="font-mono">hansard:</span> source
        keys; the bundled seed does not. After{" "}
        <span className="font-mono">make db-up</span> and{" "}
        <span className="font-mono">make ingest-live-files</span>, expect the
        committed Estimates Officials under{" "}
        <span className="font-mono">fixtures/live/transcripts</span> (21 Hansard
        JSON files, including 29617 / 29625 / 29629) plus the fixture hearings
        if you also ran <span className="font-mono">make seed</span>.
      </p>
    </article>
  );
}
