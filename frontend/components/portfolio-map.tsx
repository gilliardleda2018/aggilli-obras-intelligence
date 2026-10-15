"use client";
/// <reference types="google.maps" />
import Link from "next/link";
import {useEffect, useMemo, useRef, useState} from "react";
import {MarkerClusterer} from "@googlemaps/markerclusterer";
import {MapPin, MapPinOff} from "lucide-react";
import type {MapProject} from "../lib/api";
import {DEFAULT_CENTER, RISK, loadGoogleMaps, type RiskLevel} from "../lib/google-maps";

const STATUS: Record<string, string> = {PLANNED: "Planejada", IN_PROGRESS: "Em execução", PAUSED: "Paralisada", DONE: "Concluída"};
const unique = (values: (string | null)[]) => [...new Set(values.filter((v): v is string => !!v))].sort((a, b) => a.localeCompare(b));
const pct = (value: number | null) => (value === null ? "—" : value.toLocaleString("pt-BR", {maximumFractionDigits: 1}) + "%");
const escape = (text: string) => text.replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"})[c]!);

function infoHtml(p: MapProject) {
  const risk = RISK[p.risk.level as RiskLevel];
  return `<div class="map-info"><b>${escape(p.name)}</b><div>${escape([p.municipality, p.organization].filter(Boolean).join(" · "))}</div>
    <div>${escape(STATUS[p.status] ?? p.status)} · avanço ${pct(p.progress)}</div>
    <div style="color:${risk.color};font-weight:650">${risk.label}${p.risk.reasons.length ? ": " + escape(p.risk.reasons.join("; ")) : ""}</div>
    <a href="/obras/${p.id}">Abrir painel da obra →</a></div>`;
}

export function PortfolioMap({projects, apiKey, mapId}: {projects: MapProject[]; apiKey: string; mapId: string}) {
  const [filters, setFilters] = useState({municipality: "", organization: "", responsible: "", status: "", risk: ""});
  const [error, setError] = useState("");
  const element = useRef<HTMLDivElement>(null);
  const state = useRef<{map?: google.maps.Map; clusterer?: MarkerClusterer; info?: google.maps.InfoWindow}>({});
  const visible = useMemo(() => projects.filter(p =>
    (!filters.municipality || p.municipality === filters.municipality) && (!filters.organization || p.organization === filters.organization) &&
    (!filters.responsible || p.responsible === filters.responsible) && (!filters.status || p.status === filters.status) &&
    (!filters.risk || p.risk.level === filters.risk)), [projects, filters]);
  const located = visible.filter(p => p.location.latitude !== null);
  const missing = visible.filter(p => p.location.latitude === null);

  useEffect(() => {
    if (!apiKey || !element.current) return;
    let cancelled = false;
    loadGoogleMaps(apiKey).then(async maps => {
      if (cancelled || !element.current) return;
      const {Map, InfoWindow} = await maps.importLibrary("maps") as google.maps.MapsLibrary;
      const {AdvancedMarkerElement, PinElement} = await maps.importLibrary("marker") as google.maps.MarkerLibrary;
      const s = state.current;
      s.map ??= new Map(element.current, {center: DEFAULT_CENTER, zoom: 9, mapId, mapTypeControl: true, streetViewControl: false,
        fullscreenControl: true, gestureHandling: "cooperative"});
      s.info ??= new InfoWindow();
      s.clusterer?.clearMarkers();
      const bounds = new maps.LatLngBounds();
      const markers = located.map(p => {
        const position = {lat: p.location.latitude!, lng: p.location.longitude!};
        bounds.extend(position);
        const pin = new PinElement({background: RISK[p.risk.level as RiskLevel].color, borderColor: "#ffffff", glyphColor: "#ffffff"});
        const marker = new AdvancedMarkerElement({position, title: p.name, content: pin.element});
        marker.addListener("click", () => { s.info!.setContent(infoHtml(p)); s.info!.open({map: s.map, anchor: marker}); });
        return marker;
      });
      s.clusterer = new MarkerClusterer({map: s.map, markers});
      if (markers.length === 1) { s.map.setCenter(bounds.getCenter()); s.map.setZoom(15); }
      else if (markers.length > 1) s.map.fitBounds(bounds, 48);
    }).catch(e => setError(e instanceof Error ? e.message : String(e)));
    return () => { cancelled = true; };
  }, [apiKey, mapId, located]);

  const select = (name: keyof typeof filters, label: string, options: [string, string][]) =>
    <label>{label}<select className="select" value={filters[name]} onChange={e => setFilters({...filters, [name]: e.target.value})}>
      <option value="">Todos</option>{options.map(([value, text]) => <option key={value} value={value}>{text}</option>)}</select></label>;

  return <>
    <div className="card" style={{marginBottom: 18}}><div className="card-body">
      <div className="form" style={{gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))", display: "grid"}}>
        {select("municipality", "Município", unique(projects.map(p => p.municipality)).map(v => [v, v]))}
        {select("organization", "Empresa", unique(projects.map(p => p.organization)).map(v => [v, v]))}
        {select("responsible", "Responsável", unique(projects.map(p => p.responsible)).map(v => [v, v]))}
        {select("status", "Situação", unique(projects.map(p => p.status)).map(v => [v, STATUS[v] ?? v]))}
        {select("risk", "Risco", Object.entries(RISK).map(([v, r]) => [v, r.label]))}
      </div>
    </div></div>
    <div className="grid-main">
      <div className="card" style={{overflow: "hidden"}}>
        {apiKey ? <div ref={element} className="map-canvas" role="region" aria-label="Mapa das obras"/>
          : <div className="map-canvas map-empty"><MapPinOff/><b>Mapa aguardando a chave do Google Maps</b>
            <span>Configure GOOGLE_MAPS_BROWSER_KEY (restrita ao domínio do painel). As obras e filtros continuam disponíveis ao lado.</span></div>}
        {error && <p className="empty" style={{color: "var(--danger)"}}>{error}</p>}
        <div className="map-legend">{Object.entries(RISK).map(([key, r]) =>
          <span key={key}><i style={{background: r.color}}/>{r.label}</span>)}</div>
      </div>
      <div className="stack">
        <div className="card"><div className="card-head"><div><h2>No mapa ({located.length})</h2><p>Clique no marcador para abrir o painel</p></div></div>
          {located.map(p => <Link key={p.id} href={"/obras/" + p.id} className="list-item">
            <span className="dot" style={{background: RISK[p.risk.level as RiskLevel].color}}/>
            <div style={{flex: 1}}><b>{p.name}</b><small>{[p.municipality, STATUS[p.status], "avanço " + pct(p.progress)].filter(Boolean).join(" · ")}
              {p.location.refresh_due && " · coordenada do Google a renovar"}</small></div></Link>)}
          {!located.length && <p className="empty">Nenhuma obra com localização confirmada neste filtro.</p>}
        </div>
        <div className="card"><div className="card-head"><div><h2>Sem localização ({missing.length})</h2>
          <p>Coordenadas nunca são estimadas: defina pelo endereço, no mapa ou no local</p></div></div>
          {missing.map(p => <Link key={p.id} href={"/obras/" + p.id + "/localizacao"} className="list-item">
            <MapPin size={16}/><div style={{flex: 1}}><b>{p.name}</b><small>{p.address ?? p.municipality ?? "endereço não informado"}</small></div>
            <span className="link">Definir</span></Link>)}
          {!missing.length && <p className="empty">Todas as obras deste filtro estão localizadas.</p>}
        </div>
      </div>
    </div>
  </>;
}
