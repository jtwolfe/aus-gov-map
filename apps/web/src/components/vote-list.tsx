import Link from "next/link";
import type { DivisionVoteRow } from "@/lib/laws";
import { formatDate } from "@/lib/format";

export function voteLabel(vote: string): string {
  switch (vote) {
    case "aye":
      return "Aye";
    case "no":
      return "No";
    case "abstain":
      return "Abstain";
    case "absent":
      return "Absent";
    default:
      return vote;
  }
}

export function VoteList({
  votes,
  empty,
}: {
  votes: DivisionVoteRow[];
  empty: string;
}) {
  if (!votes.length) {
    return <p className="text-sm leading-relaxed text-muted">{empty}</p>;
  }
  return (
    <ul className="divide-y divide-rule border-y border-rule">
      {votes.map((row, idx) => (
        <li key={`${row.divisionSlug}-${row.personName}-${row.vote}-${idx}`} className="py-3">
          <p className="flex flex-wrap items-baseline justify-between gap-2">
            <span className="font-serif text-lg text-navy">
              {row.personSlug ? (
                <Link href={`/people/${row.personSlug}`} className="hover:text-ochre">
                  {row.personName}
                </Link>
              ) : (
                row.personName
              )}
            </span>
            <span className="text-xs uppercase tracking-[0.12em] text-muted">
              {voteLabel(row.vote)}
            </span>
          </p>
          <p className="text-sm text-muted">
            {row.party}
            {row.electorate ? ` · ${row.electorate}` : ""}
            {row.dividedOn ? ` · ${formatDate(row.dividedOn)}` : ""}
            {row.house ? ` · ${row.house}` : ""}
          </p>
          <p className="mt-1 text-sm text-muted">{row.divisionTitle}</p>
          {row.sourceUrl ? (
            <p className="mt-1 text-xs">
              <a href={row.sourceUrl} className="link" rel="noreferrer">
                They Vote For You
              </a>
            </p>
          ) : null}
          {!row.personSlug ? (
            <p className="mt-1 text-xs text-muted">
              Published name only — no matching person in this store. We do not invent MPs.
            </p>
          ) : null}
        </li>
      ))}
    </ul>
  );
}
