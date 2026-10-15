"use client";
import {useRouter} from "next/navigation";
import {useRef, useState} from "react";
import {Camera, ImagePlus, Loader2} from "lucide-react";
import type {FieldDoc} from "../lib/api";

/** Phone position once per batch; denied or unavailable just means the work is chosen by hand. */
function locate(): Promise<GeolocationPosition["coords"] | null> {
  if (typeof navigator === "undefined" || !navigator.geolocation) return Promise.resolve(null);
  return new Promise(resolve => navigator.geolocation.getCurrentPosition(p => resolve(p.coords), () => resolve(null),
    {enableHighAccuracy: true, timeout: 15_000, maximumAge: 60_000}));
}

export function DocumentCapture({projectId}: {projectId?: string}) {
  const router = useRouter();
  const camera = useRef<HTMLInputElement>(null);
  const gallery = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [errors, setErrors] = useState<string[]>([]);

  async function send(files: FileList | null) {
    const list = Array.from(files ?? []).filter(file => file.type.startsWith("image/")).slice(0, 10);
    if (!list.length) return;
    setErrors([]);
    setBusy("Pegando a localização do celular…");
    const position = await locate();
    const sent: FieldDoc[] = [], failed: string[] = [];
    for (const [index, file] of list.entries()) {
      setBusy(list.length > 1 ? `Lendo documento ${index + 1} de ${list.length}…` : "Lendo o documento…");
      const form = new FormData();
      form.append("file", file, file.name);
      if (projectId) form.append("project_id", projectId);
      if (position) {
        form.append("latitude", position.latitude.toFixed(6));
        form.append("longitude", position.longitude.toFixed(6));
        form.append("accuracy", position.accuracy.toFixed(1));
      }
      if (file.lastModified) form.append("taken_at", new Date(file.lastModified).toISOString());
      try {
        const response = await fetch("/api/documentos", {method: "POST", body: form});
        const body = await response.json();
        if (response.ok) sent.push(body as FieldDoc); else failed.push(file.name + ": " + (body.message ?? "erro"));
      } catch {
        failed.push(file.name + ": sem conexão");
      }
    }
    setBusy(null);
    setErrors(failed);
    if (sent.length === 1 && !failed.length) router.push("/documentos/" + sent[0].id);
    else router.refresh();
  }

  return <div>
    <div className="diary-actions">
      <button type="button" className="btn primary big" disabled={Boolean(busy)} onClick={() => camera.current?.click()}><Camera/>Fotografar documento</button>
      <button type="button" className="btn big" disabled={Boolean(busy)} onClick={() => gallery.current?.click()}><ImagePlus/>Escolher da galeria</button>
      <input ref={camera} type="file" accept="image/*" capture="environment" hidden onChange={e => { send(e.target.files); e.target.value = ""; }}/>
      <input ref={gallery} type="file" accept="image/jpeg,image/png,image/webp" multiple hidden onChange={e => { send(e.target.files); e.target.value = ""; }}/>
    </div>
    {busy && <p className="diary-count" role="status"><Loader2 className="spin"/>{busy}</p>}
    {errors.length > 0 && <div className="form-error" role="alert">{errors.map(e => <div key={e}>{e}</div>)}</div>}
  </div>;
}
