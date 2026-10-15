import {Suspense} from "react";
import {AlertTriangle, CalendarClock, HardHat, Info, Package} from "lucide-react";
import {PageHead} from "../../../components/app-shell";
import {PrintButton} from "../../../components/print-button";
import {Callout, Kpi} from "../../../components/ui";
import {getDataset, summarize} from "../../../lib/data";
import {money} from "../../../lib/portfolio";
import {FopagTable} from "./fopag-table";

export const dynamic = "force-dynamic";

export default async function Fopag() {
  const data = await getDataset();
  const t = summarize(data);
  return <>
    {data.error && <div style={{marginBottom: 16}}><Callout icon={AlertTriangle}>{data.error}</Callout></div>}
    <PageHead eyebrow={data.sourceLabel + " · " + data.weekLabel} title="FOPAG semanal"
              subtitle="Pagamentos programados da semana, por fornecedor, equipe e obra." actions={<PrintButton/>}/>
    <div className="kpis">
      <Kpi label="Total da semana" value={money(t.weekly)} note={t.items + " lançamentos"} icon={CalendarClock}/>
      <Kpi label="Mão de obra" value={money(t.labor)} note={t.laborItems + " lançamentos"} icon={HardHat} tone="info"/>
      <Kpi label="Materiais, serviços e outros" value={money(t.other)} note={t.items - t.laborItems + " lançamentos"} icon={Package} tone="ok"/>
      <Kpi label="Com observação" value={String(t.flagged)} note="itens a conferir antes de pagar" icon={Info} tone="warn"/>
    </div>
    <div style={{marginBottom: 18}}>
      <Callout tone="info" icon={Info}>Pagamento só conta como realizado depois do registro do comprovante. Nenhuma baixa bancária é
        presumida a partir da programação.</Callout>
    </div>
    <Suspense><FopagTable rows={data.schedule} fileName={"fopag-" + data.weekLabel.replace(/[^0-9a-z]+/gi, "-").toLowerCase() + ".csv"}/></Suspense>
  </>;
}
