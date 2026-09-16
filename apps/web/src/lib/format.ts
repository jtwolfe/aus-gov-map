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

export function roleTypeLabel(type: string): string {
  switch (type) {
    case "minister":
      return "Minister";
    case "shadow":
      return "Shadow";
    case "secretary":
      return "Secretary";
    case "deputy":
      return "Deputy";
    case "committee":
      return "Committee";
    case "mp":
      return "MP";
    case "senator":
      return "Senator";
    case "agency_head":
      return "Agency head";
    default:
      return type;
  }
}

export function instrumentTypeLabel(type: string): string {
  switch (type) {
    case "program":
      return "Program";
    case "measure":
      return "Measure";
    case "bill":
      return "Bill";
    case "act":
      return "Act";
    case "contract":
      return "Contract";
    case "grant":
      return "Grant";
    case "policy":
      return "Policy";
    default:
      return type;
  }
}
