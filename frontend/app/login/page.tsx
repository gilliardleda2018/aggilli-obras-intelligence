import { LoginFlow } from "./login-flow";

export default function LoginPage() {
  const projectId = process.env.NEXT_PUBLIC_DESCOPE_PROJECT_ID;
  if (!projectId) return <main style={{padding:32}}><h1>Login indisponível</h1><p>Projeto Descope não configurado.</p></main>;
  return <main style={{maxWidth:520,margin:"64px auto",padding:24}}>
    <h1>Aggilli Obras Intelligence</h1>
    <p>Autenticação de homologação — acesso às obras depende de autorização adicional.</p>
    <LoginFlow projectId={projectId}/>
  </main>;
}
