"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { navIsActive, SITE_NAV } from "@/lib/nav";

export function SiteHeader() {
  const pathname = usePathname() || "/";
  return (
    <header className="border-b border-rule/80 bg-card/70 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-6 px-5 py-4">
        <Link href="/" className="group flex items-baseline gap-2">
          <span className="font-serif text-xl tracking-tight text-navy">aus-gov-map</span>
          <span className="hidden text-[11px] uppercase tracking-[0.18em] text-muted sm:inline">
            Stage 2
          </span>
          <span className="block h-px w-8 bg-gold transition-all group-hover:w-12" />
        </Link>
        <nav className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-navy sm:gap-x-5">
          {SITE_NAV.filter((item) => item.href !== "/about").map((item) => {
            const active = navIsActive(pathname, item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={active ? "text-ochre" : "hover:text-ochre"}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
