"use client";
import Link from "next/link";
import {useRouter} from "next/navigation";
import {useState} from "react";
import {AlertTriangle, CheckCircle2, Loader2, MapPin, Trash2} from "lucide-react";
import type {DocKind, FieldDoc} from "../lib/api";
import {confirmDocument, discardDocument} from "../lib/document-actions";

const KINDS: [DocKind, string][] = [["NOTA_FISCAL", "Nota fiscal"], ["RECIBO", "Recibo"], ["COMPROVANTE", "Comprovante de pagamento"],
  ["ORCAMENTO", "Orçamento (não é gasto)"], ["OUTRO", "Outro"]];
const CATEGORIES = [["MATERIAL", "Material"], ["LABOR", "Mão de obra"], ["SERVICE", "Serviço"], ["FUEL", "Combustível"],
  ["EQUIPMENT", "Equipamento"], ["OTHER", "Outros"]];
const brl = (value: string | null) => value ? value.replace(".", ",") : "";

export function DocumentReview({doc, projects}: {doc: FieldDoc; projects: {id: string; name: string}[]}) {
  const router = useRouter();
  const d = doc.draft;
  const [form, setForm] = useState({
    project_id: doc.suggested_project_id ?? "", kind: doc.kind ?? "RECIBO", supplier: d.supplier, description: d.description,
    amount: brl(d.amount), expense_date: d.expense_date ?? "", category: d.category ?? "OTHER", notes: "",
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<{message: string; duplicate?: boolean} | null>(null);
  const set = (key: keyof typeof form) => (e: {target: {value: string}}) => setForm(f => ({...f, [key]: e.target.value}));

  async function confirm(allowDuplicate = false) {
    setBusy(true); setError(null);
    const result = await confirmDocument(doc.id, {...form, expense_date: form.expense_date || null, notes: form.notes || null,
      allow_duplicate: allowDuplicate});
    setBusy(false);
    if (result.ok) router.push("/documentos?ok=1"); else setError(result);
  }
  async function discard() {
    if (!window.confirm("Descartar este documento? Ele não entra nos gastos.")) return;
    setBusy(true);
    const result = await discardDocument(doc.id);
    setBusy(false);
    if (result.ok) router.push("/documentos"); else setError(result);
  }

  const warnings = [...doc.problems, ...d.issues.filter(issue => !doc.problems.includes(issue))];
  return <section className="card">
    <div className="card-head"><div><h2>Conferir e lançar</h2>
      <p>{doc.engine ? "Valores lidos automaticamente. Confira cada campo antes de lançar." : "Preencha os dados do documento."}</p></div></div>
    <div className="card-body">
      <p className="doc-place"><MapPin/>{doc.suggestion_reason ?? "Sem localização"}</p>
      {doc.read_error && <p className="form-error">Não foi possível ler o documento ({doc.read_error}). Preencha à mão.</p>}
      {warnings.length > 0 && <div className="callout"><AlertTriangle/><div><b>Confira com atenção:</b>
        <ul className="doc-issues">{warnings.map(w => <li key={w}>{w}</li>)}</ul></div></div>}
      {doc.nfe && <p className="doc-nfe"><CheckCircle2/>Chave da {doc.nfe.model} válida: nº {doc.nfe.number}, série {doc.nfe.series},
        emitente {doc.nfe.cnpj}, {doc.nfe.uf} {doc.nfe.year_month}</p>}

      <label className="diary-label">Obra
        <select className="input" value={form.project_id} onChange={set("project_id")} required>
          <option value="">Escolha a obra…</option>
          {projects.map(p => <option key={p.id} value={p.id}>{p.name}{p.id === doc.suggested_project_id ? " (sugerida)" : ""}</option>)}
        </select></label>
      <label className="diary-label">Tipo
        <select className="input" value={form.kind} onChange={set("kind")}>{KINDS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
      <label className="diary-label">Fornecedor{d.supplier_cnpj && <small className="doc-hint">CNPJ/CPF lido: {d.supplier_cnpj}</small>}
        <input className="input" value={form.supplier} onChange={set("supplier")} maxLength={200}/></label>
      <label className="diary-label">Descrição
        <input className="input" value={form.description} onChange={set("description")} maxLength={300}/></label>
      <div className="doc-row">
        <label className="diary-label">Valor (R$)
          <input className="input" inputMode="decimal" value={form.amount} onChange={set("amount")} placeholder="0,00"/></label>
        <label className="diary-label">Data
          <input className="input" type="date" value={form.expense_date} onChange={set("expense_date")}/></label>
      </div>
      <label className="diary-label">Categoria{d.category_reason && <small className="doc-hint">sugestão: {d.category_reason}</small>}
        <select className="input" value={form.category} onChange={set("category")}>{CATEGORIES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
      <label className="diary-label">Observação
        <input className="input" value={form.notes} onChange={set("notes")} maxLength={500}/></label>

      {d.items.length > 0 && <details className="doc-items"><summary>{d.items.length} {d.items.length === 1 ? "item lido" : "itens lidos"}</summary>
        <ul>{d.items.map((item, i) => <li key={i}>{item.quantity ?? ""} {item.unit ?? ""} {item.description}
          {item.total != null && <b> R$ {item.total.toFixed(2).replace(".", ",")}</b>}</li>)}</ul></details>}

      {error && <div className="form-error" role="alert">{error.message}
        {error.duplicate && <button type="button" className="btn" onClick={() => confirm(true)}>É outro gasto, lançar mesmo assim</button>}</div>}
      <button type="button" className="btn primary big wide" disabled={busy || !form.project_id} onClick={() => confirm()}>
        {busy ? <><Loader2 className="spin"/>Salvando…</> : form.kind === "ORCAMENTO" ? "Guardar orçamento na obra" : "Confirmar e lançar gasto"}</button>
      <div className="doc-footer">
        <button type="button" className="btn" disabled={busy} onClick={discard}><Trash2/>Descartar</button>
        <Link className="link" href="/documentos">Voltar</Link>
      </div>
    </div>
  </section>;
}
