import Link from "next/link";
import {Camera, ChevronRight} from "lucide-react";
import {PageHead} from "../../../components/app-shell";
import {Card} from "../../../components/ui";
import {getDataset} from "../../../lib/data";

export const dynamic = "force-dynamic";

/** Entry point for the field team on the phone: pick the work, then log the day. */
export default async function DiaryIndex() {
  const data = await getDataset();
  const works = data.source === "api"
    ? data.projects.filter(p => p.status !== "COST_POOL").sort((a, b) => a.name.localeCompare(b.name, "pt-BR")) : [];
  return <>
    <PageHead eyebrow="Campo" title="Diário de obra" subtitle="Escolha a obra para lançar o dia e as fotos."/>
    <Card flush>
      {works.map(work => <Link key={work.key} href={"/obras/" + work.key + "/diario"} className="simple-row">
        <span className="dot-icon tone-brand"><Camera/></span>
        <div><b>{work.name}</b><span>{work.activity ?? "Sem relato ainda"}</span></div>
        <ChevronRight aria-hidden/>
      </Link>)}
      {!works.length && <p className="empty">Entre no sistema para lançar o diário das obras.</p>}
    </Card>
  </>;
}
