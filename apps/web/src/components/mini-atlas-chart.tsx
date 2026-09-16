"use client";

import { useMemo, useState } from "react";
import { AtlasChart } from "@/components/atlas-chart";
import type { AtlasPayload } from "@/lib/atlas";
import { todayUtc } from "@/lib/atlas-query";

export function MiniAtlasChart({ payload }: { payload: AtlasPayload }) {
  const initial = useMemo(() => {
    const today = todayUtc();
    if (today >= payload.window.from && today <= payload.window.to) return today;
    return payload.window.to;
  }, [payload.window.from, payload.window.to]);
  const [asOf, setAsOf] = useState(initial);
  const [focus, setFocus] = useState<string | null>(payload.params.focus);

  return (
    <div className="max-h-64 overflow-hidden">
      <AtlasChart
        payload={payload}
        compact
        asOf={asOf}
        onAsOf={setAsOf}
        focus={focus}
        onFocus={setFocus}
        showArcs={payload.params.arcs}
      />
    </div>
  );
}
