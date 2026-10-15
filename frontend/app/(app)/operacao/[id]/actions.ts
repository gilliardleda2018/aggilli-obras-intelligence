"use server";
import {revalidatePath} from "next/cache";
import {accessToken} from "../../../../lib/session";

const API=process.env.API_BASE_URL||"http://localhost:8000";
type State={message:string;ok:boolean};
async function send(path:string,body:unknown):Promise<State>{
  const token=await accessToken();
  if(!token)return {ok:false,message:"Sessão expirada. Entre novamente."};
  try{
    const res=await fetch(API+path,{method:"POST",headers:{
      Authorization:"Bearer "+token,"Content-Type":"application/json"},body:JSON.stringify(body),cache:"no-store"});
    if(!res.ok)return {ok:false,message:res.status===403||res.status===404?"Acesso negado ou recurso não encontrado.":res.status===409?"Conflito: confira o saldo ou o estado atual.":"Não foi possível concluir a operação ("+res.status+")."};
    return {ok:true,message:"Operação registrada com sucesso."};
  }catch{return {ok:false,message:"Não foi possível conectar à API."};}
}
function positiveAmount(v:FormDataEntryValue|null){
  const raw=String(v||"").trim().replace(",",".");
  const amount=Number(raw);
  if(!Number.isFinite(amount)||amount<=0||!/^\d+(\.\d{1,2})?$/.test(raw))return null;
  return amount.toFixed(2);
}
export async function addExpense(projectId:string,_prev:State,form:FormData):Promise<State>{
  const amount=positiveAmount(form.get("amount"));
  const description=String(form.get("description")||"").trim();
  const supplier=String(form.get("supplier")||"").trim();
  const category=String(form.get("category")||"");
  const evidence=String(form.get("evidence_key")||"").trim();
  if(!amount||!description||!supplier||!["MATERIAL","LABOR","FUEL","EQUIPMENT","SERVICE","OTHER"].includes(category))
    return {ok:false,message:"Preencha os campos obrigatórios corretamente."};
  const result=await send("/api/v1/projects/"+encodeURIComponent(projectId)+"/expenses",
    {amount,description,supplier,category,evidence_key:evidence||null});
  if(result.ok)revalidatePath("/operacao/"+projectId);
  return result;
}
export async function schedulePayment(projectId:string,_prev:State,form:FormData):Promise<State>{
  const expenseId=String(form.get("expense_id")||"");
  const amount=positiveAmount(form.get("amount"));
  const scheduled_date=String(form.get("scheduled_date")||"");
  if(!/^[a-f0-9-]{36}$/i.test(expenseId)||!amount||!/^\d{4}-\d{2}-\d{2}$/.test(scheduled_date))
    return {ok:false,message:"Despesa, valor ou data inválidos."};
  const result=await send("/api/v1/expenses/"+expenseId+"/payments",{amount,scheduled_date});
  if(result.ok)revalidatePath("/operacao/"+projectId);
  return result;
}
export async function confirmPayment(projectId:string,_prev:State,form:FormData):Promise<State>{
  const id=String(form.get("payment_id")||"");
  const reference=String(form.get("reference")||"").trim();
  if(!/^[a-f0-9-]{36}$/i.test(id)||reference.length<3)
    return {ok:false,message:"Selecione o pagamento e informe a referência do comprovante."};
  const result=await send("/api/v1/payments/"+id+"/confirm",{reference});
  if(result.ok)revalidatePath("/operacao/"+projectId);
  return result;
}
