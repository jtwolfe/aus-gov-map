"use client";

import { useEffect, useState } from "react";

const STORAGE_KEY = "aus-gov-map:local-pins";

type LocalPin = {
  pinType: string;
  targetId: string;
  href: string;
  label: string;
};

function readPins(): LocalPin[] {
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
  const [pinned, setPinned] = useState(false);

  useEffect(() => {
    setPinned(readPins().some((p) => p.targetId === targetId && p.pinType === pinType));
  }, [pinType, targetId]);

  function toggle() {
    const current = readPins();
    const exists = current.some((p) => p.targetId === targetId && p.pinType === pinType);
    const next = exists
      ? current.filter((p) => !(p.targetId === targetId && p.pinType === pinType))
      : [...current, { pinType, targetId, href, label }];
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    setPinned(!exists);
  }

  return (
    <button
      type="button"
      onClick={toggle}
      className={`border px-3 py-1.5 text-xs uppercase tracking-[0.12em] ${
        pinned
          ? "border-ochre bg-ochre/10 text-ochre"
          : "border-rule text-muted hover:border-navy hover:text-navy"
      }`}
    >
      {pinned ? "Pinned" : "Pin to board"}
    </button>
  );
}

export function LocalPinList() {
  const [pins, setPins] = useState<LocalPin[]>([]);

  useEffect(() => {
    setPins(readPins());
  }, []);

  if (!pins.length) {
    return (
      <p className="text-sm text-muted">
        Nothing pinned in this browser yet. Use “Pin to board” on a hearing or person.
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
