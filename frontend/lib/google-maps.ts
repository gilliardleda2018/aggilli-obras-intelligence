"use client";
/// <reference types="google.maps" />

// Loads the Maps JavaScript API once per page. The browser key is public by nature and must be restricted in the
// Google Cloud console to this site's HTTP referrers and to the Maps JavaScript API.
let loading: Promise<typeof google.maps> | null = null;

export function loadGoogleMaps(apiKey: string): Promise<typeof google.maps> {
  if (typeof window === "undefined") return Promise.reject(new Error("browser only"));
  if (typeof window.google?.maps?.importLibrary === "function") return Promise.resolve(window.google.maps);
  if (loading) return loading;
  loading = new Promise((resolve, reject) => {
    const callback = "__aggilliMapsReady";
    (window as unknown as Record<string, () => void>)[callback] = () => resolve(window.google.maps);
    const script = document.createElement("script");
    script.src = "https://maps.googleapis.com/maps/api/js?" + new URLSearchParams({
      key: apiKey, v: "weekly", loading: "async", libraries: "marker", language: "pt-BR", region: "BR", callback,
    });
    script.async = true;
    script.onerror = () => { loading = null; reject(new Error("Não foi possível carregar o Google Maps.")); };
    document.head.appendChild(script);
  });
  return loading;
}

export const RISK = {
  alto: {label: "Risco alto", color: "#dc2626"}, medio: {label: "Risco médio", color: "#d97706"}, baixo: {label: "Risco baixo", color: "#059669"},
  sem_dados: {label: "Sem dados para prever", color: "#64748b"}, concluida: {label: "Concluída", color: "#2563eb"},
} as const;
export type RiskLevel = keyof typeof RISK;

// Tuntum (MA) region, used only as the initial viewport when no work has coordinates — never as a work's location.
export const DEFAULT_CENTER = {lat: -5.26, lng: -44.65};
