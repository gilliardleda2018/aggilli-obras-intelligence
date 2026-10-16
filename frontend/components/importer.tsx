"use client";
import {useActionState} from "react";
import Link from "next/link";
import {AlertTriangle, CheckCircle2, FileSpreadsheet, Sparkles, Upload} from "lucide-react";
import {commitImport, uploadSpreadsheet, type PreviewState} from "../lib/import-actions";
import {Badge} from "./ui";

const CATEGORIES = [["MATERIAL", "Material"], ["LABOR", "Mão de obra"], ["SERVICE", "Serviço"], ["FUEL", "Combustível"],
  ["EQUIPMENT", "Equipamento"], ["OTHER", "Outros"]];
const LABEL = Object.fromEntries(CATEGORIES);
const FIELD = {date: "Data", project: "Obra", supplier: "Fornecedor", description: "Descrição / serviço", amount: "Valor", category: "Categoria",
  status: "Situação", reference: "Comprovante", notes: "Observações", quantity: "Quantidade", unit: "Unidade"} as Record<string, string>;
const money = (v?: string | null) => (v ? Number(v).toLocaleString("pt-BR", {style: "currency", currency: "BRL"}) : "—");
const br = (iso: string | null) => (iso ? iso.split("-").reverse().join("/") : "sem data");

