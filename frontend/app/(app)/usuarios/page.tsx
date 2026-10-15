import {Lock} from "lucide-react";
import {PageHead} from "../../../components/app-shell";
import {Callout} from "../../../components/ui";
import {UsersAdmin} from "../../../components/account-forms";
import {apiGet, type Me, type OrgUser} from "../../../lib/api";

export const dynamic = "force-dynamic";

/** Company administrators (Dono / Administrador) manage who has access and with which profile. */
export default async function Users({searchParams}: {searchParams: Promise<{empresa?: string}>}) {
  const [{empresa}, me] = await Promise.all([searchParams, apiGet<Me>("/me")]);
  const managed = (me?.organizations ?? []).filter(o => o.role === "OWNER" || o.role === "ADMIN");
  const org = managed.find(o => o.id === empresa) ?? managed[0];
  const users = org ? await apiGet<OrgUser[]>("/organizations/" + org.id + "/users") : null;
  if (!me || !org || !users) return <><PageHead eyebrow="Administração" title="Usuários"/>
    <Callout icon={Lock}>Somente o dono ou um administrador da empresa gerencia usuários.</Callout></>;
  return <>
    <PageHead eyebrow={"Administração · " + org.name} title="Usuários"
              subtitle="Quem tem acesso ao sistema e com qual perfil. Desativar encerra o acesso na hora; nada é apagado."/>
    <UsersAdmin orgId={org.id} users={users} actorRole={org.role} actorId={me.id}/>
  </>;
}
