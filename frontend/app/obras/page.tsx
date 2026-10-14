import Link from "next/link";
export default function Obras(){
  return <main style={{padding:32,maxWidth:850,margin:"auto"}}>
    <h1>Obras cadastradas</h1>
    <p>O acesso a obras reais requer login OIDC por usuário. A interface de sessão está em implementação.</p>
    <p>Por segurança, nenhum token de serviço compartilhado é utilizado para representar usuários.</p>
    <Link href="/">Voltar ao painel demonstrativo</Link>
  </main>;
}
