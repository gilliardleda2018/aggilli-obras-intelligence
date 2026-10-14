import Link from "next/link";
const API=process.env.API_BASE_URL||"http://localhost:8000";
type Data={name:string;location:string;budget:string;physical_progress:number;planning_complete:boolean;stages:{name:string;progress:number;approved_quantity:string;planned_quantity:string;unit:string}[]};
export default async function Detail({params}:{params:Promise<{id:string}>}){
  const {id}=await params;
  const token=process.env.DASHBOARD_SERVICE_TOKEN;
  let data:Data|null=null;
  if(token) try{
    const response=await fetch(API+"/api/v1/projects/"+encodeURIComponent(id)+"/dashboard",
      {headers:{Authorization:"Bearer "+token},cache:"no-store"});
    if(response.ok) data=await response.json();
  }catch{}
  return <main style={{padding:32,maxWidth:1000,margin:"auto"}}><Link href="/obras">← Obras</Link>
    {!data?<p>Obra indisponível ou acesso não autorizado.</p>:<>
      <h1>{data.name}</h1><p>{data.location}</p><h2>Avanço físico: {data.physical_progress}%</h2>
      {!data.planning_complete&&<p>Planejamento incompleto: pesos dos serviços não somam 100%.</p>}
      <p>Orçamento previsto: {Number(data.budget).toLocaleString("pt-BR",{style:"currency",currency:"BRL"})}</p>
      {data.stages.map(s=><section key={s.name} style={{padding:16,background:"white",marginBottom:12,borderRadius:12}}>
        <strong>{s.name}</strong><p>{s.approved_quantity} / {s.planned_quantity} {s.unit} · {s.progress}%</p>
        <div style={{background:"#ddd",height:10}}><div style={{background:"#168b76",width:s.progress+"%",height:10}}/></div>
      </section>)}
    </>}
  </main>;
}
