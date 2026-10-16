import {Lock, LogIn} from "lucide-react";
import {PageHead} from "../../../components/app-shell";
import {Callout} from "../../../components/ui";
import {Importer} from "../../../components/importer";
import {apiGet, type Me} from "../../../lib/api";

export const dynamic = "force-dynamic";

export default async function Importar() {
  const [me, projects] = await Promise.all([apiGet<Me>("/me"),
    apiGet<{id: string; organization_id: string; name: string}[]>("/projects")]);
  return <>
    <PageHead eyebrow="Alimentar o sistema" title="Importar planilha"
              subtitle="Custos, FOPAG ou medições: envie a planilha e o sistema organiza, classifica e atualiza as previsões."/>
    {me && !projects
      ? <Callout tone="info">Não foi possível carregar as obras autorizadas. Tente novamente; nenhuma importação foi realizada.</Callout>
      : me
      ? <Importer projects={(projects ?? []).map(p => ({id: p.id, organization_id: p.organization_id, name: p.name}))} organizations={me?.organizations ?? []}/>
      : <Callout tone="info" icon={Lock}>Entre para importar planilhas. <a className="link" href="/login"><LogIn size={14}/> Entrar</a></Callout>}
  </>;
}
