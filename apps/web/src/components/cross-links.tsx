import Link from "next/link";

export type CrossLink = { href: string; label: string };

export function CrossLinks({ items }: { items: CrossLink[] }) {
  const seen = new Set<string>();
  const links = items.filter((item) => {
    if (!item.href || seen.has(item.href)) return false;
    seen.add(item.href);
    return true;
  });
  if (!links.length) return null;
  return (
    <nav className="mt-4 flex flex-wrap gap-x-4 gap-y-1 text-sm" aria-label="Related layers">
      {links.map((item) => (
        <Link key={item.href} href={item.href} className="link">
          {item.label}
        </Link>
      ))}
    </nav>
  );
}
