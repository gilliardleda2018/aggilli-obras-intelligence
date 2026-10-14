import Link from "next/link";
export default async function Detail({params}:{params:Promise<{id:string}>}){
  await params;
  return <main style={{padding:32,maxWidth:850,margin:"auto"}}>
    <Link href="/obras">← Obras</Link>
    <h1>Detalhes da obra</h1>
    <p>A visualização de dados reais exige autenticação OIDC individual e sessão validada no servidor.</p>
    <p>Esta rota permanece bloqueada até a integração de identidade.</p>
  </main>;
}
