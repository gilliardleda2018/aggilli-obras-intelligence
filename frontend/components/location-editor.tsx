"use client";
/// <reference types="google.maps" />
import {useEffect, useRef, useState, useTransition} from "react";
import {Crosshair, MapPinOff, Search} from "lucide-react";
import type {GeoCandidate, GeoLocation} from "../lib/api";
import {geocodeAddress, saveLocation, type LocationInput} from "../lib/geo-actions";
import {DEFAULT_CENTER, loadGoogleMaps} from "../lib/google-maps";

const SOURCE: Record<string, string> = {
  GEOCODED: "endereço geocodificado (Google)", MAP: "marcado no mapa", FIELD: "GPS no local da obra", MANUAL: "coordenadas digitadas",
};
const fmt = (value: number) => value.toLocaleString("pt-BR", {minimumFractionDigits: 6, maximumFractionDigits: 6});
const parse = (text: string) => { const n = Number(text.trim().replace(",", ".")); return text.trim() && Number.isFinite(n) ? n : null; };
type Draft = LocationInput & {latitude: number; longitude: number; label: string};

export function LocationEditor({projectId, address, location, canEdit, apiKey, mapId}:
  {projectId: string; address: string | null; location: GeoLocation; canEdit: boolean; apiKey: string; mapId: string}) {
  const [query, setQuery] = useState(address ?? "");
  const [candidates, setCandidates] = useState<GeoCandidate[]>([]);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [manual, setManual] = useState({lat: "", lng: ""});
  const [message, setMessage] = useState<{ok: boolean; text: string} | null>(null);
  const [street, setStreet] = useState<string>("");
  const [pending, start] = useTransition();
  const mapEl = useRef<HTMLDivElement>(null);
  const panoEl = useRef<HTMLDivElement>(null);
  const refs = useRef<{map?: google.maps.Map; saved?: google.maps.marker.AdvancedMarkerElement; draft?: google.maps.marker.AdvancedMarkerElement}>({});
  const saved = location.latitude !== null ? {lat: location.latitude, lng: location.longitude!} : null;
  const point = draft ? {lat: draft.latitude, lng: draft.longitude} : saved;

  // Map with the confirmed point and the draft (click or drag = point placed by a person).
  useEffect(() => {
    if (!apiKey || !mapEl.current) return;
    let cancelled = false;
    loadGoogleMaps(apiKey).then(async maps => {
      if (cancelled || !mapEl.current) return;
      const {Map} = await maps.importLibrary("maps") as google.maps.MapsLibrary;
      const {AdvancedMarkerElement, PinElement} = await maps.importLibrary("marker") as google.maps.MarkerLibrary;
      const r = refs.current;
      if (!r.map) {
        r.map = new Map(mapEl.current, {center: saved ?? DEFAULT_CENTER, zoom: saved ? 17 : 10, mapId, mapTypeId: "hybrid",
          streetViewControl: false, gestureHandling: "cooperative"});
        if (canEdit) r.map.addListener("click", (e: google.maps.MapMouseEvent) => e.latLng &&
          setDraft({latitude: e.latLng.lat(), longitude: e.latLng.lng(), source: "MAP", label: "ponto marcado no mapa"}));
      }
      if (saved && !r.saved) r.saved = new AdvancedMarkerElement({map: r.map, position: saved, title: "Localização confirmada",
        content: new PinElement({background: "#0e7c86", borderColor: "#ffffff", glyphColor: "#ffffff"}).element});
      if (r.saved && saved) r.saved.position = saved;
      else if (r.saved) { r.saved.map = null; r.saved = undefined; }
      if (draft) {
        if (!r.draft) {
          r.draft = new AdvancedMarkerElement({map: r.map, gmpDraggable: canEdit, title: "Nova localização (não salva)",
            content: new PinElement({background: "#d97706", borderColor: "#ffffff", glyphColor: "#ffffff"}).element});
          r.draft.addListener("dragend", () => {
            const p = r.draft!.position as google.maps.LatLngLiteral;
            setDraft({latitude: p.lat, longitude: p.lng, source: "MAP", label: "pino ajustado no mapa"});
          });
        }
        r.draft.map = r.map;
        r.draft.position = {lat: draft.latitude, lng: draft.longitude};
        r.map.panTo({lat: draft.latitude, lng: draft.longitude});
        if ((r.map.getZoom() ?? 0) < 16) r.map.setZoom(17);
      } else if (r.draft) r.draft.map = null;
    }).catch(e => setMessage({ok: false, text: e instanceof Error ? e.message : String(e)}));
    return () => { cancelled = true; };
  }, [apiKey, mapId, canEdit, draft, saved?.lat, saved?.lng]); // eslint-disable-line react-hooks/exhaustive-deps

  // Street View: only as a reference of the surroundings, with the image date — never as evidence of current progress.
  useEffect(() => {
    if (!apiKey || !point || !panoEl.current) { setStreet(""); return; }
    let cancelled = false;
    loadGoogleMaps(apiKey).then(async maps => {
      const {StreetViewService, StreetViewPanorama, StreetViewSource} = await maps.importLibrary("streetView") as google.maps.StreetViewLibrary;
      new StreetViewService().getPanorama({location: point, radius: 50, sources: [StreetViewSource.OUTDOOR]}, (data, status) => {
        if (cancelled || !panoEl.current) return;
        if (status !== "OK" || !data?.location?.pano) { setStreet("none"); return; }
        new StreetViewPanorama(panoEl.current, {pano: data.location.pano, addressControl: false, motionTracking: false});
        setStreet(data.imageDate ?? "data não informada");
      });
    });
    return () => { cancelled = true; };
  }, [apiKey, point?.lat, point?.lng]); // eslint-disable-line react-hooks/exhaustive-deps

  const search = () => start(async () => {
    setMessage(null);
    const result = await geocodeAddress(projectId, query);
    if (!result.ok) { setMessage({ok: false, text: result.message}); return; }
    setCandidates(result.data.candidates);
    if (!result.data.candidates.length) setMessage({ok: false, text: "Nenhum resultado para este endereço. Ajuste o texto ou marque no mapa."});
  });

  const gps = () => {
    if (!navigator.geolocation) { setMessage({ok: false, text: "Este dispositivo não informa a localização."}); return; }
    setMessage({ok: true, text: "Obtendo a posição do dispositivo…"});
    navigator.geolocation.getCurrentPosition(p => {
      const meters = Math.round(p.coords.accuracy);
      setDraft({latitude: p.coords.latitude, longitude: p.coords.longitude, source: "FIELD", accuracy: "GPS ±" + meters + " m",
        label: "posição do dispositivo (±" + meters + " m)"});
      setMessage(meters > 100 ? {ok: false, text: `Precisão baixa (±${meters} m). Use ao ar livre, no terreno da obra.`} : null);
    }, error => setMessage({ok: false, text: "Localização negada ou indisponível: " + error.message}), {enableHighAccuracy: true, timeout: 20000});
  };

  const confirm = (input: LocationInput, success: string) => start(async () => {
    const result = await saveLocation(projectId, input);
    setMessage(result.ok ? {ok: true, text: success} : {ok: false, text: result.message});
    if (result.ok) { setDraft(null); setCandidates([]); }
  });

  return <div className="grid-main">
    <div className="stack">
      <div className="card" style={{overflow: "hidden"}}>
        {apiKey ? <div ref={mapEl} className="map-canvas" aria-label="Mapa da obra"/>
          : <div className="map-canvas small map-empty"><MapPinOff/><b>Mapa aguardando a chave do Google Maps</b>
            <span>Ainda é possível confirmar a localização pelo GPS no local ou digitando as coordenadas.</span></div>}
        <div className="map-legend">
          <span><i style={{background: "#0e7c86"}}/>Localização confirmada</span><span><i style={{background: "#d97706"}}/>Nova localização (não salva)</span>
          {canEdit && apiKey && <span>Clique no mapa ou arraste o pino para ajustar</span>}
        </div>
      </div>
      {apiKey && <div className="card" style={{overflow: "hidden"}}>
        <div className="card-head"><div><h2>Street View</h2><p>Referência do entorno — não comprova a situação atual da obra</p></div></div>
        <div ref={panoEl} className="map-canvas small" style={{display: street && street !== "none" ? "block" : "none"}}/>
        <div className="card-body">
          {!point && <p className="empty">Defina a localização para consultar o Street View.</p>}
          {point && street === "none" && <p className="empty">Sem cobertura do Street View num raio de 50 m deste ponto.</p>}
          {point && street && street !== "none" && <p className="hint">Imagem do Google de <b>{street.split("-").reverse().join("/")}</b>. Mostra o local
            na data da captura e <b>não é evidência da execução atual</b>; o andamento vale pelas medições e fotos da obra.</p>}
        </div>
      </div>}
    </div>

    <div className="stack">
      <div className="card"><div className="card-head"><div><h2>Localização atual</h2></div></div><div className="card-body">
        {saved ? <p style={{margin: 0}}><b>{fmt(saved.lat)}, {fmt(saved.lng)}</b><br/>
          <small className="hint">Origem: {SOURCE[location.source ?? ""] ?? "não registrada"}{location.accuracy ? " · " + location.accuracy : ""}
            {location.confirmed_by ? " · confirmada por " + location.confirmed_by : ""}
            {location.confirmed_at ? " em " + new Date(location.confirmed_at).toLocaleDateString("pt-BR") : ""}</small>
          {location.refresh_due && <><br/><small style={{color: "var(--warn)"}}>Coordenada do Google com mais de 30 dias: será renovada pelo identificador do local.</small></>}
          <br/><a className="link" target="_blank" rel="noreferrer"
                  href={`https://www.google.com/maps/dir/?api=1&destination=${saved.lat},${saved.lng}`}>Abrir rota no Google Maps</a></p>
          : <p className="empty" style={{padding: 0}}>Obra ainda sem localização. Coordenadas nunca são estimadas.</p>}
      </div></div>

      {canEdit && <>
        {draft && <div className="card"><div className="card-head"><div><h2>Confirmar nova localização</h2><p>{draft.label}</p></div></div>
          <div className="card-body form">
            <b>{fmt(draft.latitude)}, {fmt(draft.longitude)}</b>
            <div style={{display: "flex", gap: 8, flexWrap: "wrap"}}>
              <button className="btn primary" disabled={pending} onClick={() => confirm(draft, "Localização confirmada.")}>Confirmar localização</button>
              <button className="btn" disabled={pending} onClick={() => setDraft(null)}>Descartar</button>
            </div>
          </div></div>}

        <div className="card"><div className="card-head"><div><h2>Pelo endereço</h2><p>O Google sugere; você confere e confirma</p></div></div>
          <div className="card-body form">
            <div style={{display: "flex", gap: 8}}>
              <input className="input" value={query} onChange={e => setQuery(e.target.value)} maxLength={300} placeholder="Rua, número, bairro"/>
              <button className="btn" disabled={pending || !query.trim()} onClick={search}><Search/>Buscar</button>
            </div>
            {candidates.map(c => <button key={c.place_id} type="button" style={{textAlign: "left", background: "none", cursor: "pointer"}}
              className={"candidate" + (draft?.place_id === c.place_id ? " selected" : "")}
              onClick={() => setDraft({latitude: c.latitude, longitude: c.longitude, source: "GEOCODED", accuracy: c.accuracy, place_id: c.place_id,
                label: c.formatted_address})}>
              <b>{c.formatted_address}</b>
              <small className="hint">{c.accuracy === "ROOFTOP" ? "ponto exato do endereço" : c.accuracy === "RANGE_INTERPOLATED" ? "posição interpolada na rua" : "ponto aproximado"}</small>
              {c.warnings.length > 0 && <ul>{c.warnings.map(w => <li key={w}>{w}</li>)}</ul>}
            </button>)}
          </div></div>

        <div className="card"><div className="card-head"><div><h2>No local da obra</h2><p>Use o GPS do celular estando no terreno</p></div></div>
          <div className="card-body"><button className="btn" onClick={gps} disabled={pending}><Crosshair/>Usar minha localização</button></div></div>

        <div className="card"><div className="card-head"><div><h2>Coordenadas conferidas</h2><p>De levantamento topográfico, projeto ou GPS</p></div></div>
          <div className="card-body form">
            <div style={{display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8}}>
              <label>Latitude<input className="input" inputMode="decimal" value={manual.lat} onChange={e => setManual({...manual, lat: e.target.value})} placeholder="-5,258123"/></label>
              <label>Longitude<input className="input" inputMode="decimal" value={manual.lng} onChange={e => setManual({...manual, lng: e.target.value})} placeholder="-44,648988"/></label>
            </div>
            <div><button className="btn" disabled={parse(manual.lat) === null || parse(manual.lng) === null}
              onClick={() => setDraft({latitude: parse(manual.lat)!, longitude: parse(manual.lng)!, source: "MANUAL", label: "coordenadas digitadas"})}>
              Ver no mapa</button></div>
          </div></div>

        {saved && <button className="btn" disabled={pending} onClick={() => confirm({latitude: null, longitude: null, source: null}, "Localização removida.")}>
          Remover localização</button>}
      </>}
      {message && <p aria-live="polite" className={"feedback " + (message.ok ? "ok" : "err")}>{message.text}</p>}
    </div>
  </div>;
}
