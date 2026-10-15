import Link from "next/link";
import {CheckCircle2} from "lucide-react";
import {PageHead} from "../../../components/app-shell";
import {Card} from "../../../components/ui";
import {getDataset} from "../../../lib/data";

export const dynamic = "force-dynamic";

export default async function Atividades() {
  const data = await getDataset();
  const withActivity = data.projects.filter(project => project.activity);
  return <>
    <PageHead eyebrow={data.sourceLabel} title="Atividades" subtitle="Último relato de serviço de cada frente de obra."/>
    <Card flush title="Relatos de campo" subtitle={withActivity.length + " obras com relato"}>
      {withActivity.map(project => <Link key={project.key} href={project.href} className="list-item">
        <span className="dot-icon tone-ok"><CheckCircle2/></span>
        <div><b>{project.name}</b><small>{project.activity}</small></div>
      </Link>)}
      {!withActivity.length && <p className="empty">Nenhum relato registrado.</p>}
    </Card>
  </>;
}
