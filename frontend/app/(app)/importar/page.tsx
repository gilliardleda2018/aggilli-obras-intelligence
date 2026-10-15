import {Lock, LogIn} from "lucide-react";
import {PageHead} from "../../../components/app-shell";
import {Callout} from "../../../components/ui";
import {Importer} from "../../../components/importer";
import {getDataset} from "../../../lib/data";

export const dynamic = "force-dynamic";

export default async function Importar() {
  const data = await getDataset();
  return <>
    <PageHead eyebrow="Alimentar o sistema" title="Importar planilha"
              subtitle="Custos, FOPAG ou medições: envie a planilha e o sistema organiza, classifica e atualiza as previsões."/>
    {data.source === "api"
      ? <Importer projects={data.projects.map(p => ({id: p.key, name: p.name}))}/>
      : <Callout tone="info" icon={Lock}>Entre para importar planilhas. <a className="link" href="/login"><LogIn size={14}/> Entrar</a></Callout>}
  </>;
}
