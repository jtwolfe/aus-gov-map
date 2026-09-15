import Link from "next/link";
import { AccountabilityNav, EmptyRows } from "@/components/accountability-lens";
import { loadRoleAtDate } from "@/lib/accountability";
import { formatDate, roleTypeLabel } from "@/lib/format";

export const metadata = { title: "Role at date" };
export const dynamic = "force-dynamic";

export default async function RoleAtDatePage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | undefined>>;
}) {
  const params = await searchParams;
  const on = params.on?.trim() || null;
  const person = params.person?.trim() || null;
  const portfolio = params.portfolio?.trim() || null;
  const payload = await loadRoleAtDate(on, person, portfolio);

  return (
    <div className="space-y-8">
      <header className="max-w-3xl">
        <p className="eyebrow">Occupancy · sourced tenures</p>
        <h1 className="mt-2 font-serif text-4xl text-ink">Role at date</h1>
        <p className="mt-3 text-muted leading-relaxed">
          Who held a seat on a given day. Use a hearing date from Stage 1 to
          ask who was minister or secretary then. An Estimates appearance is
          not a tenure.
        </p>
        <p className="mt-2 text-xs text-muted">
          Source · <span className="font-mono">{payload.source}</span>
          {on ? ` · on ${formatDate(on)}` : " · any overlapping occupancy"}
        </p>
      </header>

      <AccountabilityNav current="/accountability/role-at-date" />

      <form className="flex flex-wrap items-end gap-3" method="get">
        <label className="text-sm text-muted">
          Date
          <input
            type="date"
            name="on"
            defaultValue={on ?? ""}
            className="mt-1 block border border-rule bg-card px-3 py-1.5 text-ink"
          />
        </label>
        <label className="text-sm text-muted">
          Person
          <input
            type="search"
            name="person"
            defaultValue={person ?? ""}
            placeholder="name or slug"
            className="mt-1 block border border-rule bg-card px-3 py-1.5 text-ink"
          />
        </label>
        <label className="text-sm text-muted">
          Portfolio
          <input
            type="search"
            name="portfolio"
            defaultValue={portfolio ?? ""}
            className="mt-1 block border border-rule bg-card px-3 py-1.5 text-ink"
          />
        </label>
        <button type="submit" className="border border-navy px-3 py-1.5 text-sm text-navy hover:bg-paper-2">
          Filter
        </button>
      </form>

      {payload.rows.length ? (
        <ul className="divide-y divide-rule border-y border-rule">
          {payload.rows.map((row, idx) => (
            <li key={`${row.personSlug}-${row.roleType}-${idx}`} className="py-3">
              <p className="font-serif text-lg text-navy">
                {row.personSlug ? (
                  <Link href={`/people/${row.personSlug}`} className="hover:text-ochre">
                    {row.personName}
                  </Link>
                ) : (
                  row.personName
                )}
              </p>
              <p className="text-sm text-muted">
                {roleTypeLabel(row.roleType)}
                {row.roleTitle ? ` · ${row.roleTitle}` : ""}
                {row.portfolio ? ` · ${row.portfolio}` : ""}
                {row.agencyName ? (
                  <>
                    {" · "}
                    {row.agencySlug ? (
                      <Link href={`/agencies/${row.agencySlug}`} className="hover:text-ochre">
                        {row.agencyName}
                      </Link>
                    ) : (
                      row.agencyName
                    )}
                  </>
                ) : null}
              </p>
              <p className="mt-1 text-xs uppercase tracking-[0.12em] text-muted">
                {formatDate(row.startDate)} – {row.endDate ? formatDate(row.endDate) : "open"}
                {" · "}
                {row.source}
                {row.sourceUrl ? (
                  <>
                    {" · "}
                    <a href={row.sourceUrl} className="link normal-case tracking-normal" rel="noreferrer">
                      source
                    </a>
                  </>
                ) : null}
              </p>
            </li>
          ))}
        </ul>
      ) : (
        <EmptyRows label="occupancies for this filter" needed={payload.needed} />
      )}
    </div>
  );
}
