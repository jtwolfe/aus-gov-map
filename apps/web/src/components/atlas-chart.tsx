"use client";

import { useEffect, useMemo, useRef, useState, type PointerEvent } from "react";
import type { AtlasPayload } from "@/lib/atlas";
import {
  activeOn,
  addDays,
  markMatchesFocus,
  occupantsAtDate,
  openPresentStart,
  packIntervals,
  todayUtc,
} from "@/lib/atlas-query";
import { formatDate, roleTypeLabel } from "@/lib/format";

const ROLE_FILL: Record<string, string> = {
  minister: "#1a3a4a",
  secretary: "#2f5d46",
  agency_head: "#2f5d46",
  deputy: "#4a7a62",
  senator: "#6b6458",
  mp: "#6b6458",
  shadow: "#c56a2d",
  committee: "#b0892e",
  other: "#8a7f6c",
};

type Hover =
  | { kind: "tenure"; id: string; x: number; y: number }
  | { kind: "moment"; id: string; x: number; y: number }
  | { kind: "instrument"; id: string; x: number; y: number }
  | null;

export function AtlasChart({
  payload,
  compact = false,
  asOf,
  onAsOf,
  focus,
  onFocus,
  showArcs = true,
}: {
  payload: AtlasPayload;
  compact?: boolean;
  asOf: string;
  onAsOf?: (iso: string) => void;
  focus: string | null;
  onFocus?: (focus: string | null) => void;
  showArcs?: boolean;
}) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(compact ? 720 : 980);
  const [hover, setHover] = useState<Hover>(null);
  const [dragging, setDragging] = useState(false);

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const next = Math.floor(entries[0]?.contentRect.width ?? 980);
      if (next > 0) setWidth(next);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const from = payload.window.from;
  const to = payload.window.to;
  const today = todayUtc();
  const gutter = compact ? 118 : 168;
  const right = 16;
  const top = compact ? 28 : 36;
  const plotW = Math.max(240, width - gutter - right);
  const minSvg = compact ? 560 : 720;

  const xOf = (iso: string) => {
    const a = Date.parse(`${from}T00:00:00Z`);
    const b = Date.parse(`${to}T00:00:00Z`);
    const t = Date.parse(`${iso}T00:00:00Z`);
    if (!Number.isFinite(a) || !Number.isFinite(b) || b <= a) return gutter;
    const clamped = Math.min(Math.max(t, a), b);
    return gutter + ((clamped - a) / (b - a)) * plotW;
  };

  const isoAt = (px: number) => {
    const a = Date.parse(`${from}T00:00:00Z`);
    const b = Date.parse(`${to}T00:00:00Z`);
    const ratio = Math.min(1, Math.max(0, (px - gutter) / plotW));
    const t = a + ratio * (b - a);
    return new Date(t).toISOString().slice(0, 10);
  };

  const layout = useMemo(() => {
    const tenureH = compact ? 14 : 18;
    const lanePad = compact ? 8 : 12;
    let y = top;
    const lanes = payload.lanes.map((lane) => {
      const tenures = payload.tenures.filter((t) => t.laneId === lane.id);
      const packed = packIntervals(
        tenures.map((t) => ({
          id: t.id,
          start: t.start ?? from,
          end: t.end ?? to,
        })),
      );
      const rows = packed.reduce((m, p) => Math.max(m, p.row + 1), tenures.length ? 1 : 0);
      const instruments = payload.instruments.filter((i) => i.laneId === lane.id);
      const moments = payload.moments.filter((m) => m.laneId === lane.id);
      const instH = instruments.length ? (compact ? 8 : 10) : 0;
      const momentH = moments.length || tenures.length ? 14 : 0;
      const height = lanePad + rows * (tenureH + 4) + instH + momentH + 8;
      const y0 = y;
      y += height;
      return { lane, tenures, packed, rows, instruments, moments, y0, height, tenureH };
    });
    return { lanes, height: Math.max(y + 28, compact ? 160 : 220) };
  }, [payload, compact, from, to, top]);

  const presentStart = openPresentStart(payload.window, today);
  const presentX = xOf(presentStart);
  const todayX = today >= from && today <= to ? xOf(today) : null;
  const asOfX = xOf(asOf);

  const ticks = useMemo(() => yearTicks(from, to), [from, to]);

  function onPlotPointer(event: PointerEvent<SVGSVGElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    const px = event.clientX - rect.left;
    if (px < gutter - 4) return;
    onAsOf?.(isoAt(px));
  }

  const occupants = occupantsAtDate(payload.tenures, asOf);

  return (
    <div ref={wrapRef} className="relative w-full overflow-x-auto">
      <svg
        role="img"
        aria-label="Responsibility Atlas timeline. Horizontal bars are sourced tenures. Points are hearings, questions on notice, or ANAO items. Sitting in Estimates is not a tenure."
        width={Math.max(width, minSvg)}
        height={layout.height}
        className="min-w-full touch-pan-y bg-card"
        onPointerDown={(e) => {
          setDragging(true);
          (e.currentTarget as SVGSVGElement).setPointerCapture(e.pointerId);
          onPlotPointer(e);
        }}
        onPointerMove={(e) => {
          if (dragging) onPlotPointer(e);
        }}
        onPointerUp={() => setDragging(false)}
        onKeyDown={(e) => {
          if (e.key === "ArrowLeft") {
            e.preventDefault();
            onAsOf?.(clampDate(addDays(asOf, -7), from, to));
          }
          if (e.key === "ArrowRight") {
            e.preventDefault();
            onAsOf?.(clampDate(addDays(asOf, 7), from, to));
          }
          if (e.key === "Escape") onFocus?.(null);
        }}
        tabIndex={0}
      >
        <title>Responsibility Atlas</title>
        <desc>
          Time runs left to right. Swimlanes are portfolios or people. Tenure bars
          come from person roles only. Hearing points are scrutiny, not occupancy.
        </desc>
        <rect x={0} y={0} width="100%" height="100%" fill="#faf7f0" />
        <rect x={gutter} y={0} width={presentX - gutter} height={layout.height} fill="rgba(28,25,21,0.035)" />
        <rect
          x={presentX}
          y={0}
          width={Math.max(0, (todayX ?? gutter + plotW) - presentX)}
          height={layout.height}
          fill="rgba(47,93,70,0.07)"
        />
        {ticks.map((tick) => (
          <g key={tick.iso}>
            <line
              x1={xOf(tick.iso)}
              x2={xOf(tick.iso)}
              y1={0}
              y2={layout.height}
              stroke="#d4cbb8"
              strokeDasharray={tick.major ? "0" : "2 4"}
              strokeWidth={tick.major ? 1 : 0.6}
            />
            <text
              x={xOf(tick.iso) + 4}
              y={14}
              className="fill-muted"
              fontSize={10}
              fontFamily="IBM Plex Mono, ui-monospace, monospace"
            >
              {tick.label}
            </text>
          </g>
        ))}
        <text x={gutter + 6} y={layout.height - 8} fontSize={9} className="fill-muted" fontFamily="IBM Plex Mono, ui-monospace, monospace">
          Settled past
        </text>
        <text x={presentX + 6} y={layout.height - 8} fontSize={9} className="fill-eucalyptus" fontFamily="IBM Plex Mono, ui-monospace, monospace">
          Open present
        </text>

        {showArcs
          ? payload.arcs.map((arc) => {
              const fromM = payload.moments.find((m) => m.id === arc.fromMomentId);
              const toM = arc.toMomentId ? payload.moments.find((m) => m.id === arc.toMomentId) : null;
              const toI = arc.toInstrumentId
                ? payload.instruments.find((i) => i.id === arc.toInstrumentId)
                : null;
              if (!fromM) return null;
              const x1 = xOf(fromM.at);
              const y1 = laneMid(layout.lanes, fromM.laneId);
              const x2 = toM ? xOf(toM.at) : toI ? xOf(toI.start ?? from) : x1;
              const y2 = toM ? laneMid(layout.lanes, toM.laneId) : toI ? laneMid(layout.lanes, toI.laneId) : y1;
              const cpx = (x1 + x2) / 2;
              const cpy = Math.min(y1, y2) - 28;
              const dim = focus
                ? !markMatchesFocus(focus, fromM) && !(toI && markMatchesFocus(focus, toI))
                : false;
              return (
                <path
                  key={arc.id}
                  d={`M ${x1} ${y1} Q ${cpx} ${cpy} ${x2} ${y2}`}
                  fill="none"
                  stroke={arc.kind === "tested" ? "#2f5d46" : arc.kind === "ton" ? "#1a3a4a" : "#c56a2d"}
                  strokeOpacity={dim ? 0.08 : 0.45}
                  strokeWidth={1.2}
                />
              );
            })
          : null}

        {layout.lanes.map(({ lane, tenures, packed, instruments, moments, y0, height, tenureH, rows }) => {
          const laneFocus =
            !focus ||
            focus === lane.id ||
            focus === `agency:${lane.id.replace(/^agency:/, "")}` ||
            focus === `person:${lane.id.replace(/^person:/, "")}`;
          return (
            <g key={lane.id} opacity={focus && !laneFocus ? 0.18 : 1}>
              <rect x={0} y={y0} width={Math.max(width, minSvg)} height={height} fill="transparent" />
              <line x1={0} x2={Math.max(width, minSvg)} y1={y0 + height} y2={y0 + height} stroke="#d4cbb8" />
              <text
                x={8}
                y={y0 + 16}
                fontSize={compact ? 10 : 11}
                className="fill-navy"
                fontFamily="Source Serif 4, Georgia, serif"
                onClick={() => onFocus?.(focus === lane.id ? null : lane.id)}
                style={{ cursor: "pointer" }}
              >
                {truncate(lane.label, compact ? 18 : 26)}
              </text>
              <text x={8} y={y0 + 28} fontSize={8} className="fill-muted" fontFamily="IBM Plex Mono, ui-monospace, monospace">
                {lane.kind}
              </text>
              {tenures.map((t) => {
                const pack = packed.find((p) => p.id === t.id);
                const row = pack?.row ?? 0;
                const x1 = xOf(t.start ?? from);
                const x2 = xOf(t.end ?? to);
                const w = Math.max(4, x2 - x1);
                const y = y0 + 10 + row * (tenureH + 4);
                const fill = ROLE_FILL[t.roleType] ?? ROLE_FILL.other;
                const live = activeOn(t.start, t.end, asOf);
                return (
                  <a key={t.id} href={t.href ?? undefined}>
                    <rect
                      x={x1}
                      y={y}
                      width={w}
                      height={tenureH}
                      rx={2}
                      fill={fill}
                      fillOpacity={live ? 0.92 : 0.55}
                      onMouseEnter={(e) => setHover({ kind: "tenure", id: t.id, x: e.clientX, y: e.clientY })}
                      onMouseLeave={() => setHover(null)}
                      onClick={(e) => {
                        e.preventDefault();
                        onFocus?.(t.personSlug ? `person:${t.personSlug}` : lane.id);
                      }}
                    />
                    {w > 54 ? (
                      <text
                        x={x1 + 4}
                        y={y + tenureH - 4}
                        fontSize={9}
                        fill="#faf7f0"
                        fontFamily="Public Sans, sans-serif"
                      >
                        {truncate(shortName(t.personName), Math.floor(w / 6))}
                      </text>
                    ) : null}
                  </a>
                );
              })}
              {instruments.map((inst, idx) => {
                const x1 = xOf(inst.start ?? from);
                const x2 = xOf(inst.end ?? to);
                const y = y0 + 10 + rows * (tenureH + 4) + (idx % 2) * 5;
                const proposed = (inst.status ?? "").toLowerCase() === "proposed";
                return (
                  <a key={inst.id} href={inst.href}>
                    <rect
                      x={x1}
                      y={y}
                      width={Math.max(6, x2 - x1)}
                      height={compact ? 5 : 6}
                      rx={1}
                      fill={proposed ? "none" : "#b0892e"}
                      fillOpacity={0.45}
                      stroke="#b0892e"
                      strokeDasharray={proposed ? "3 2" : undefined}
                      onMouseEnter={(e) => setHover({ kind: "instrument", id: inst.id, x: e.clientX, y: e.clientY })}
                      onMouseLeave={() => setHover(null)}
                      onClick={(e) => {
                        e.preventDefault();
                        onFocus?.(`instrument:${inst.slug}`);
                      }}
                    />
                  </a>
                );
              })}
              {moments.map((m) => {
                const cx = xOf(m.at);
                const cy = y0 + height - 12;
                const overdue = m.kind === "qon" && (m.status === "overdue" || m.status === "open");
                return (
                  <a key={m.id} href={m.href ?? undefined}>
                    {m.kind === "hearing" ? (
                      <circle
                        cx={cx}
                        cy={cy}
                        r={4}
                        fill="#1a3a4a"
                        onMouseEnter={(e) => setHover({ kind: "moment", id: m.id, x: e.clientX, y: e.clientY })}
                        onMouseLeave={() => setHover(null)}
                      />
                    ) : m.kind === "anao" ? (
                      <rect
                        x={cx - 3.5}
                        y={cy - 3.5}
                        width={7}
                        height={7}
                        fill="#b0892e"
                        onMouseEnter={(e) => setHover({ kind: "moment", id: m.id, x: e.clientX, y: e.clientY })}
                        onMouseLeave={() => setHover(null)}
                      />
                    ) : (
                      <polygon
                        points={`${cx},${cy - 5} ${cx + 4.5},${cy} ${cx},${cy + 5} ${cx - 4.5},${cy}`}
                        fill={m.status === "answered" ? "#2f5d46" : "#c56a2d"}
                        stroke={overdue ? "#1c1915" : "none"}
                        strokeWidth={overdue ? 1 : 0}
                        onMouseEnter={(e) => setHover({ kind: "moment", id: m.id, x: e.clientX, y: e.clientY })}
                        onMouseLeave={() => setHover(null)}
                      />
                    )}
                  </a>
                );
              })}
            </g>
          );
        })}

        <line
          x1={asOfX}
          x2={asOfX}
          y1={0}
          y2={layout.height}
          stroke="#c56a2d"
          strokeWidth={1.4}
          strokeDasharray="3 3"
        />
        <polygon
          points={`${asOfX - 6},0 ${asOfX + 6},0 ${asOfX},10`}
          fill="#c56a2d"
        />
        {todayX != null ? (
          <line x1={todayX} x2={todayX} y1={0} y2={layout.height} stroke="#2f5d46" strokeOpacity={0.35} />
        ) : null}
      </svg>

      {hover ? <AtlasTooltip payload={payload} hover={hover} /> : null}

      {!compact ? (
        <p className="sr-only" aria-live="polite">
          As of {formatDate(asOf)}: {occupants.length} sourced occupancies in view.
        </p>
      ) : null}
    </div>
  );
}

