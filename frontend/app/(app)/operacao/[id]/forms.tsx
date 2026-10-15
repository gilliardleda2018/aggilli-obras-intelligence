"use client";
import {useActionState} from "react";
import {addExpense, schedulePayment, confirmPayment} from "./actions";

type Expense = {id: string; description: string; supplier: string; amount: string; status: string};
type Payment = {id: string; supplier: string; amount: string; status: string};
const initial = {ok: false, message: ""};

function Feedback({state, pending}: {state: {ok: boolean; message: string}; pending: boolean}) {
  return <div aria-live="polite" className={"feedback " + (state.ok ? "ok" : "err")}>
    {pending ? "Registrando…" : state.message}
  </div>;
}

export function ExpenseForm({id}: {id: string}) {
  const [state, action, pending] = useActionState(addExpense.bind(null, id), initial);
  return <form action={action} className="card card-body form" style={{paddingTop: 18}}>
    <div><h2 style={{fontSize: 15}}>Registrar despesa</h2><p className="hint">Darlan / equipe de campo</p></div>
    <label>Fornecedor<input className="input" name="supplier" maxLength={200} required/></label>
    <label>Descrição<input className="input" name="description" maxLength={300} required/></label>
    <label>Valor (R$)<input className="input" name="amount" inputMode="decimal" placeholder="935.00" required/></label>
    <label>Categoria<select className="select" name="category">
      <option value="MATERIAL">Material</option><option value="LABOR">Mão de obra</option><option value="SERVICE">Serviço</option>
      <option value="FUEL">Combustível</option><option value="EQUIPMENT">Equipamento</option><option value="OTHER">Outros</option>
    </select></label>
    <label>Referência do comprovante (opcional)
      <input className="input" name="evidence_key" placeholder="Identificador de documento já armazenado" maxLength={500}/>
      <span className="hint">O envio de arquivos ainda não está habilitado. Não informe URLs públicas ou dados bancários.</span></label>
    <button className="btn primary" disabled={pending}>Registrar despesa</button>
    <Feedback state={state} pending={pending}/>
  </form>;
}

export function PaymentForms({id, expenses, payments}: {id: string; expenses: Expense[]; payments: Payment[]}) {
  const [scheduleState, schedule, scheduling] = useActionState(schedulePayment.bind(null, id), initial);
  const [confirmState, confirm, confirming] = useActionState(confirmPayment.bind(null, id), initial);
  const scheduled = payments.filter(payment => payment.status === "SCHEDULED");
  return <div className="stack">
    <form action={schedule} className="card card-body form" style={{paddingTop: 18}}>
      <div><h2 style={{fontSize: 15}}>Programar pagamento</h2><p className="hint">Denise / financeiro</p></div>
      <label>Despesa<select className="select" name="expense_id" required>
        {expenses.map(expense => <option key={expense.id} value={expense.id}>
          {expense.supplier} — {expense.description} — R$ {expense.amount}</option>)}
      </select></label>
      <label>Valor (R$)<input className="input" name="amount" inputMode="decimal" required/></label>
      <label>Data programada<input className="input" type="date" name="scheduled_date" required/></label>
      <button className="btn primary" disabled={scheduling || !expenses.length}>Programar pagamento</button>
      <Feedback state={scheduleState} pending={scheduling}/>
    </form>
    <form action={confirm} className="card card-body form" style={{paddingTop: 18}}>
      <div><h2 style={{fontSize: 15}}>Confirmar pagamento realizado</h2><p className="hint">Somente com comprovante</p></div>
      <label>Pagamento programado<select className="select" name="payment_id" required>
        {scheduled.map(payment => <option key={payment.id} value={payment.id}>{payment.supplier} — R$ {payment.amount}</option>)}
      </select></label>
      <label>Referência bancária / comprovante<input className="input" name="reference" minLength={3} maxLength={200} required/></label>
      <button className="btn primary" disabled={confirming || !scheduled.length}>Confirmar quitação</button>
      <Feedback state={confirmState} pending={confirming}/>
    </form>
  </div>;
}
