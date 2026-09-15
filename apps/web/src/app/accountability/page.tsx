import Link from "next/link";
import { AccountabilityNav, LensNeeded } from "@/components/accountability-lens";

export const metadata = { title: "Accountability" };
export const dynamic = "force-dynamic";

const LENSES = [
  {
    href: "/accountability/role-at-date",
    kicker: "01",
    title: "Role at date",
    body: "Who occupied a seat on a hearing or decision date. Occupancy comes from Handbook / AAO tenures, not from sitting at the table.",
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
];

export default function AccountabilityPage() {
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
          note: "Lenses read Postgres views when 007_accountability.sql and 008_hearing_segments.sql have been applied. Handbook, QoN, agencies, and instrument_propose now write into that model. ANAO / PBS / AusTender stay empty stubs. Sparse data is correct; nothing invents officials or findings.",
          apply: "make db-apply",
          sources: ["handbook", "qon", "agencies", "instrument_propose", "anao", "budget_measure", "austender"],
          tables: ["person_roles", "instruments", "qons", "claims", "scrutiny_items"],
        }}
      />
    </div>
  );
}
