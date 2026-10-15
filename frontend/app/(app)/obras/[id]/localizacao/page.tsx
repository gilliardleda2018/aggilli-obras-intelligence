import Link from "next/link";
import {ArrowLeft, Lock} from "lucide-react";
import {PageHead} from "../../../../../components/app-shell";
import {LocationEditor} from "../../../../../components/location-editor";
import {Callout} from "../../../../../components/ui";
import {apiGet, type GeoLocation} from "../../../../../lib/api";

export const dynamic = "force-dynamic";

export default async function Localizacao({params}: {params: Promise<{id: string}>}) {
  const {id} = await params;
  const back = <Link href={"/obras/" + id} className="back"><ArrowLeft/>Obra</Link>;
  const data = await apiGet<{name: string; address: string | null; municipality: string | null; location: GeoLocation; can_edit: boolean}>(
    "/projects/" + encodeURIComponent(id) + "/location");
  if (!data) return <>{back}<Callout icon={Lock}>Obra indisponível, sem sessão ou sem autorização.</Callout></>;
  return <>
    {back}
    <PageHead eyebrow={"Localização" + (data.municipality ? " · " + data.municipality : "")} title={data.name}
              subtitle="Defina o ponto da obra pelo endereço, marcando no mapa, com o GPS no local ou por coordenadas conferidas. Nada é salvo sem a sua confirmação."/>
    <LocationEditor projectId={id} address={data.address} location={data.location} canEdit={data.can_edit}
                    apiKey={process.env.GOOGLE_MAPS_BROWSER_KEY ?? ""} mapId={process.env.GOOGLE_MAPS_MAP_ID || "DEMO_MAP_ID"}/>
  </>;
}
