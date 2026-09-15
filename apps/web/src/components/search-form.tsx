"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import type { SearchMode } from "@/lib/types";

export function SearchForm({
  initialQuery = "",
  initialMode = "combined",
  size = "lg",
}: {
  initialQuery?: string;
  initialMode?: SearchMode;
  size?: "lg" | "sm";
}) {
  const router = useRouter();
  const [q, setQ] = useState(initialQuery);
  const [mode, setMode] = useState<SearchMode>(initialMode);

  function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    const params = new URLSearchParams();
    if (q.trim()) params.set("q", q.trim());
    if (mode !== "combined") params.set("mode", mode);
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
            ["semantic", "Semantic (placeholder)"],
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
    </form>
  );
}
