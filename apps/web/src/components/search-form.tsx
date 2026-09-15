"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import type { SearchFilters, SearchMode } from "@/lib/types";

export function SearchForm({
  initialQuery = "",
  initialMode = "combined",
  initialFilters,
  committees = [],
  size = "lg",
}: {
  initialQuery?: string;
  initialMode?: SearchMode;
  initialFilters?: SearchFilters;
  committees?: Array<{ slug: string; name: string }>;
  size?: "lg" | "sm";
}) {
  const router = useRouter();
  const [q, setQ] = useState(initialQuery);
  const [mode, setMode] = useState<SearchMode>(initialMode);
  const [committee, setCommittee] = useState(initialFilters?.committee ?? "");
  const [person, setPerson] = useState(initialFilters?.person ?? "");
  const [hearingType, setHearingType] = useState<SearchFilters["hearingType"]>(
    initialFilters?.hearingType ?? "all",
  );
  const [from, setFrom] = useState(initialFilters?.from ?? "");
  const [to, setTo] = useState(initialFilters?.to ?? "");

  function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    const params = new URLSearchParams();
    if (q.trim()) params.set("q", q.trim());
    if (mode !== "combined") params.set("mode", mode);
    if (committee) params.set("committee", committee);
    if (person.trim()) params.set("person", person.trim());
    if (hearingType && hearingType !== "all") params.set("type", hearingType);
    if (from) params.set("from", from);
    if (to) params.set("to", to);
    router.push(`/search?${params.toString()}`);
  }

  return (
    <form onSubmit={onSubmit} className="w-full">
      <div
        className={`flex flex-col gap-3 rounded-sm border border-rule bg-card shadow-[0_1px_0_rgba(28,25,21,0.04)] ${
          size === "lg" ? "p-3 sm:flex-row sm:items-center" : "p-2 sm:flex-row"
        }`}
      >
        <label className="sr-only" htmlFor="q">
          Search hearings and people
        </label>
        <input
          id="q"
          name="q"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search Estimates, committees, people — e.g. FOI, procurement, Paterson"
          className={`w-full bg-transparent px-3 text-ink outline-none placeholder:text-muted/70 ${
            size === "lg" ? "py-3 text-base" : "py-2 text-sm"
          }`}
        />
        <button
          type="submit"
          className="shrink-0 bg-navy px-5 py-2.5 text-sm text-paper hover:bg-eucalyptus"
        >
          Search
        </button>
      </div>
      <fieldset className="mt-3 flex flex-wrap gap-4 text-xs text-muted">
        <legend className="sr-only">Search mode</legend>
        {(
          [
            ["combined", "Keyword + semantic"],
            ["keyword", "Keyword"],
            ["semantic", "Semantic"],
          ] as const
        ).map(([value, label]) => (
          <label key={value} className="flex cursor-pointer items-center gap-2">
            <input
              type="radio"
              name="mode"
              value={value}
              checked={mode === value}
              onChange={() => setMode(value)}
            />
            {label}
          </label>
        ))}
      </fieldset>
      <div className="mt-3 grid gap-2 text-xs text-muted sm:grid-cols-2 lg:grid-cols-5">
        <label className="block">
          <span className="eyebrow">Committee</span>
          <select
            className="mt-1 w-full border border-rule bg-card px-2 py-1.5 text-ink"
            value={committee}
            onChange={(e) => setCommittee(e.target.value)}
          >
            <option value="">Any committee</option>
            {committees.map((c) => (
              <option key={c.slug} value={c.slug}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="eyebrow">Kind</span>
          <select
            className="mt-1 w-full border border-rule bg-card px-2 py-1.5 text-ink"
            value={hearingType}
            onChange={(e) => setHearingType(e.target.value as SearchFilters["hearingType"])}
          >
            <option value="all">Estimates + other</option>
            <option value="estimates">Estimates only</option>
            <option value="other">Other hearings</option>
          </select>
        </label>
        <label className="block">
          <span className="eyebrow">Person</span>
          <input
            className="mt-1 w-full border border-rule bg-card px-2 py-1.5 text-ink"
            value={person}
            onChange={(e) => setPerson(e.target.value)}
            placeholder="Name or slug"
          />
        </label>
        <label className="block">
          <span className="eyebrow">From</span>
          <input
            type="date"
            className="mt-1 w-full border border-rule bg-card px-2 py-1.5 text-ink"
            value={from}
            onChange={(e) => setFrom(e.target.value)}
          />
        </label>
        <label className="block">
          <span className="eyebrow">To</span>
          <input
            type="date"
            className="mt-1 w-full border border-rule bg-card px-2 py-1.5 text-ink"
            value={to}
            onChange={(e) => setTo(e.target.value)}
          />
        </label>
      </div>
    </form>
  );
}
