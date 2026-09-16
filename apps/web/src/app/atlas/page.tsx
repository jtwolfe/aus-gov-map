import { AtlasView } from "@/components/atlas-view";
import { loadAtlas } from "@/lib/atlas";

export const metadata = { title: "Responsibility Atlas" };
export const dynamic = "force-dynamic";

export default async function AtlasPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const raw = await searchParams;
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(raw)) {
    const v = Array.isArray(value) ? value[value.length - 1] : value;
    if (v) params.set(key, v);
  }
  const payload = await loadAtlas(params);
  return <AtlasView payload={payload} />;
}
