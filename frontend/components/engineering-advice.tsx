import {AlertTriangle, BrainCircuit, ClipboardList, Info} from "lucide-react";
import {Card} from "./ui";
import type {EngineeringAdvice} from "../lib/api";

export function EngineeringAdvicePanel({advice}: {advice: EngineeringAdvice | null}) {
  return <Card title="Engenheiro IA — diagnóstico técnico"
    subtitle="Recomendações baseadas em medições e custos registrados; nenhuma alteração automática">
    {!advice ? <p className="empty">Diagnóstico indisponível. Verifique a sessão ou tente novamente.</p> :
      <div className="stack">
        {advice.findings.map((finding, index) =>
          <div key={finding.code + ":" + index} className="list-item">
            <span className="dot-icon tone-warn">
              {finding.severity === "high" ? <AlertTriangle/> :
                finding.severity === "warning" ? <ClipboardList/> : <Info/>}
            </span>
            <div style={{flex: 1}}>
              <b>{finding.message}</b>
              <small>{finding.recommended_action}</small>
              <div className="cell-sub">Evidência: {Object.entries(finding.evidence).map(([key, value]) =>
                key + ": " + (Array.isArray(value) ? value.join("; ") : value == null ? "não informado" : String(value))).join(" · ")}</div>
            </div>
          </div>)}
        <div className="cell-sub"><BrainCircuit size={14}/> Agente consultivo v{advice.version} · avaliação {advice.evaluated_on} · sem execução de ações</div>
      </div>}
  </Card>;
}
