const API = process.env.API_BASE_URL || "http://localhost:8000";
type Stage = {name:string;weight:number;progress:number};
type Project = {name:string;location:string;budget:number;physical_progress:number;stages:Stage[]};
async function load():Promise<Project|null> {
  try { const r=await fetch(API+"/api/v1/demo/project",{cache:"no-store"}); return r.ok?await r.json():null; }
  catch { return null; }
}
export default async function Home(){
  const p=await load();
  return <main style={{maxWidth:1050,margin:"auto",padding:32}}>
    <header><small>AGGILLI INTELLIGENCE</small><h1>Gestão de Obras</h1><p>Painel demonstrativo · sem dados reais ou autenticação</p></header>
    {!p?<p>API indisponível. Inicie o backend na porta 8000.</p>:<>
      <section style={{display:"flex",gap:16,flexWrap:"wrap"}}>
        <article style={card}><small>Obra</small><h2>{p.name}</h2><p>{p.location}</p></article>
        <article style={card}><small>Avanço físico</small><h2>{p.physical_progress.toLocaleString("pt-BR")}%</h2></article>
        <article style={card}><small>Orçamento previsto</small><h2>{p.budget.toLocaleString("pt-BR",{style:"currency",currency:"BRL"})}</h2></article>
      </section>
      <h2>Execução por etapa</h2>
      {p.stages.map(s=><article key={s.name} style={{...card,marginBottom:12}}>
        <div style={{display:"flex",justifyContent:"space-between"}}><strong>{s.name}</strong><span>{s.progress}% · peso {s.weight}%</span></div>
        <div style={{height:12,background:"#e2e8f0",borderRadius:10,marginTop:12}}><div style={{width:s.progress+"%",height:"100%",background:"#168b76",borderRadius:10}} /></div>
      </article>)}
    </>}
  </main>;
}
const card:React.CSSProperties={background:"white",borderRadius:16,padding:24,flex:"1 1 200px",boxShadow:"0 2px 12px #10204012"};
