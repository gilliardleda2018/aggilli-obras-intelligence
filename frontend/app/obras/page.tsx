import Link from "next/link";
import { accessToken } from "../../lib/session";
const API=process.env.API_BASE_URL||"http://localhost:8000";
export default async function Obras(){
  const token=await accessToken();
  if(!token)return <main style={{padding:32}}><h1>Obras</h1><a href="/api/auth/login">Entrar com identidade corporativa</a></main>;
  let projects:{id:string;name:string;location:string;budget:string}[]=[];
  let error="";
  try{
    const response=await fetch(API+"/api/v1/projects",{headers:{Authorization:"Bearer "+token},cache:"no-store"});
    if(response.ok)projects=await response.json();
    else error="Não foi possível carregar as obras autorizadas.";
  }catch{error="API indisponível.";}
  return <main style={{padding:32,maxWidth:900,margin:"auto"}}><h1>Obras</h1><a href="/api/auth/logout">Sair</a>
    {error&&<p role="alert">{error}</p>}
    {projects.map(p=><article key={p.id}><h2><Link href={"/obras/"+p.id}>{p.name}</Link></h2><p>{p.location}</p></article>)}
  </main>;
}