function AtlasTooltip({
  payload,
  hover,
}: {
  payload: AtlasPayload;
  hover: Exclude<Hover, null>;
}) {
  let title = "";
  let body = "";
  if (hover.kind === "tenure") {
    const t = payload.tenures.find((x) => x.id === hover.id);
    if (!t) return null;
    title = `${t.personName} · ${roleTypeLabel(t.roleType)}`;
    body = `${formatDate(t.start)} – ${t.end ? formatDate(t.end) : "open"} · ${t.source}. Sitting in Estimates is not this bar.`;
  } else if (hover.kind === "moment") {
    const m = payload.moments.find((x) => x.id === hover.id);
    if (!m) return null;
    title = m.title;
    const chips =
      m.kind === "hearing" && m.meta
        ? ` · ${m.meta.segmentCount ?? 0} segments rolled up`
        : "";
    body = `${m.kind}${m.status ? ` · ${m.status}` : ""} · ${formatDate(m.at)}${chips}. Public record; no guilt label.`;
  } else {
    const i = payload.instruments.find((x) => x.id === hover.id);
    if (!i) return null;
    title = i.title;
    body = `${i.type}${i.status ? ` · ${i.status}` : ""} · ${formatDate(i.start)} – ${i.end ? formatDate(i.end) : "open"}`;
  }
  return (
    <div
      className="pointer-events-none fixed z-20 max-w-xs border border-rule bg-card px-3 py-2 text-xs shadow-sm"
      style={{ left: hover.x + 12, top: hover.y + 12 }}
    >
      <p className="font-serif text-sm text-navy">{title}</p>
      <p className="mt-1 text-muted">{body}</p>
    </div>
  );
}

