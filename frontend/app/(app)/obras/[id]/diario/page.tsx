import Link from "next/link";
import {ArrowLeft, Cloud, CloudRain, Images, Lock, MapPinOff, Sun} from "lucide-react";
import {PageHead} from "../../../../../components/app-shell";
import {Badge, Callout, Card} from "../../../../../components/ui";
import {DiaryForm} from "../../../../../components/diary-form";
import {apiGet, type Diary} from "../../../../../lib/api";
import {longDate, placeLabel, placeTone} from "../../../../../lib/diary";

export const dynamic = "force-dynamic";
const WEATHER_ICON: Record<string, typeof Sun> = {Sol: Sun, Nublado: Cloud, Chuva: CloudRain};

export default async function DiaryPage({params, searchParams}: {params: Promise<{id: string}>; searchParams: Promise<{etapa?: string}>}) {
  const [{id}, {etapa}] = await Promise.all([params, searchParams]);
  const back = <Link href={"/obras/" + id} className="back"><ArrowLeft/>Obra</Link>;
  const diary = /^[a-f0-9-]{36}$/i.test(id) ? await apiGet<Diary>("/projects/" + id + "/diary") : null;
  if (!diary) return <>{back}<Callout icon={Lock}>Obra indisponível ou acesso não autorizado.</Callout></>;
  const stage = diary.services.find(s => s.id === etapa);
  const days = diary.days
    .map(day => ({...day, photos: stage ? day.photos.filter(p => p.service_id === stage.id) : day.photos, reports: stage ? [] : day.reports}))
    .filter(day => day.reports.length || day.photos.length);
  const total = days.reduce((n, day) => n + day.photos.length, 0);

  return <>
    {back}
    <PageHead eyebrow="Diário de obra" title={diary.project.name}
              subtitle="O dia a dia da obra: o que foi feito, o tempo e as fotos com o lugar onde foram tiradas."/>
    {!diary.project.located && <div style={{marginBottom: 16}}><Callout tone="info" icon={MapPinOff}>
      A obra ainda não tem localização confirmada, então não dá para conferir se as fotos foram tiradas no local.{" "}
      <Link className="link" href={"/obras/" + id + "/localizacao"}>Definir localização</Link></Callout></div>}

    <div className="diary-grid">
      <DiaryForm projectId={id} services={diary.services}/>

      <div className="stack">
        {diary.services.length > 0 && <nav className="chips" aria-label="Fotos por etapa">
          <Link className={"chip" + (!stage ? " on" : "")} href={"/obras/" + id + "/diario"}>Tudo</Link>
          {diary.services.map(s => <Link key={s.id} className={"chip" + (stage?.id === s.id ? " on" : "")}
                                         href={"/obras/" + id + "/diario?etapa=" + s.id}>{s.name}</Link>)}
        </nav>}
        {stage && <p className="diary-count"><Images/>{total} {total === 1 ? "foto" : "fotos"} da etapa {stage.name}, da mais recente para a mais antiga</p>}

        {days.map(day => <Card key={day.date} title={longDate(day.date)}>
          {day.reports.map(report => {
            const Icon = WEATHER_ICON[report.weather] ?? Cloud;
            return <div key={report.id} className="diary-report"><Badge tone="neutral"><Icon size={14}/> {report.weather}</Badge><p>{report.summary}</p></div>;
          })}
          {day.photos.length > 0 && <div className="diary-photos">
            {day.photos.map(photo => <figure key={photo.id}>
              <a href={"/api/fotos/" + photo.id} target="_blank" rel="noopener">
                <img src={"/api/fotos/" + photo.id} alt={photo.caption ?? "Foto da obra"} loading="lazy" width={photo.width} height={photo.height}/></a>
              <figcaption>
                <Badge tone={placeTone(photo.place)}>{placeLabel(photo)}</Badge>
                {photo.service && <small>{photo.service}</small>}
                {photo.taken_at && <small>{new Date(photo.taken_at).toLocaleTimeString("pt-BR", {hour: "2-digit", minute: "2-digit", timeZone: "America/Fortaleza"})}
                  {photo.taken_at_source === "EXIF" ? " · hora da câmera" : ""}</small>}
              </figcaption>
            </figure>)}
          </div>}
        </Card>)}
        {!days.length && <Card><p className="empty">{stage ? "Nenhuma foto desta etapa ainda." :
          "Nada lançado ainda. Use “Lançar o dia” para registrar o que foi feito e as fotos."}</p></Card>}
      </div>
    </div>
  </>;
}
