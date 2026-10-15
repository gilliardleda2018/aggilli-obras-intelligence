import Link from "next/link";
import {ArrowLeft, Lock} from "lucide-react";
import {PageHead} from "../../../../components/app-shell";
import {Badge, Callout, Card} from "../../../../components/ui";
import {accessToken} from "../../../../lib/session";
import {money} from "../../../../lib/portfolio";
import {ExpenseForm, PaymentForms} from "./forms";

const API = process.env.API_BASE_URL || "http://localhost:8000";
type Expense = {id: string; description: string; supplier: string; amount: string; status: string};
type Payment = {id: string; supplier: string; amount: string; status: string};

async function getData<T>(path: string, token: string): Promise<T | null> {
  try {
    const response = await fetch(API + path, {headers: {Authorization: "Bearer " + token}, cache: "no-store"});
    return response.ok ? await response.json() : null;
  } catch {
    return null;
  }
}

const STATUS: Record<string, {label: string; tone: "ok" | "warn" | "info" | "neutral"}> = {
  OPEN: {label: "Em aberto", tone: "warn"}, PAID: {label: "Paga", tone: "ok"}, SCHEDULED: {label: "Programado", tone: "info"},
};

export default async function Operation({params}: {params: Promise<{id: string}>}) {
  const {id} = await params;
  const token = await accessToken();
  const back = <Link href={"/obras/" + id} className="back"><ArrowLeft/>Obra</Link>;
  if (!token) return <>{back}<Callout tone="info" icon={Lock}>Autenticação necessária. <Link className="link" href="/login">Entrar</Link></Callout></>;
  const prefix = "/api/v1/projects/" + encodeURIComponent(id);
  const [expenses, payments] = await Promise.all([getData<Expense[]>(prefix + "/expenses", token), getData<Payment[]>(prefix + "/payments", token)]);
  if (!expenses || !payments) return <>{back}<Callout icon={Lock}>Acesso indisponível. Verifique suas permissões e a conexão com a API.</Callout></>;
  return <>
    {back}
    <PageHead eyebrow="Operação financeira" title="Despesas e pagamentos"
              subtitle="Darlan registra as despesas; Denise programa e confirma os pagamentos com comprovante."/>
    <div className="form-grid"><ExpenseForm id={id}/><PaymentForms id={id} expenses={expenses} payments={payments}/></div>
    <Card flush title="Despesas registradas" subtitle={expenses.length + " despesas"}>
      <div className="table-wrap"><table>
        <thead><tr><th>Fornecedor</th><th>Descrição</th><th className="num">Valor</th><th>Situação</th></tr></thead>
        <tbody>
          {expenses.map(expense => <tr key={expense.id}>
            <td><b>{expense.supplier}</b></td><td>{expense.description}</td><td className="num">{money(Number(expense.amount))}</td>
            <td><Badge tone={STATUS[expense.status]?.tone ?? "neutral"}>{STATUS[expense.status]?.label ?? expense.status}</Badge></td>
          </tr>)}
          {!expenses.length && <tr><td colSpan={4} className="empty">Nenhuma despesa registrada.</td></tr>}
        </tbody>
      </table></div>
    </Card>
  </>;
}
