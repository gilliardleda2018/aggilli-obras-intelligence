import Link from "next/link";
import {accessToken} from "../../../lib/session";
import {ExpenseForm,PaymentForms} from "./forms";
const API=process.env.API_BASE_URL||"http://localhost:8000";
type Expense={id:string;description:string;supplier:string;amount:string;status:string};
type Payment={id:string;supplier:string;amount:string;status:string};
async function getData<T>(path:string,token:string):Promise<T|null>{
 try{const r=await fetch(API+path,{headers:{Authorization:"Bearer "+token},cache:"no-store"});return r.ok?await r.json():null;}catch{return null;}
}
export default async function Operation({params}:{params:Promise<{id:string}>}){
 const {id}=await params;
 const token=await accessToken();
 if(!token)return <main className="operation-page"><h1>Autenticação necessária</h1><Link href="/login">Entrar</Link></main>;
 const prefix="/api/v1/projects/"+encodeURIComponent(id);
 const [expenses,payments]=await Promise.all([
  getData<Expense[]>(prefix+"/expenses",token),getData<Payment[]>(prefix+"/payments",token)]);
 if(!expenses||!payments)return <main className="operation-page"><h1>Acesso indisponível</h1><p>Verifique suas permissões e a conexão com a API.</p></main>;
 return <main className="operation-page"><Link href="/obras">← Obras</Link><h1>Operação financeira da obra</h1>
 <p>Dados persistidos na API. Ações sujeitas à autorização por empresa e função.</p>
 <div className="operation-grid"><ExpenseForm id={id}/><PaymentForms id={id} expenses={expenses} payments={payments}/></div>
 <section className="panel"><h2>Despesas registradas</h2><table><thead><tr><th>Fornecedor</th><th>Descrição</th><th>Valor</th><th>Estado</th></tr></thead><tbody>{expenses.map(e=><tr key={e.id}><td>{e.supplier}</td><td>{e.description}</td><td>{e.amount}</td><td>{e.status}</td></tr>)}</tbody></table></section>
 </main>;
}
