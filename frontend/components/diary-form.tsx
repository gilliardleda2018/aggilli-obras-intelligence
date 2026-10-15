"use client";
import {useRouter} from "next/navigation";
import {useEffect, useRef, useState} from "react";
import {Camera, CheckCircle2, CloudRain, Cloud, ImagePlus, Loader2, MapPin, Sun, X} from "lucide-react";
import {createReport, refreshDiary} from "../lib/diary-actions";
import type {DiaryPhoto} from "../lib/api";
import {placeLabel} from "../lib/diary";

type Picked = {key: string; file: File; preview: string; serviceId: string};
type Position = {latitude: number; longitude: number; accuracy: number} | null;
const WEATHER = [{label: "Sol", icon: Sun}, {label: "Nublado", icon: Cloud}, {label: "Chuva", icon: CloudRain}];

const today = () => new Date(Date.now() - new Date().getTimezoneOffset() * 60_000).toISOString().slice(0, 10);

/** Phone position once per submission. Denied or unavailable is fine: photos are then sent without a location. */
function locate(): Promise<Position> {
  if (typeof navigator === "undefined" || !navigator.geolocation) return Promise.resolve(null);
  return new Promise(resolve => navigator.geolocation.getCurrentPosition(
    p => resolve({latitude: p.coords.latitude, longitude: p.coords.longitude, accuracy: p.coords.accuracy}),
    () => resolve(null), {enableHighAccuracy: true, timeout: 15_000, maximumAge: 60_000}));
}

export function DiaryForm({projectId, services}: {projectId: string; services: {id: string; name: string}[]}) {
  const router = useRouter();
  const [date, setDate] = useState(today);
  const [weather, setWeather] = useState("Sol");
  const [summary, setSummary] = useState("");
  const [photos, setPhotos] = useState<Picked[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<{sent: DiaryPhoto[]; failed: string[]} | null>(null);
  const camera = useRef<HTMLInputElement>(null);
  const gallery = useRef<HTMLInputElement>(null);

  useEffect(() => () => photos.forEach(p => URL.revokeObjectURL(p.preview)), []); // eslint-disable-line react-hooks/exhaustive-deps

  const add = (files: FileList | null) => {
    if (!files) return;
    const next = Array.from(files).filter(file => file.type.startsWith("image/"))
      .map(file => ({key: crypto.randomUUID(), file, preview: URL.createObjectURL(file), serviceId: ""}));
    setPhotos(current => [...current, ...next].slice(0, 20));
    setDone(null);
  };
  const remove = (key: string) => setPhotos(current => {
    const gone = current.find(p => p.key === key);
    if (gone) URL.revokeObjectURL(gone.preview);
    return current.filter(p => p.key !== key);
  });

  async function submit() {
    setError(null);
    if (!summary.trim() && !photos.length) return setError("Escreva o que foi feito ou adicione pelo menos uma foto.");
    let reportId: string | null = null;
    if (summary.trim()) {
      setBusy("Salvando o relato…");
      const saved = await createReport(projectId, {date, weather, summary});
      if (!saved.ok) { setBusy(null); return setError(saved.message); }
      reportId = saved.id;
    }
    const position = photos.length ? (setBusy("Pegando a localização do celular…"), await locate()) : null;
    const sent: DiaryPhoto[] = [], failed: string[] = [];
    for (const [index, photo] of photos.entries()) {
      setBusy(`Enviando foto ${index + 1} de ${photos.length}…`);
      const form = new FormData();
      form.append("file", photo.file, photo.file.name);
      if (reportId) form.append("report_id", reportId);
      if (photo.serviceId) form.append("service_id", photo.serviceId);
      if (position) {
        form.append("latitude", position.latitude.toFixed(6));
        form.append("longitude", position.longitude.toFixed(6));
        form.append("accuracy", position.accuracy.toFixed(1));
      }
      if (photo.file.lastModified) form.append("taken_at", new Date(photo.file.lastModified).toISOString());
      try {
        const response = await fetch("/api/obras/" + projectId + "/fotos", {method: "POST", body: form});
        const body = await response.json();
        if (response.ok) sent.push(body as DiaryPhoto); else failed.push(photo.file.name + ": " + (body.message ?? "erro"));
      } catch {
        failed.push(photo.file.name + ": sem conexão");
      }
    }
    photos.forEach(p => URL.revokeObjectURL(p.preview));
    setPhotos([]); setSummary(""); setBusy(null);
    setDone({sent, failed});
    await refreshDiary(projectId);
    router.refresh();
  }

  return <section className="card diary-form">
    <div className="card-head"><div><h2>Lançar o dia</h2><p>Conte o que foi feito e tire fotos. A localização do celular vai junto.</p></div></div>
    <div className="card-body">
      <label className="diary-label">Dia<input className="input" type="date" value={date} max={today()} onChange={e => setDate(e.target.value)}/></label>
      <div className="diary-label">Tempo
        <div className="chips">{WEATHER.map(({label, icon: Icon}) =>
          <button key={label} type="button" className={"chip" + (weather === label ? " on" : "")} onClick={() => setWeather(label)}
                  aria-pressed={weather === label}><Icon/>{label}</button>)}</div>
      </div>
      <label className="diary-label">O que foi feito hoje?
        <textarea className="input" rows={4} maxLength={5000} value={summary} onChange={e => setSummary(e.target.value)}
                  placeholder="Ex.: Levantamos a parede do fundo. Chegaram 2 mil tijolos. Faltou cimento à tarde."/>
      </label>

      <div className="diary-actions">
        <button type="button" className="btn primary big" onClick={() => camera.current?.click()}><Camera/>Tirar foto</button>
        <button type="button" className="btn big" onClick={() => gallery.current?.click()}><ImagePlus/>Escolher da galeria</button>
        <input ref={camera} type="file" accept="image/*" capture="environment" hidden onChange={e => { add(e.target.files); e.target.value = ""; }}/>
        <input ref={gallery} type="file" accept="image/jpeg,image/png,image/webp" multiple hidden onChange={e => { add(e.target.files); e.target.value = ""; }}/>
      </div>

      {photos.length > 0 && <div className="diary-picked">
        {photos.map(photo => <figure key={photo.key}>
          <img src={photo.preview} alt=""/>
          <button type="button" className="remove" aria-label="Tirar esta foto" onClick={() => remove(photo.key)}><X/></button>
          {services.length > 0 && <select className="select" aria-label="Etapa da obra" value={photo.serviceId}
                  onChange={e => setPhotos(cur => cur.map(p => p.key === photo.key ? {...p, serviceId: e.target.value} : p))}>
            <option value="">Etapa (opcional)</option>
            {services.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>}
        </figure>)}
      </div>}

      {error && <p className="form-error" role="alert">{error}</p>}
      {done && <div className="diary-done" role="status">
        <CheckCircle2/>
        <div><b>Lançado.</b> {done.sent.length ? done.sent.length + (done.sent.length === 1 ? " foto enviada" : " fotos enviadas") : "Relato salvo"}.
          {done.sent.length > 0 && <ul>{done.sent.map(p => <li key={p.id}><MapPin/>{placeLabel(p)}</li>)}</ul>}
          {done.failed.length > 0 && <ul className="failed">{done.failed.map(f => <li key={f}>{f}</li>)}</ul>}
        </div>
      </div>}

      <button type="button" className="btn primary big wide" disabled={Boolean(busy)} onClick={submit}>
        {busy ? <><Loader2 className="spin"/>{busy}</> : "Salvar o dia"}</button>
    </div>
  </section>;
}
