import {Suspense} from "react";
import {Info} from "lucide-react";
import {PageHead} from "../../../components/app-shell";
import {PrintButton} from "../../../components/print-button";
import {Callout, Kpi} from "../../../components/ui";
import {money, SOURCE, totals} from "../../../lib/portfolio";
import {CalendarClock, HardHat, Package} from "lucide-react";
import {FopagTable} from "./fopag-table";

export default function Fopag() {
  const t = totals();
  return <>
    <PageHead eyebrow={SOURCE.label} title="FOPAG semanal" subtitle="Programação de pagamentos da semana, por fornecedor, equipe e obra."
              actions={<PrintButton/>}/>
    <div className="kpis">
      <Kpi label="Total programado" value={money(t.weekly)} note={t.items + " lançamentos"} icon={CalendarClock}/>
      <Kpi label="Mão de obra" value={money(t.labor)} note={t.laborItems + " lançamentos"} icon={HardHat} tone="info"/>
      <Kpi label="Materiais, serviços e outros" value={money(t.other)} note={t.items - t.laborItems + " lançamentos"} icon={Package} tone="ok"/>
      <Kpi label="Com observação" value={String(t.flagged)} note="itens a conferir antes de pagar" icon={Info} tone="warn"/>
    </div>
    <div style={{marginBottom: 18}}>
      <Callout tone="info" icon={Info}>Valores transcritos da {SOURCE.label}. Nenhuma baixa bancária foi presumida: o pagamento só conta
        como realizado depois do registro do comprovante.</Callout>
    </div>
    <Suspense><FopagTable/></Suspense>
  </>;
}
