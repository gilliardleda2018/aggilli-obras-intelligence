import {AlertTriangle, Info, Scale} from "lucide-react";
import {Card} from "./ui";
import type {FinancialDiagnosis} from "../lib/api";

export function FinancialDiagnosisPanel({data}: {data: FinancialDiagnosis | null}) {
  return <Card title="Financeiro IA — auditoria consultiva"
    subtitle="Alertas com evidências; nenhuma baixa ou pagamento automático">
    {!data ? <p className="empty">Diagnóstico indisponível. Verifique sua sessão e tente novamente.</p> :
      !data.findings.length ? <p className="empty">Nenhuma divergência adicional identificada nos registros acessíveis.</p> :
      <div className="stack">
        {data.findings.map((f, i) => <div key={f.code + f.project_id + i} className="list-item">
          <span className="dot-icon tone-warn">{f.severity === "high" ? <AlertTriangle/> : f.severity === "warning" ? <Scale/> : <Info/>}</span>
          <div style={{flex: 1}}>
            <b>{f.message}</b>
            <small>{f.recommended_action}</small>
            <div className="cell-sub">Evidência: {Object.entries(f.evidence).map(([k,v]) =>
              k + ": " + (v == null ? "não informado" : String(v))).join(" · ")}</div>
          </div>
        </div>)}
        <div className="cell-sub">Agente consultivo v{data.version} · {data.projects} registros de projeto autorizados · nenhuma ação executada</div>
      </div>}
  </Card>;
}
