import {Lock, ShieldCheck, ShieldAlert} from "lucide-react";
import {PageHead} from "../../../components/app-shell";
import {Badge, Callout, Card} from "../../../components/ui";
import {LicenseActivate} from "../../../components/account-forms";
import {apiGet, type LicenseStatus} from "../../../lib/api";

export const dynamic = "force-dynamic";
const STATE: Record<string, [string, "ok" | "warn" | "danger" | "neutral"]> = {
  active: ["Ativa", "ok"], expiring: ["Vence em breve", "warn"], grace: ["Vencida — em tolerância", "danger"],
  blocked: ["Suspensa", "danger"], missing: ["Não ativada", "neutral"],
};
const when = (iso: string | null) => iso ? new Date(iso).toLocaleString("pt-BR", {timeZone: "America/Fortaleza", dateStyle: "short", timeStyle: "short"}) : "—";

export default async function License() {
  const lic = await apiGet<LicenseStatus>("/license");
  if (!lic) return <><PageHead eyebrow="Administração" title="Licença do sistema"/><Callout icon={Lock}>Entre no sistema para ver a licença.</Callout></>;
  const [label, tone] = STATE[lic.state] ?? STATE.missing;
  return <>
    <PageHead eyebrow="Administração" title="Licença do sistema"
              subtitle="Licença de 30 dias. Renove pelo link de pagamento enviado pela Aggilli; a nova licença soma mais 30 dias."/>
    <div className="diary-grid">
      <Card title="Situação">
        <p><Badge tone={tone}>{label}</Badge></p>
        <p>Válida até <b>{when(lic.expires_at)}</b>{lic.days_left !== null && lic.days_left >= 0 ? ` (${lic.days_left} dias)` : ""}.</p>
        {lic.state === "grace" && <p>O acesso será suspenso em {when(lic.grace_ends)} se a licença não for renovada. Nenhum dado é apagado.</p>}
        {lic.holder && <p>Titular: {lic.holder}</p>}
        {!lic.enforced && <p className="hint">Controle de licença ainda não ligado neste ambiente.</p>}
        {lic.last_error && <Callout icon={ShieldAlert}>Última verificação: {lic.last_error}</Callout>}
      </Card>
      <Card title="Ativar ou atualizar">
        {lic.can_manage ? <LicenseActivate/> : <p><ShieldCheck size={16}/> Somente administradores ativam ou atualizam a licença.</p>}
      </Card>
    </div>
  </>;
}
