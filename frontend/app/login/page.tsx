import {BarChart3, Building2, MapPinned, ShieldCheck} from "lucide-react";
import {LoginFlow} from "./login-flow";
import {PasswordLogin} from "../../components/account-forms";

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
        <img className="auth-product-logo" src="/emobras-logo.webp" alt="emobras — planeja, acompanha, evolui"
             width={900} height={580}/>
        <h1>Entrar</h1>
        <p>Entre com o e-mail e a senha cadastrados pelo administrador da sua empresa.</p>
        <PasswordLogin/>
        {process.env.ALLOW_DEV_LOGIN === "1" && <a className="btn" href="/api/auth/dev">Entrar como usuário de desenvolvimento</a>}
        {projectId && process.env.OIDC_CLIENT_ID && <details className="auth-alt"><summary>Entrar com identidade corporativa</summary>
          <LoginFlow projectId={projectId}/></details>}
      </div>
    </section>
  </main>;
}
