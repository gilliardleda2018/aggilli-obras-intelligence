import {Lock} from "lucide-react";
import {PageHead} from "../../../components/app-shell";
import {Callout, Card} from "../../../components/ui";
import {PasswordForm, ROLE_LABEL} from "../../../components/account-forms";
import {apiGet, type Me} from "../../../lib/api";

export const dynamic = "force-dynamic";

export default async function Account() {
  const me = await apiGet<Me>("/me");
  if (!me) return <><PageHead eyebrow="Conta" title="Minha conta"/><Callout icon={Lock}>Entre no sistema para ver sua conta.</Callout></>;
  return <>
    <PageHead eyebrow="Conta" title="Minha conta" subtitle={me.email ?? me.name}/>
    <div className="diary-grid">
      <Card title={me.must_change_password ? "Crie sua senha" : "Trocar senha"}
            subtitle={me.must_change_password ? "Você entrou com uma senha temporária. Crie a sua para continuar." : undefined}>
        {me.local ? <PasswordForm forced={me.must_change_password}/> : <p>Sua conta entra pela identidade corporativa; a senha é trocada lá.</p>}
      </Card>
      <Card title="Empresas e perfis">
        <ul className="help-steps">{me.organizations.map(o => <li key={o.id}><b>{o.name}</b> — {ROLE_LABEL[o.role] ?? o.role}</li>)}</ul>
      </Card>
    </div>
  </>;
}
