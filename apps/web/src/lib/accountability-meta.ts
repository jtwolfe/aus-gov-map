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
];
