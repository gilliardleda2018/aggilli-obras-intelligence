"use client";
import {useActionState, useState} from "react";
import {Check, X} from "lucide-react";
import {createService, decideMeasurement, recordMeasurement, type ActionState} from "../lib/measurement-actions";

const initial: ActionState = {ok: false, message: ""};
export type ServiceOption = {id: string; name: string; unit: string; remaining_quantity: string};

function Feedback({state}: {state: ActionState}) {
  return <span aria-live="polite" className={"feedback " + (state.ok ? "ok" : "err")}>{state.message}</span>;
}

export function ServiceForm({projectId, available}: {projectId: string; available: string}) {
  const [state, action, pending] = useActionState(createService.bind(null, projectId), initial);
  return <form action={action} className="form">
    <label>Serviço<input className="input" name="name" maxLength={200} placeholder="Ex.: Estrutura metálica do galpão" required/></label>
    <div className="form-grid" style={{marginBottom: 0, gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 10}}>
      <label>Unidade<input className="input" name="unit" maxLength={30} placeholder="m², m³, t, un" required/></label>
      <label>Quantidade prevista<input className="input" name="planned_quantity" inputMode="decimal" required/></label>
      <label>Peso (%)<input className="input" name="weight" inputMode="decimal" placeholder={"até " + available} required/></label>
    </div>
    <p className="hint">O peso representa a participação do serviço na obra; a soma dos pesos deve chegar a 100%. Disponível: {available}%.</p>
    <div><button className="btn primary" disabled={pending}>Cadastrar serviço</button> <Feedback state={state}/></div>
  </form>;
}

export function MeasurementForm({projectId, services}: {projectId: string; services: ServiceOption[]}) {
  const [state, action, pending] = useActionState(recordMeasurement.bind(null, projectId), initial);
  const today = new Date().toISOString().slice(0, 10);
  return <form action={action} className="form">
    <label>Serviço<select className="select" name="service_id" required>
      {services.map(service => <option key={service.id} value={service.id}>{service.name} — restam {Number(service.remaining_quantity).toLocaleString("pt-BR", {maximumFractionDigits: 3})} {service.unit}</option>)}
    </select></label>
    <div className="form-grid" style={{marginBottom: 0, gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 10}}>
      <label>Quantidade executada<input className="input" name="quantity" inputMode="decimal" required/></label>
      <label>Data da medição<input className="input" type="date" name="measured_on" defaultValue={today} max={today}/></label>
    </div>
    <label>Observações<input className="input" name="notes" maxLength={500} placeholder="Trecho, eixo, pavimento…"/></label>
    <div><button className="btn primary" disabled={pending || !services.length}>Registrar medição</button> <Feedback state={state}/></div>
  </form>;
}

export function DecisionButtons({projectId, measurementId}: {projectId: string; measurementId: string}) {
  const [state, action, pending] = useActionState(decideMeasurement.bind(null, projectId), initial);
  const [rejecting, setRejecting] = useState(false);
  return <form action={action} style={{display: "grid", gap: 6, justifyItems: "end"}}>
    <input type="hidden" name="measurement_id" value={measurementId}/>
    {rejecting && <input className="input" name="reason" placeholder="Motivo da recusa" minLength={5} maxLength={500} required autoFocus/>}
    <div style={{display: "flex", gap: 6}}>
      {!rejecting && <button className="btn primary" name="decision" value="approve" disabled={pending}><Check/>Aprovar</button>}
      {rejecting
        ? <><button className="btn" type="button" onClick={() => setRejecting(false)}>Cancelar</button>
            <button className="btn" name="decision" value="reject" disabled={pending}><X/>Confirmar recusa</button></>
        : <button className="btn" type="button" onClick={() => setRejecting(true)} disabled={pending}><X/>Recusar</button>}
    </div>
    <Feedback state={state}/>
  </form>;
}
