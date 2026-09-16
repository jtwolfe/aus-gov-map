/**
 * Top-level chrome. Keep this list the single source for header + footer.
 *
 * LAWS_NAV_SLOT: a parallel Stage 3a PR may insert
 * `{ href: "/laws", label: "Laws" }` after Atlas (or Accountability).
 * Do not rename existing hrefs here without coordinating that PR.
 */
export const SITE_NAV = [
  { href: "/search", label: "Search" },
  { href: "/hearings", label: "Hearings" },
  { href: "/people", label: "People" },
  { href: "/agencies", label: "Agencies" },
  { href: "/accountability", label: "Accountability" },
  { href: "/atlas", label: "Atlas" },
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
