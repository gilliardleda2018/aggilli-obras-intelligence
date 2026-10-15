import {BarChart3, Building2, MapPinned, ShieldCheck} from "lucide-react";
import {LoginFlow} from "./login-flow";

export const dynamic = "force-dynamic";

export default function LoginPage() {
  const projectId = process.env.NEXT_PUBLIC_DESCOPE_PROJECT_ID;
  return <main className="auth">
    <section className="auth-art">
      <span/>
      <div className="auth-hero">
        <img className="auth-logo" src="/aggilli-intelligence.webp" alt="Aggilli Intelligence" width={1400} height={320}/>
        <div className="auth-product">Obras Intelligence</div>
        <h2>Suas obras, do canteiro ao caixa, em uma só tela.</h2>
        <ul>
          <li><Building2/>Carteira de obras com contratos e programação semanal</li>
          <li><BarChart3/>Avanço físico por medições aprovadas</li>
          <li><MapPinned/>Mapa das obras e fotos georreferenciadas</li>
          <li><ShieldCheck/>Acesso por empresa e função, com trilha de auditoria</li>
        </ul>
      </div>
      <small style={{color: "#8fc3cc"}}>© Aggilli Intelligence</small>
    </section>
    <section className="auth-panel">
      <div className="auth-box">
        <img className="auth-logo-mobile" src="/aggilli-intelligence.webp" alt="Aggilli Intelligence" width={1400} height={320}/>
        <h1>Entrar</h1>
        <p>Use sua identidade corporativa. O acesso às obras depende da autorização da sua empresa.</p>
        {process.env.ALLOW_DEV_LOGIN === "1" && <a className="btn primary" href="/api/auth/dev">Entrar como usuário de desenvolvimento</a>}
        {projectId ? <LoginFlow projectId={projectId}/>
          : <div className="callout"><span>Login indisponível: projeto de identidade não configurado neste ambiente.</span></div>}
      </div>
    </section>
  </main>;
}