function yearTicks(from: string, to: string) {
  const startYear = Number(from.slice(0, 4));
  const endYear = Number(to.slice(0, 4));
  const ticks: { iso: string; label: string; major: boolean }[] = [];
  for (let y = startYear; y <= endYear + 1; y++) {
    const iso = `${y}-01-01`;
    if (iso < from || iso > to) {
      if (iso.slice(0, 4) === from.slice(0, 4)) {
        ticks.push({ iso: from, label: from.slice(0, 4), major: true });
      }
      continue;
    }
    ticks.push({ iso, label: String(y), major: true });
  }
  if (ticks.length < 2) {
    ticks.push({ iso: from, label: from.slice(0, 7), major: true });
  }
  return ticks;
}

function laneMid(
  lanes: { lane: { id: string }; y0: number; height: number }[],
  laneId: string,
) {
  const hit = lanes.find((l) => l.lane.id === laneId);
  return hit ? hit.y0 + hit.height / 2 : 40;
}

function truncate(value: string, n: number) {
  return value.length > n ? `${value.slice(0, n - 1)}…` : value;
}

function shortName(name: string) {
  const parts = name.replace(/^Senator the Hon |^the Hon |^Professor |^Dr /i, "").split(/\s+/);
  return parts[parts.length - 1] || name;
}

function clampDate(iso: string, min: string, max: string) {
  if (iso < min) return min;
  if (iso > max) return max;
  return iso;
}
