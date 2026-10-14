import Link from "next/link";
const API = process.env.API_BASE_URL || "http://localhost:8000";
export default async function Obras(){
  // Auth is intentionally server-side. No client-supplied subject or organization headers.
  const token = process.env.DASHBOARD_SERVICE_TOKEN;
  if (!token) return <main style={{padding:32}}><h1>Obras</h1><p>Autenticação do dashboard ainda não configurada.</p><Link href="/">Voltar</Link></main>;
  let projects: {id:string;name:string;location:string;budget:string}[] = [];
  try {
    const response=await fetch(API+"/api/v1/projects",{headers:{Authorization:"Bearer "+token},cache:"no-store"});
    if(response.ok) projects=await response.json();
  } catch {}
  return <main style={{padding:32}}><h1>Obras cadastradas</h1>{projects.map(p=><article key={p.id}>
    <h2><Link href={"/obras/"+p.id}>{p.name}</Link></h2><p>{p.location} · R$ {p.budget}</p>
  </article>)}</main>;
}
