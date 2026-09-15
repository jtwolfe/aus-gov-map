import Link from "next/link";

const NAV = [
  { href: "/search", label: "Search" },
  { href: "/hearings", label: "Hearings" },
  { href: "/people", label: "People" },
  { href: "/boards", label: "Boards" },
  { href: "/about", label: "About" },
];

export function SiteHeader() {
  return (
    <header className="border-b border-rule/80 bg-card/70 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-6 px-5 py-4">
        <Link href="/" className="group flex items-baseline gap-2">
          <span className="font-serif text-xl tracking-tight text-navy">aus-gov-map</span>
          <span className="hidden text-[11px] uppercase tracking-[0.18em] text-muted sm:inline">
            Stage 1
          </span>
          <span className="block h-px w-8 bg-gold transition-all group-hover:w-12" />
        </Link>
        <nav className="flex flex-wrap items-center gap-x-5 gap-y-1 text-sm text-navy">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="hover:text-ochre"
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
