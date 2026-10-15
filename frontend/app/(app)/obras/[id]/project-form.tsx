"use client";
import {useActionState} from "react";
import {updateProject} from "./actions";

export type ProjectDetails = {
  municipality: string | null; address: string | null; responsible: string | null; cost_center: string | null; status: string;
  budget: string | null; start_date: string | null; end_date: string | null; latitude: string | null; longitude: string | null;
};
const STATUS = [["PLANNED", "Planejada"], ["IN_PROGRESS", "Em execução"], ["PAUSED", "Paralisada"], ["DONE", "Concluída"],
  ["COST_POOL", "Despesas a ratear"]];

export function ProjectForm({id, details}: {id: string; details: ProjectDetails}) {
  const [state, action, pending] = useActionState(updateProject.bind(null, id), {ok: false, message: ""});
  return <form action={action} className="form">
    <div className="form-grid" style={{marginBottom: 0, gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))"}}>
      <label>Situação<select className="select" name="status" defaultValue={details.status}>
        {STATUS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
      <label>Responsável<input className="input" name="responsible" maxLength={200} defaultValue={details.responsible ?? ""}/></label>
      <label>Município<input className="input" name="municipality" maxLength={120} defaultValue={details.municipality ?? ""}/></label>
      <label>Endereço<input className="input" name="address" maxLength={300} defaultValue={details.address ?? ""}/></label>
      <label>Centro de custo<input className="input" name="cost_center" maxLength={60} defaultValue={details.cost_center ?? ""}/></label>
      <label>Orçamento contratual (R$)<input className="input" name="budget" inputMode="decimal" defaultValue={details.budget ?? ""}
        placeholder="não informado"/></label>
      <label>Início<input className="input" type="date" name="start_date" defaultValue={details.start_date ?? ""}/></label>
      <label>Término previsto<input className="input" type="date" name="end_date" defaultValue={details.end_date ?? ""}/></label>
    </div>
    <div style={{display: "flex", gap: 12, alignItems: "center"}}>
      <button className="btn primary" disabled={pending}>{pending ? "Salvando…" : "Salvar dados da obra"}</button>
      <span aria-live="polite" className={"feedback " + (state.ok ? "ok" : "err")}>{state.message}</span>
    </div>
  </form>;
}
