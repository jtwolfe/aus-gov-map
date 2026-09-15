export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "Date to be advised";
  const [year, month, day] = iso.slice(0, 10).split("-").map(Number);
  if (!year || !month || !day) return iso;
  return new Intl.DateTimeFormat("en-AU", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(Date.UTC(year, month - 1, day)));
}

export function roleLabel(role: string): string {
  switch (role) {
    case "chair":
      return "Chair";
    case "minister":
      return "Minister";
    case "senator":
      return "Senator";
    case "official":
      return "Official";
    case "witness":
      return "Witness";
    default:
      return "Appeared";
  }
}

export function typeLabel(type: string): string {
  switch (type) {
    case "estimates":
      return "Estimates";
    case "committee":
      return "Committee";
    default:
      return type;
  }
}
