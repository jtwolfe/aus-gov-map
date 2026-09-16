"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { AccountabilityNav, LensNeeded } from "@/components/accountability-lens";
import { AtlasChart } from "@/components/atlas-chart";
import type { AtlasPayload } from "@/lib/atlas";
import { occupantsAtDate, todayUtc } from "@/lib/atlas-query";
import { formatDate, roleTypeLabel } from "@/lib/format";

export function AtlasView({ payload }: { payload: AtlasPayload }) {
  const router = useRouter();
  const pathname = usePathname();
  const params = payload.params;
  const defaultAsOf = clamp(
    params.asOf ?? (todayUtc() < payload.window.to ? todayUtc() : payload.window.to),
    payload.window.from,
    payload.window.to,
  );
  const [asOf, setAsOf] = useState(defaultAsOf);
  const [focus, setFocus] = useState<string | null>(params.focus);
  const occupants = useMemo(() => occupantsAtDate(payload.tenures, asOf), [payload.tenures, asOf]);

  function replaceQuery(patch: Record<string, string | null>) {
    const next = new URLSearchParams();
    const current = payload.params;
    const seed: Record<string, string | null> = {
      from: current.from ?? payload.window.from,
      to: current.to ?? payload.window.to,
      lane: current.lane,
      agency: current.agency,
      portfolio: current.portfolio,
      person: current.person,
      instrument: current.instrument,
      includeProposed: current.includeProposed ? "1" : "0",
      qon: current.qon ? "1" : "0",
      anao: current.anao ? "1" : "0",
      arcs: current.arcs ? "1" : "0",
      asOf,
      focus,
    };
    for (const [k, v] of Object.entries({ ...seed, ...patch })) {
      if (v) next.set(k, v);
    }
    router.replace(`${pathname}?${next.toString()}`, { scroll: false });
  }

  function onAsOf(iso: string) {
    setAsOf(iso);
    replaceQuery({ asOf: iso });
  }

  function onFocus(next: string | null) {
    setFocus(next);
    replaceQuery({ focus: next });
  }

  const empty = payload.ready && payload.lanes.length === 0;

  return (
    <div className="space-y-8">
      <header className="max-w-3xl">
        <p className="eyebrow">Temporal duty view · Stage 2</p>
        <h1 className="mt-2 font-serif text-4xl text-ink">Responsibility Atlas</h1>
        <p className="mt-3 text-muted leading-relaxed">
          Past on the left, present on the right. Swimlanes are portfolios or
          people. Bars are sourced occupancies. Points are hearings, questions
          on notice, and ANAO items. This map does not assign guilt.
        </p>
        <p className="mt-2 text-sm text-muted">
          Sitting in Estimates is <strong>not</strong> a tenure. Hansard, QoNs,
          and ANAO records are sourced public records — attribute the
          Commonwealth. Proposed instruments stay dashed and off until you ask.
        </p>
        <p className="mt-2 text-xs text-muted">
          Source · <span className="font-mono">{payload.source}</span>
          {" · "}
          {payload.window.from} → {payload.window.to}
          {payload.window.clamped ? " · window clamped" : ""}
          {" · "}
          <Link href="/accountability" className="hover:text-ochre">
            Accountability lenses
          </Link>
        </p>
      </header>

      <AccountabilityNav current="/atlas" />

      <form className="grid gap-3 border border-rule bg-card p-4 md:grid-cols-12" method="get">
        <label className="text-sm text-muted md:col-span-2">
          From
          <input
            type="date"
            name="from"
            defaultValue={params.from ?? payload.window.from}
            className="mt-1 block w-full border border-rule bg-paper px-2 py-1.5 text-ink"
          />
        </label>
        <label className="text-sm text-muted md:col-span-2">
          To
          <input
            type="date"
            name="to"
            defaultValue={params.to ?? payload.window.to}
            className="mt-1 block w-full border border-rule bg-paper px-2 py-1.5 text-ink"
          />
        </label>
        <label className="text-sm text-muted md:col-span-2">
          Lanes
          <select
            name="lane"
            defaultValue={params.lane}
            className="mt-1 block w-full border border-rule bg-paper px-2 py-1.5 text-ink"
          >
            <option value="agency">Portfolio / agency</option>
            <option value="person">Person</option>
          </select>
        </label>
        <label className="text-sm text-muted md:col-span-2">
          Agency
          <input
            type="search"
            name="agency"
            defaultValue={params.agency ?? ""}
            placeholder="slug or name"
            className="mt-1 block w-full border border-rule bg-paper px-2 py-1.5 text-ink"
          />
        </label>
        <label className="text-sm text-muted md:col-span-2">
          Person
          <input
            type="search"
            name="person"
            defaultValue={params.person ?? ""}
            placeholder="name or slug"
            className="mt-1 block w-full border border-rule bg-paper px-2 py-1.5 text-ink"
          />
        </label>
        <label className="text-sm text-muted md:col-span-2">
          Instrument
          <input
            type="search"
            name="instrument"
            defaultValue={params.instrument ?? ""}
            placeholder="title or slug"
            className="mt-1 block w-full border border-rule bg-paper px-2 py-1.5 text-ink"
          />
        </label>
        <input type="hidden" name="portfolio" defaultValue={params.portfolio ?? ""} />
        <fieldset className="md:col-span-9 flex flex-wrap items-end gap-3 text-sm text-muted">
          <label>
            Proposed
            <select name="includeProposed" defaultValue={params.includeProposed ? "1" : "0"} className="mt-1 block border border-rule bg-paper px-2 py-1.5 text-ink">
              <option value="0">Hide</option>
              <option value="1">Show</option>
            </select>
          </label>
          <label>
            Arcs
            <select name="arcs" defaultValue={params.arcs ? "1" : "0"} className="mt-1 block border border-rule bg-paper px-2 py-1.5 text-ink">
              <option value="1">On</option>
              <option value="0">Off</option>
            </select>
          </label>
          <label>
            QoN
            <select name="qon" defaultValue={params.qon ? "1" : "0"} className="mt-1 block border border-rule bg-paper px-2 py-1.5 text-ink">
              <option value="1">On</option>
              <option value="0">Off</option>
            </select>
          </label>
          <label>
            ANAO
            <select name="anao" defaultValue={params.anao ? "1" : "0"} className="mt-1 block border border-rule bg-paper px-2 py-1.5 text-ink">
              <option value="1">On</option>
              <option value="0">Off</option>
            </select>
          </label>
        </fieldset>
        <div className="md:col-span-3 flex items-end justify-end">
          <button type="submit" className="border border-navy px-3 py-1.5 text-sm text-navy hover:bg-paper-2">
            Apply filters
          </button>
        </div>
      </form>

      {!payload.ready ? (
        <div className="space-y-4">
          <p className="border border-dashed border-rule bg-paper-2/50 px-5 py-6 text-sm leading-relaxed text-muted">
            The Atlas is empty until Postgres holds sourced rows. Nothing here is
            inferred from silence. Use Accountability lenses in the meantime.
          </p>
          <LensNeeded needed={payload.needed} />
          <p className="text-sm">
            <Link href="/accountability" className="link">
              Open Accountability
            </Link>
          </p>
        </div>
      ) : empty ? (
        <div className="space-y-4">
          <p className="border border-dashed border-rule bg-paper-2/50 px-5 py-6 text-sm leading-relaxed text-muted">
            No tenures or moments in this window. Widen the dates, clear a
            filter, or ingest the layer you need. Empty is correct — it is not a
            finding.
          </p>
          <LayerGuide />
          <LensNeeded needed={payload.needed} />
        </div>
      ) : (
        <>
          <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_16rem]">
            <section className="border border-rule">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-rule bg-paper-2/60 px-3 py-2 text-xs text-muted">
                <p>
                  <span className="font-mono text-navy">{payload.counts.tenures}</span> tenures
                  {" · "}
                  <span className="font-mono text-navy">{payload.counts.moments}</span> moments
                  {" · "}
                  <span className="font-mono text-navy">{payload.counts.instruments}</span> instruments
                  {payload.counts.droppedLanes ? ` · ${payload.counts.droppedLanes} quieter lanes hidden` : ""}
                </p>
                <p className="font-mono">
                  Drag the ochre line · ← → weeks
                  {focus ? (
                    <>
                      {" · "}
                      <button type="button" className="underline hover:text-ochre" onClick={() => onFocus(null)}>
                        clear focus
                      </button>
                    </>
                  ) : null}
                </p>
              </div>
              <AtlasChart
                payload={payload}
                asOf={asOf}
                onAsOf={onAsOf}
                focus={focus}
                onFocus={onFocus}
                showArcs={params.arcs}
              />
            </section>
            <aside className="border border-rule bg-card px-4 py-4">
              <p className="eyebrow">As of {formatDate(asOf)}</p>
              <h2 className="mt-2 font-serif text-xl text-navy">Role at date</h2>
              <p className="mt-2 text-xs leading-relaxed text-muted">
                Occupants of visible lanes whose sourced tenure overlaps this
                date. An Estimates appearance does not appear here.
              </p>
              {occupants.length ? (
                <ul className="mt-3 divide-y divide-rule border-y border-rule">
                  {occupants.map((row, idx) => (
                    <li key={`${row.personSlug}-${row.roleType}-${idx}`} className="py-2">
                      <p className="font-serif text-navy">
                        {row.href ? (
                          <Link href={row.href} className="hover:text-ochre">
                            {row.personName}
                          </Link>
                        ) : (
                          row.personName
                        )}
                      </p>
                      <p className="text-xs text-muted">
                        {roleTypeLabel(row.roleType)}
                        {row.roleTitle ? ` · ${row.roleTitle}` : ""}
                        {" · "}
                        {row.source}
                      </p>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-3 text-sm text-muted">
                  No sourced occupancy on this date in the visible lanes.
                </p>
              )}
              <p className="mt-4 text-xs">
                <Link
                  href={`/accountability/role-at-date?on=${encodeURIComponent(asOf)}`}
                  className="hover:text-ochre"
                >
                  Open the Role at date lens
                </Link>
              </p>
            </aside>
          </div>
          <Legend />
        </>
      )}
    </div>
  );
}

function Legend() {
  return (
    <section className="border border-rule bg-card px-4 py-3 text-xs text-muted">
      <p className="eyebrow">Grammar</p>
      <ul className="mt-2 flex flex-wrap gap-x-5 gap-y-1">
        <li><span className="inline-block h-2 w-6 bg-navy align-middle" /> Minister / navy bar</li>
        <li><span className="inline-block h-2 w-6 bg-eucalyptus align-middle" /> Secretary / agency head</li>
        <li><span className="inline-block h-2 w-2 rounded-full bg-navy align-middle" /> Hearing (segments rolled up)</li>
        <li><span className="inline-block h-2 w-2 rotate-45 bg-ochre align-middle" /> QoN (ochre open, eucalyptus answered)</li>
        <li><span className="inline-block h-2 w-2 bg-gold align-middle" /> ANAO</li>
        <li><span className="inline-block h-1 w-6 border border-dashed border-gold align-middle" /> Proposed instrument</li>
      </ul>
    </section>
  );
}

export function LayerGuide() {
  return (
    <dl className="grid gap-3 border border-rule bg-card px-5 py-4 text-sm md:grid-cols-2">
      {[
        ["Tenure bars", "handbook, aps_leaders → person_roles"],
        ["Hearing points", "estimates / aph_transcript_file → hearings (segments roll up)"],
        ["QoN diamonds", "qon → qons"],
        ["ANAO squares", "anao → scrutiny_items"],
        ["Instrument threads", "budget_measure, austender; instrument_propose is proposed-only"],
        ["Arcs", "claims (promise / TON) with qon_id or instrument_id"],
      ].map(([k, v]) => (
        <div key={k}>
          <dt className="font-serif text-navy">{k}</dt>
          <dd className="font-mono text-xs text-muted">{v}</dd>
        </div>
      ))}
    </dl>
  );
}

function clamp(iso: string, min: string, max: string) {
  if (iso < min) return min;
  if (iso > max) return max;
  return iso;
}