export function Importer({projects, organizations = []}: {projects: {id: string; name: string}[]; organizations?: {id: string; name: string; role: string}[]}) {
  const [state, upload, uploading] = useActionState(uploadSpreadsheet, {ok: false, message: ""} as PreviewState);
  const [result, confirm, confirming] = useActionState(commitImport, {ok: false, message: ""} as PreviewState);
  const preview = state.preview;

  if (result.committed) return <div className="card card-body" style={{paddingTop: 18}}>
    <div className="callout info"><CheckCircle2/><div><b>{result.committed.created} {result.committed.kind === "expenses" ? "despesas" : "medições"} importadas</b>
      {result.committed.skipped ? ` · ${result.committed.skipped} linhas deixadas de fora (com problema ou repetidas)` : ""}.
      {result.committed.kind === "expenses" ? " Custos, obrigações e previsões já foram atualizados."
        : " As medições aguardam aprovação do engenheiro; depois de aprovadas, o avanço e as previsões são recalculados."}</div></div>
    <div className="actions" style={{marginTop: 14}}>
      <Link className="btn primary" href="/inteligencia">Ver previsões</Link>
      <Link className="btn" href={result.committed.kind === "expenses" ? "/financeiro" : "/medicoes"}>Ver lançamentos</Link>
      <a className="btn" href="/importar">Importar outra planilha</a>
    </div>
  </div>;

  return <div className="stack">
    <form action={upload} className="card card-body form" style={{paddingTop: 18}}>
      <div style={{display: "flex", gap: 14, alignItems: "center"}}>
        <span className="kpi-icon tone-brand"><FileSpreadsheet/></span>
        <div><b>Envie a planilha como ela é</b><p className="hint">Excel (.xlsx) ou CSV. O sistema encontra o cabeçalho, reconhece as colunas,
          identifica a obra de cada linha, sugere a categoria e aponta repetições — você só confere e confirma.</p></div>
      </div>
      {organizations.length === 1 && <input type="hidden" name="organization_id" value={organizations[0].id}/>}
      {organizations.length > 1 && <label>Organização<select className="select" name="organization_id" required defaultValue="">
        <option value="">Selecione a organização</option>{organizations.map(o => <option key={o.id} value={o.id}>{o.name}</option>)}
      </select></label>}
      <div className="form-grid" style={{marginBottom: 0, gridTemplateColumns: "2fr 1fr"}}>
        <label>Arquivo<input className="input" type="file" name="file" accept=".xlsx,.xlsm,.csv" required style={{paddingTop: 6}}/></label>
        <label>Obra padrão (linhas sem obra)<select className="select" name="default_project_id" defaultValue="">
          <option value="">Identificar pela planilha</option>{projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
      </div>
      <div><button className="btn primary" disabled={uploading}><Upload/>{uploading ? "Lendo planilha…" : "Ler planilha"}</button>
        {" "}<span className="feedback err">{state.message}</span></div>
    </form>

    {preview && <form action={confirm} className="card">
      <input type="hidden" name="batch_id" value={preview.id}/>
      <div className="card-head"><div><h2>{preview.filename}</h2>
        <p>{preview.summary.kind === "expenses" ? "Despesas" : "Medições"} · {preview.summary.valid} linhas prontas · {preview.summary.with_issues} com
          problema{preview.summary.total ? " · total " + money(preview.summary.total) : ""}</p></div>
        <button className="btn primary" disabled={confirming || !preview.summary.valid}><CheckCircle2/>{confirming ? "Importando…" : "Confirmar importação"}</button>
      </div>
      <div className="card-body" style={{display: "flex", gap: 8, flexWrap: "wrap"}}>
        {Object.entries(preview.summary.columns).map(([field, column]) => <Badge key={field} tone="info">{FIELD[field] ?? field} ← “{column}”</Badge>)}
        {preview.summary.kind === "expenses" && <Badge tone="ok"><Sparkles size={12}/> categorias por {preview.summary.classifier.method === "modelo"
          ? "modelo treinado em " + preview.summary.classifier.trained_on + " lançamentos" : "regras (o modelo aprende com o uso)"}</Badge>}
      </div>
      <div className="table-wrap"><table>
        <thead><tr><th>Linha</th><th>Obra</th><th>Data</th>
          {preview.summary.kind === "expenses" ? <><th>Fornecedor / descrição</th><th>Categoria sugerida</th><th className="num">Valor</th></>
            : <><th>Serviço</th><th className="num">Quantidade</th></>}<th>Situação</th></tr></thead>
        <tbody>{preview.rows.map(row => <tr key={row.line} style={row.ok ? undefined : {background: "var(--warn-50)"}}>
          <td>{row.line}</td>
          <td>{row.project ? <>{row.project}{row.project_text && row.project_score !== null && row.project_score < 1 &&
              <span className="cell-sub">“{row.project_text}”</span>}</> :
            <select className="select" name={"project_" + row.line} defaultValue=""><option value="">Escolha a obra</option>
              {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select>}</td>
          <td>{br(row.date)}</td>
          {preview.summary.kind === "expenses" ? <>
            <td><b>{row.supplier}</b><span className="cell-sub">{row.description}</span></td>
            <td><select className="select" name={"category_" + row.line} defaultValue={row.category}>
              {CATEGORIES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
              {row.classification && <span className="cell-sub" title={row.classification.reason}>
                {row.classification.method} · {Math.round(row.classification.confidence * 100)}%</span>}</td>
            <td className="num"><b>{money(row.amount)}</b>{row.paid && <span className="cell-sub">pago</span>}</td>
          </> : <>
            <td><b>{row.service}</b></td><td className="num">{row.quantity ?? "—"} {row.unit ?? ""}</td>
          </>}
          <td>{row.ok ? <Badge tone="ok">Pronta</Badge> : <Badge tone="warn">Revisar</Badge>}
            {row.issues.map(issue => <div key={issue} className="note"><AlertTriangle/>{issue}</div>)}</td>
        </tr>)}</tbody>
      </table></div>
      <div className="card-body"><span className="feedback err">{result.message}</span>
        <p className="hint">Linhas com problema ficam de fora; corrija na planilha e importe de novo — as linhas já importadas não se repetem.
          Categoria e obra podem ser ajustadas aqui antes de confirmar ({preview.summary.kind === "expenses" ? LABEL.MATERIAL + ", " + LABEL.LABOR + "…" : "medições entram pendentes"}).</p></div>
    </form>}
  </div>;
}
