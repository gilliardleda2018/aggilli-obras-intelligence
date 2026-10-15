"use client";
import {useActionState, useState} from "react";
import {createMaterial, recordMovement, type MaterialState} from "../lib/material-actions";

const initial: MaterialState = {ok: false, message: ""};
const Feedback = ({state}: {state: MaterialState}) => <span aria-live="polite" className={"feedback " + (state.ok ? "ok" : "err")}>{state.message}</span>;

export function MaterialForm({projectId, services}: {projectId: string; services: {id: string; name: string}[]}) {
  const [state, action, pending] = useActionState(createMaterial.bind(null, projectId), initial);
  return <form action={action} className="form">
    <div className="form-grid" style={{marginBottom: 0, gridTemplateColumns: "2fr 1fr", gap: 10}}>
      <label>Material<input className="input" name="name" maxLength={200} placeholder="Ex.: Cimento CP-II 50 kg" required/></label>
      <label>Unidade<input className="input" name="unit" maxLength={30} placeholder="saco, m³, kg, un" required/></label>
      <label>Categoria<input className="input" name="category" maxLength={60} placeholder="Cimento, aço, elétrico…"/></label>
      <label>Estoque mínimo<input className="input" name="min_stock" inputMode="decimal"/></label>
      <label>Consumo previsto na obra<input className="input" name="planned_quantity" inputMode="decimal" placeholder="quantitativo total"/></label>
      <label>Serviço que consome<select className="select" name="service_id" defaultValue="">
        <option value="">— nenhum —</option>{services.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}</select></label>
    </div>
    <p className="hint">Com consumo previsto e serviço, o sistema compara o que saiu com o que o avanço medido justifica.</p>
    <div><button className="btn primary" disabled={pending}>Cadastrar material</button> <Feedback state={state}/></div>
  </form>;
}

export function MovementForm({projectId, materials}: {projectId: string; materials: {id: string; name: string; unit: string; balance: string}[]}) {
  const [state, action, pending] = useActionState(recordMovement.bind(null, projectId), initial);
  const [kind, setKind] = useState("IN");
  const today = new Date().toISOString().slice(0, 10);
  return <form action={action} className="form">
    <div className="tabs" style={{marginBottom: 4}}>
      {[["IN", "Entrada (compra/recebimento)"], ["OUT", "Saída (consumo na obra)"]].map(([value, label]) =>
        <button key={value} type="button" className={"tab" + (kind === value ? " active" : "")} onClick={() => setKind(value)}>{label}</button>)}
    </div>
    <input type="hidden" name="kind" value={kind}/>
    <label>Material<select className="select" name="material_id" required>
      {materials.map(m => <option key={m.id} value={m.id}>{m.name} — saldo {Number(m.balance).toLocaleString("pt-BR")} {m.unit}</option>)}</select></label>
    <div className="form-grid" style={{marginBottom: 0, gridTemplateColumns: "1fr 1fr", gap: 10}}>
      <label>Quantidade<input className="input" name="quantity" inputMode="decimal" required/></label>
      <label>Data<input className="input" type="date" name="movement_date" defaultValue={today} max={today}/></label>
      {kind === "IN" && <>
        <label>Custo unitário (R$)<input className="input" name="unit_cost" inputMode="decimal"/></label>
        <label>Fornecedor<input className="input" name="supplier" maxLength={200}/></label>
      </>}
    </div>
    <label>Observação<input className="input" name="note" maxLength={300} placeholder={kind === "IN" ? "Nota fiscal, pedido…" : "Frente, pavimento, serviço…"}/></label>
    {kind === "IN" && <label style={{display: "flex", gap: 8, alignItems: "center", fontWeight: 500}}>
      <input type="checkbox" name="create_expense"/> Registrar também como despesa (compra ainda não lançada)</label>}
    <div><button className="btn primary" disabled={pending || !materials.length}>Registrar {kind === "IN" ? "entrada" : "saída"}</button> <Feedback state={state}/></div>
  </form>;
}
