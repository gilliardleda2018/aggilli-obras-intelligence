import Link from "next/link";
import {ArrowLeft, Lock} from "lucide-react";
import {PageHead} from "../../../../components/app-shell";
import {Badge, Callout} from "../../../../components/ui";
import {DocumentReview} from "../../../../components/document-review";
import {apiGet, type FieldDoc} from "../../../../lib/api";
import {getDataset} from "../../../../lib/data";

export const dynamic = "force-dynamic";

export default async function DocumentPage({params}: {params: Promise<{id: string}>}) {
  const {id} = await params;
  const back = <Link href="/documentos" className="back"><ArrowLeft/>Notas e recibos</Link>;
  const [doc, data] = await Promise.all([/^[a-f0-9-]{36}$/i.test(id) ? apiGet<FieldDoc>("/documents/" + id) : null, getDataset()]);
  if (!doc) return <>{back}<Callout icon={Lock}>Documento indisponível ou acesso não autorizado.</Callout></>;
  const projects = data.source === "api"
    ? data.projects.filter(p => p.status !== "COST_POOL").map(p => ({id: p.key, name: p.name})).sort((a, b) => a.name.localeCompare(b.name, "pt-BR"))
    : [];
  const image = <a href={"/api/documentos/" + doc.id} target="_blank" rel="noopener" className="doc-image">
    <img src={"/api/documentos/" + doc.id} alt="Foto do documento" width={doc.width} height={doc.height}/></a>;

  return <>
    {back}
    <PageHead eyebrow={doc.kind_label ?? "Documento"} title={doc.draft.supplier || "Documento enviado"}
              subtitle={"Enviado por " + doc.recorded_by + " em " + new Date(doc.created_at).toLocaleString("pt-BR", {timeZone: "America/Fortaleza"})}/>
    <div className="diary-grid">
      {doc.status === "PENDING" ? <DocumentReview doc={doc} projects={projects}/> : <section className="card"><div className="card-body">
        <Badge tone={doc.status === "CONFIRMED" ? "ok" : "neutral"}>{doc.status === "CONFIRMED" ? "Conferido" : "Descartado"}</Badge>
        {doc.project && <p>Obra: <Link className="link" href={"/obras/" + doc.project_id}>{doc.project}</Link></p>}
        {doc.confirmed_by && <p>Conferido por {doc.confirmed_by}</p>}
      </div></section>}
      <div className="stack">{image}</div>
    </div>
  </>;
}
