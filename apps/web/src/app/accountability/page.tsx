import Link from "next/link";
import { AccountabilityNav, LensNeeded } from "@/components/accountability-lens";
import { loadAccountabilitySummary } from "@/lib/accountability";

export const metadata = { title: "Accountability" };
export const dynamic = "force-dynamic";

const LENSES = [
  {
    href: "/atlas",
    kicker: "00",
    title: "Responsibility Atlas",
    body: "Left-to-right past–future view of tenures, Estimates moments, QoNs, ANAO items, and instrument threads. A scrubber asks role-at-date for the lanes in view.",
  },
  {
    href: "/accountability/role-at-date",
    kicker: "01",
    title: "Role at date",
    body: "Who occupied a seat on a hearing or decision date. Occupancy comes from Handbook tenures and APS secretaries (aps_leaders), not from sitting at the table.",
  },
  {
    href: "/accountability/promise-receipt",
    kicker: "02",
    title: "Promise → receipt",
    body: "Sourced claims (promise, assurance, taken on notice) joined to instruments and later outcomes. Hansard is the citation.",
  },
  {
    href: "/accountability/qon-debt",
    kicker: "03",
    title: "QoN debt",
    body: "Open and overdue questions on notice by portfolio and answering agency. A count of unanswered questions, not a charge.",
  },
  {
    href: "/accountability/chain-completeness",
    kicker: "04",
    title: "Chain completeness",
    body: "Instruments missing a sourced accountable minister and/or responsible official. Gaps are missing edges.",
  },
  {
    href: "/accountability/instruments",
    kicker: "05",
    title: "Instruments",
    body: "Programs, measures, bills, contracts, grants, and policies. Search titles and identifiers once adapters write rows.",
  },
  {
    href: "/agencies",
    kicker: "06",
    title: "Agencies",
    body: "Official department names plus the current secretary or agency head when aps_leaders has written a sourced occupancy.",
  },
];

export default async function AccountabilityPage() {
  const summary = await loadAccountabilitySummary();
  return (
    <div className="space-y-10">
      <header className="max-w-3xl">
        <p className="eyebrow">Decision / duty map · Stage 2</p>
        <h1 className="mt-2 font-serif text-4xl text-ink">Accountability</h1>
        <p className="mt-3 text-muted leading-relaxed">
          Trace who held office when, which public instrument they were
          accountable or responsible for, and where that instrument was later
          scrutinised. Chains are sourced. This map does not assign guilt.
          Hansard is not ground truth — it is what was said on the day.
        </p>
        <p className="mt-2 text-sm text-muted">
          Stage 1 hearings plug in as dated scrutiny: join{" "}
          <span className="font-mono">hearings.held_on</span> to{" "}
          <span className="font-mono">person_roles</span>, and promote chunk
          spans to claims. Architecture:{" "}
          <span className="font-mono">docs/accountability-map.md</span>.
        </p>
      </header>

      <AccountabilityNav current="/accountability" />

      <section className="border border-rule bg-card px-5 py-4">
        <p className="eyebrow">Store counts</p>
        <p className="mt-2 text-sm text-muted">
          Sourced row counts in the current Postgres volume. Zero is correct until
          the matching ingest source has persisted. These are coverage numbers,
          not findings.
        </p>
        <dl className="mt-3 grid gap-3 sm:grid-cols-3 text-sm">
          <div>
            <dt className="text-xs uppercase tracking-[0.12em] text-muted">ANAO items</dt>
            <dd className="font-serif text-2xl text-navy">{summary.anaoItems}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-[0.12em] text-muted">Contracts</dt>
            <dd className="font-serif text-2xl text-navy">{summary.contracts}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-[0.12em] text-muted">Measures / programs</dt>
            <dd className="font-serif text-2xl text-navy">{summary.measures}</dd>
          </div>
        </dl>
        <p className="mt-2 text-xs text-muted">
          Source · <span className="font-mono">{summary.source}</span>
          {" · "}QoN {summary.questions}
          {" · "}proposed instruments {summary.instrumentsProposed}
        </p>
      </section>

      <section className="grid gap-5 md:grid-cols-2">
        {LENSES.map((lens) => (
          <article key={lens.href} className="border border-rule bg-card p-5">
            <p className="eyebrow">{lens.kicker}</p>
            <h2 className="mt-2 font-serif text-2xl text-navy">
              <Link href={lens.href} className="hover:text-ochre">
                {lens.title}
              </Link>
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-muted">{lens.body}</p>
          </article>
        ))}
      </section>

      <LensNeeded
        needed={{
          note: "Lenses read Postgres views when 007–011 have been applied. Handbook, QoN, agencies, aps_leaders, instrument_propose, ANAO, Budget/PBS, and AusTender now write into that model. Sparse data is correct; nothing invents officials or findings. The Atlas is the temporal reading room.",
          apply: "make db-apply",
          sources: ["handbook", "aps_leaders", "qon", "agencies", "instrument_propose", "anao", "budget_measure", "austender"],
          tables: ["person_roles", "instruments", "qons", "claims", "scrutiny_items", "outcomes"],
        }}
      />
    </div>
  );
}
