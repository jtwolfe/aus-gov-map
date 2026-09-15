"use client";

import { useEffect, useState } from "react";

type BoardOption = { id: string; slug: string; title: string };

type LocalPin = {
  pinType: string;
  targetId: string;
  href: string;
  label: string;
};

const STORAGE_KEY = "aus-gov-map:local-pins";

function readLocalPins(): LocalPin[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]") as LocalPin[];
  } catch {
    return [];
  }
}

export function PinButton({
  pinType,
  targetId,
  href,
  label,
}: {
  pinType: string;
  targetId: string;
  href: string;
  label: string;
}) {
  const [boards, setBoards] = useState<BoardOption[]>([]);
  const [boardSlug, setBoardSlug] = useState("");
  const [persist, setPersist] = useState(false);
  const [pinned, setPinned] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/boards")
      .then((res) => res.json())
      .then((data) => {
        if (cancelled) return;
        const list = (data.boards ?? []) as BoardOption[];
        setBoards(list);
        setPersist(Boolean(data.persist));
        if (list[0] && !boardSlug) setBoardSlug(list[0].slug);
      })
      .catch(() => {
        if (!cancelled) setPersist(false);
      });
    setPinned(readLocalPins().some((p) => p.targetId === targetId && p.pinType === pinType));
    return () => {
      cancelled = true;
    };
    // boardSlug is seeded once from the first fetch
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pinType, targetId]);

  async function pinRemote() {
    setBusy(true);
    setMessage(null);
    try {
      const res = await fetch("/api/pins", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pinType,
          targetId,
          boardSlug: boardSlug || undefined,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || "Could not pin");
      }
      setPinned(true);
      setMessage(`Pinned to ${data.board?.title ?? "board"}`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Pin failed");
    } finally {
      setBusy(false);
    }
  }

  function pinLocal() {
    const current = readLocalPins();
    const exists = current.some((p) => p.targetId === targetId && p.pinType === pinType);
    const next = exists
      ? current.filter((p) => !(p.targetId === targetId && p.pinType === pinType))
      : [...current, { pinType, targetId, href, label }];
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    setPinned(!exists);
  }

  if (persist) {
    return (
      <div className="flex flex-wrap items-center gap-2">
        {boards.length ? (
          <select
            className="border border-rule bg-card px-2 py-1.5 text-xs text-ink"
            value={boardSlug}
            onChange={(e) => setBoardSlug(e.target.value)}
          >
            {boards.map((board) => (
              <option key={board.id} value={board.slug}>
                {board.title}
              </option>
            ))}
          </select>
        ) : null}
        <button
          type="button"
          disabled={busy}
          onClick={pinRemote}
          className={`border px-3 py-1.5 text-xs uppercase tracking-[0.12em] ${
            pinned
              ? "border-ochre bg-ochre/10 text-ochre"
              : "border-rule text-muted hover:border-navy hover:text-navy"
          }`}
        >
          {busy ? "Pinning…" : pinned ? "Pinned" : "Pin to board"}
        </button>
        {message ? <span className="text-xs text-muted">{message}</span> : null}
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={pinLocal}
      className={`border px-3 py-1.5 text-xs uppercase tracking-[0.12em] ${
        pinned
          ? "border-ochre bg-ochre/10 text-ochre"
          : "border-rule text-muted hover:border-navy hover:text-navy"
      }`}
      title="Postgres is down — pin is stored in this browser only"
    >
      {pinned ? "Pinned locally" : "Pin locally"}
    </button>
  );
}

export function LocalPinList() {
  const [pins, setPins] = useState<LocalPin[]>([]);

  useEffect(() => {
    setPins(readLocalPins());
  }, []);

  if (!pins.length) {
    return (
      <p className="text-sm text-muted">
        Browser-only fallback. When Postgres is up, use “Pin to board” to persist.
      </p>
    );
  }

  return (
    <ul className="space-y-2 text-sm">
      {pins.map((pin) => (
        <li key={`${pin.pinType}-${pin.targetId}`}>
          <a href={pin.href} className="link">
            {pin.label}
          </a>
          <span className="ml-2 text-xs uppercase tracking-[0.12em] text-muted">{pin.pinType}</span>
        </li>
      ))}
    </ul>
  );
}

export function CreateBoardForm() {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/api/boards", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, description }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Could not create board");
      window.location.href = `/boards/${data.board.slug}`;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="border border-rule bg-card p-4">
      <p className="eyebrow">New board</p>
      <label className="mt-3 block text-sm">
        <span className="text-muted">Title</span>
        <input
          required
          className="mt-1 w-full border border-rule bg-paper px-3 py-2 text-ink"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="FOI follow-ups"
        />
      </label>
      <label className="mt-3 block text-sm">
        <span className="text-muted">Description</span>
        <textarea
          className="mt-1 w-full border border-rule bg-paper px-3 py-2 text-ink"
          rows={2}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </label>
      {error ? <p className="mt-2 text-sm text-ochre">{error}</p> : null}
      <button
        type="submit"
        disabled={busy}
        className="mt-3 bg-navy px-4 py-2 text-sm text-paper hover:bg-eucalyptus disabled:opacity-60"
      >
        {busy ? "Creating…" : "Create board"}
      </button>
    </form>
  );
}
