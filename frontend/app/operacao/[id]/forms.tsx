"use client";
import {useActionState} from "react";
import {addExpense,schedulePayment,confirmPayment} from "./actions";

type Expense={id:string;description:string;supplier:string;amount:string;status:string};
type Payment={id:string;supplier:string;amount:string;status:string};
const initial={ok:false,message:""};
function Feedback({state,pending}:{state:{ok:boolean;message:string};pending:boolean}){
  return <div aria-live="polite">{pending?"Registrando...":state.message&&<p style={{color:state.ok?"#087c61":"#ac3838"}}>{state.message}</p>}</div>;
}
export function ExpenseForm({id}:{id:string}){
 const [state,action,pending]=useActionState(addExpense.bind(null,id),initial);
 return <form action={action} className="operation-form"><h2>Registrar despesa — Darlan / equipe de campo</h2>
  <label>Fornecedor<input name="supplier" maxLength={200} required/></label>
  <label>Descrição<input name="description" maxLength={300} required/></label>
  <label>Valor (R$)<input name="amount" inputMode="decimal" placeholder="935.00" required/></label>
  <label>Categoria<select name="category"><option value="MATERIAL">Material</option><option value="LABOR">Mão de obra</option><option value="SERVICE">Serviço</option><option value="FUEL">Combustível</option><option value="EQUIPMENT">Equipamento</option><option value="OTHER">Outros</option></select></label>
  <label>Referência do comprovante (opcional)<input name="evidence_key" placeholder="Identificador de documento já armazenado" maxLength={500}/></label>
  <p>O envio de arquivos ainda não está habilitado. Não informe URLs públicas ou dados bancários.</p>
  <button disabled={pending}>Registrar despesa</button><Feedback state={state} pending={pending}/></form>;
}
export function PaymentForms({id,expenses,payments}:{id:string;expenses:Expense[];payments:Payment[]}){
 const [scheduleState,schedule,scheduling]=useActionState(schedulePayment.bind(null,id),initial);
 const [confirmState,confirm,confirming]=useActionState(confirmPayment.bind(null,id),initial);
 return <div className="operation-grid"><form action={schedule} className="operation-form"><h2>Programar pagamento — Denise / financeiro</h2>
  <label>Despesa<select name="expense_id" required>{expenses.map(e=><option key={e.id} value={e.id}>{e.supplier} — {e.description} — R$ {e.amount}</option>)}</select></label>
  <label>Valor (R$)<input name="amount" inputMode="decimal" required/></label>
  <label>Data programada<input type="date" name="scheduled_date" required/></label>
  <button disabled={scheduling||!expenses.length}>Programar pagamento</button><Feedback state={scheduleState} pending={scheduling}/></form>
  <form action={confirm} className="operation-form"><h2>Confirmar pagamento realizado</h2>
  <label>Pagamento programado<select name="payment_id" required>{payments.filter(p=>p.status==="SCHEDULED").map(p=><option key={p.id} value={p.id}>{p.supplier} — R$ {p.amount}</option>)}</select></label>
  <label>Referência bancária/comprovante<input name="reference" minLength={3} maxLength={200} required/></label>
  <button disabled={confirming||!payments.some(p=>p.status==="SCHEDULED")}>Confirmar quitação</button><Feedback state={confirmState} pending={confirming}/></form></div>;
}
