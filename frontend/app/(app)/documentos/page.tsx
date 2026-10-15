import Link from "next/link";
import {CheckCircle2, ChevronRight, FileText, Lock, MapPin} from "lucide-react";
import {PageHead} from "../../../components/app-shell";
import {Badge, Callout, Card} from "../../../components/ui";
import {DocumentCapture} from "../../../components/document-capture";
import {apiGet, type FieldDoc} from "../../../lib/api";

export const dynamic = "force-dynamic";

/** Field team: photograph receipts and invoices; the office (or the same person) checks and posts them. */
export default async function Documents({searchParams}: {searchParams: Promise<{ok?: string}>}) {
  const [{ok}, pending] = await Promise.all([searchParams, apiGet<FieldDoc[]>("/documents?status=PENDING")]);
  if (!pending) return <><PageHead eyebrow="Campo" title="Notas e recibos"/>
    <Callout icon={Lock}>Entre no sistema para enviar documentos.</Callout></>;
  return <>
    <PageHead eyebrow="Campo" title="Notas e recibos"
              subtitle="Fotografe a nota, o recibo ou o orçamento. O sistema lê os valores e sugere a obra pelo GPS; você confere e lança."/>
    {ok && <div className="diary-done" role="status"><CheckCircle2/><div><b>Lançado.</b> O documento foi conferido e guardado na obra.</div></div>}
    <div className="diary-grid">
      <Card title="Enviar documento" subtitle="Tire a foto de frente, com o documento inteiro e bem iluminado.">
        <DocumentCapture/>
      </Card>
      <Card title={pending.length ? `Para conferir (${pending.length})` : "Para conferir"} flush>
        {pending.map(doc => <Link key={doc.id} href={"/documentos/" + doc.id} className="simple-row">
          <span className="dot-icon tone-brand"><FileText/></span>
          <div>
            <b>{doc.draft.supplier || doc.kind_label || "Documento"}{doc.draft.amount ? " · R$ " + doc.draft.amount.replace(".", ",") : ""}</b>
            <span><MapPin size={13}/> {doc.suggested_project ?? "Obra a escolher"}
              {doc.problems.length > 0 && <> · <Badge tone="warn">conferir</Badge></>}</span>
          </div>
          <ChevronRight aria-hidden/>
        </Link>)}
        {!pending.length && <p className="empty">Nenhum documento esperando conferência.</p>}
      </Card>
    </div>
  </>;
}
