import type {DiaryPhoto} from "./api";

const km = (meters: number) => meters < 1000 ? meters + " m" : (meters / 1000).toLocaleString("pt-BR", {maximumFractionDigits: 1}) + " km";

/** Where the photo was taken, in words, with the provenance of the position. */
export function placeLabel(photo: Pick<DiaryPhoto, "place" | "distance_m" | "location_source">): string {
  const by = photo.location_source === "EXIF" ? " (GPS da câmera)" : photo.location_source === "DEVICE" ? " (GPS do celular)" : "";
  switch (photo.place) {
    case "NA_OBRA": return "Na obra" + by;
    case "FORA_DA_OBRA": return "Fora da obra, a " + km(photo.distance_m ?? 0) + by;
    case "OBRA_SEM_LOCAL": return "Com localização; obra ainda sem endereço confirmado";
    default: return "Sem localização";
  }
}

export const placeTone = (place: DiaryPhoto["place"]) =>
  place === "NA_OBRA" ? "ok" as const : place === "FORA_DA_OBRA" ? "danger" as const : "neutral" as const;

export function longDate(iso: string): string {
  const text = new Date(iso + "T12:00:00").toLocaleDateString("pt-BR", {weekday: "long", day: "numeric", month: "long", timeZone: "America/Fortaleza"});
  return text.charAt(0).toUpperCase() + text.slice(1);
}
