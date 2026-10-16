import Link from "next/link";
import {AlertTriangle, FileSearch, Info} from "lucide-react";
import {Card} from "./ui";
import type {DocumentAuditDiagnosis} from "../lib/api";

export function DocumentAuditPanel({data}: {data: DocumentAuditDiagnosis | null}) {
  return <Card title="Auditor Documental IA"
    subtitle="Conferência de extrações, origem e pendências; nenhum lançamento automático">
    {!data ? <p className="empty">Diagnóstico indisponível. Confira sua sessão.</p> :
      !data.documents.length ? <p className="empty">Nenhum documento disponível para análise.</p> :
      <div className="stack">
        {data.documents.map(doc => <div key={doc.document_id} className="list-item">
          <span className="dot-icon tone-brand"><FileSearch/></span>
          <div style={{flex: 1}}>
            <Link href={"/documentos/" + encodeURIComponent(doc.document_id)} className="link">
              <b>Documento {doc.document_id.slice(0, 8)}</b>
            </Link>
            {doc.findings.map((f,i) => <div key={f.code+i} style={{marginTop: 6}}>
              {f.severity === "warning" ? <AlertTriangle size={14}/> : <Info size={14}/>}
              {" "}{f.message} <span className="cell-sub">{f.recommended_action}</span>
            </div>)}
          </div>
        </div>)}
        <div className="cell-sub">{data.documents.length} documentos analisados · agente consultivo v{data.version}</div>
      </div>}
  </Card>;
}
