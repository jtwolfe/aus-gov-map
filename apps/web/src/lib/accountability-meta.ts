export type NeededHint = {
  note: string;
  apply?: string;
  sources?: string[];
  tables?: string[];
};

export const LENSES = [
  { href: "/accountability", label: "Overview", match: "exact" as const },
  { href: "/atlas", label: "Atlas" },
  { href: "/accountability/role-at-date", label: "Role at date" },
  { href: "/accountability/promise-receipt", label: "Promise → receipt" },
  { href: "/accountability/qon-debt", label: "QoN debt" },
  { href: "/accountability/chain-completeness", label: "Chain completeness" },
  { href: "/accountability/instruments", label: "Instruments" },
  { href: "/agencies", label: "Agencies" },
  // LAWS_NAV_SLOT: a parallel Stage 3a PR may add { href: "/laws", label: "Laws" }.
];

export const OVERVIEW_LENSES = [
  {
    href: "/atlas",
    kicker: "00",
    title: "Atlas",
    body: "Left-to-right past–present view of tenures, Estimates moments, QoNs, ANAO items, and instrument threads. A scrubber asks role-at-date for the lanes in view.",
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
