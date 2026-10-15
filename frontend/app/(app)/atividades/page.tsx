import Link from "next/link";
import {CheckCircle2} from "lucide-react";
import {PageHead} from "../../../components/app-shell";
import {Card} from "../../../components/ui";
import {activities} from "../../../lib/tuntum-data";
import {SOURCE, slug} from "../../../lib/portfolio";

export default function Atividades() {
  return <>
    <PageHead eyebrow={SOURCE.label} title="Atividades da semana" subtitle="Serviços relatados em cada frente de obra."/>
    <Card flush title="Relato de serviços" subtitle={activities.length + " frentes com atividade relatada"}>
      {activities.map(activity => <Link key={activity.project} href={"/obras/referencia/" + slug(activity.project)} className="list-item">
        <span className="dot-icon tone-ok"><CheckCircle2/></span>
        <div><b>{activity.project}</b><small>{activity.description}</small></div>
      </Link>)}
    </Card>
  </>;
}
