/**
 * Top-level chrome. Keep this list the single source for header + footer.
 */
export const SITE_NAV = [
  { href: "/search", label: "Search" },
  { href: "/hearings", label: "Hearings" },
  { href: "/people", label: "People" },
  { href: "/agencies", label: "Agencies" },
  { href: "/accountability", label: "Accountability" },
  { href: "/atlas", label: "Atlas" },
  { href: "/laws", label: "Laws" },
  { href: "/insights", label: "Insights" },
  { href: "/boards", label: "Boards" },
  { href: "/about", label: "About" },
] as const;

export function navIsActive(pathname: string, href: string): boolean {
  if (pathname === href) return true;
  if (href === "/accountability") {
    return pathname.startsWith("/accountability/");
  }
  if (href === "/about") return false;
  return pathname.startsWith(`${href}/`);
}
