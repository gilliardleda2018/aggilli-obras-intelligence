"use client";
import {useRouter} from "next/navigation";
import {useState} from "react";
import {KeyRound, Loader2, LogIn, ShieldCheck, UserPlus} from "lucide-react";
import type {LicenseStatus, OrgUser} from "../lib/api";
import {activateLicense, addUser, changePassword, changeUser, resetPassword} from "../lib/account-actions";

export const ROLE_LABEL: Record<string, string> = {OWNER: "Dono", ADMIN: "Administrador", ENGINEER: "Engenheiro",
  INSPECTOR: "Fiscal", FIELD_OPERATOR: "Campo", VIEWER: "Consulta"};

/** E-mail + password sign-in, with "Manter conectado" (30 days) as in MG Transportes. */
export function PasswordLogin() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function submit(form: FormData) {
    setBusy(true); setError(null);
    const response = await fetch("/api/auth/password", {method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({email: form.get("email"), password: form.get("password"), remember: form.get("remember") === "on"})});
    const body = await response.json().catch(() => ({}));
    setBusy(false);
    if (!response.ok) return setError(body.message ?? "Não foi possível entrar.");
    router.replace(body.mustChange ? "/conta?trocar=1" : "/");
    router.refresh();
  }
  return <form className="form login-form" action={submit}>
    <label>E-mail<input className="input" name="email" type="email" autoComplete="username" required/></label>
    <label>Senha<input className="input" name="password" type="password" autoComplete="current-password" required/></label>
    <label className="check"><input type="checkbox" name="remember"/> Manter conectado neste aparelho</label>
    {error && <p className="form-error" role="alert">{error}</p>}
    <button className="btn primary big" disabled={busy}>{busy ? <Loader2 className="spin"/> : <LogIn/>}Entrar</button>
  </form>;
}

export function PasswordForm({forced}: {forced: boolean}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ok: boolean; text: string} | null>(null);
  async function submit(form: FormData) {
    const next = String(form.get("next") ?? "");
    if (next !== form.get("confirm")) return setMessage({ok: false, text: "A confirmação não confere com a nova senha."});
    setBusy(true);
    const result = await changePassword(String(form.get("current") ?? ""), next);
    setBusy(false);
    if (!result.ok) return setMessage({ok: false, text: result.message});
    setMessage({ok: true, text: "Senha alterada. As outras sessões abertas foram encerradas."});
    if (forced) { router.replace("/"); router.refresh(); }
  }
  return <form className="form" action={submit}>
    <label>{forced ? "Senha temporária" : "Senha atual"}<input className="input" name="current" type="password" autoComplete="current-password" required/></label>
    <label>Nova senha<input className="input" name="next" type="password" autoComplete="new-password" required minLength={10}/>
      <span className="hint">Pelo menos 10 caracteres, com letras e números.</span></label>
    <label>Confirme a nova senha<input className="input" name="confirm" type="password" autoComplete="new-password" required/></label>
    {message && <p className={message.ok ? "diary-done" : "form-error"} role="status">{message.text}</p>}
    <button className="btn primary" disabled={busy}>{busy ? <Loader2 className="spin"/> : <KeyRound/>}Trocar senha</button>
  </form>;
}

function TempPassword({user, onClose}: {user: OrgUser; onClose: () => void}) {
  return <div className="note-box" role="status">
    <b>Senha temporária de {user.name}:</b> <code className="temp-pass">{user.temporary_password}</code>
    <p>Passe para a pessoa por um canal seguro. Ela vai criar a própria senha no primeiro acesso. Esta senha não aparece de novo.</p>
    <button type="button" className="btn" onClick={onClose}>Entendi</button>
  </div>;
}

export function UsersAdmin({orgId, users, actorRole, actorId}: {orgId: string; users: OrgUser[]; actorRole: string; actorId: string}) {
  const [shown, setShown] = useState<OrgUser | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const roles = Object.keys(ROLE_LABEL).filter(r => r !== "OWNER" || actorRole === "OWNER");

  async function add(form: FormData) {
    setBusy(true); setError(null);
    const result = await addUser(orgId, {email: String(form.get("email") ?? ""), name: String(form.get("name") ?? ""),
      role: String(form.get("role") ?? "VIEWER")});
    setBusy(false);
    if (!result.ok) return setError(result.message);
    if (result.data.temporary_password) setShown(result.data);
  }
  async function act(run: () => Promise<{ok: boolean; message?: string; data?: OrgUser}>) {
    setError(null);
    const result = await run();
    if (!result.ok) setError(result.message ?? "Erro");
    else if (result.data?.temporary_password) setShown(result.data);
  }

  return <div className="stack">
    {shown && <TempPassword user={shown} onClose={() => setShown(null)}/>}
    {error && <p className="form-error" role="alert">{error}</p>}
    <section className="card"><div className="card-head"><div><h2>Novo usuário</h2>
      <p>O sistema gera uma senha temporária; a pessoa troca no primeiro acesso.</p></div></div>
      <div className="card-body"><form className="form user-form" action={add}>
        <label>Nome<input className="input" name="name" required minLength={2} maxLength={120}/></label>
        <label>E-mail<input className="input" name="email" type="email" required/></label>
        <label>Perfil<select className="select" name="role" defaultValue="FIELD_OPERATOR">
          {roles.map(r => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}</select></label>
        <button className="btn primary" disabled={busy}>{busy ? <Loader2 className="spin"/> : <UserPlus/>}Adicionar</button>
      </form></div></section>

    <section className="card"><div className="card-head"><div><h2>Usuários ({users.length})</h2></div></div>
      <div className="table-wrap"><table><thead><tr><th>Nome</th><th>Perfil</th><th>Situação</th><th>Último acesso</th><th/></tr></thead>
        <tbody>{users.map(u => {
          const locked = u.role === "OWNER" && actorRole !== "OWNER";
          return <tr key={u.membership_id}>
            <td><b>{u.name}</b><br/><small>{u.email ?? "identidade externa"}</small></td>
            <td><select className="select" value={u.role} disabled={locked}
                        onChange={e => act(() => changeUser(orgId, u.user_id, {role: e.target.value}))}>
              {Object.keys(ROLE_LABEL).filter(r => r !== "OWNER" || actorRole === "OWNER" || u.role === "OWNER")
                .map(r => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}</select></td>
            <td>{!u.active ? "Desativado" : u.locked ? "Bloqueado (tentativas)" : u.must_change_password ? "Aguardando 1º acesso" : "Ativo"}</td>
            <td>{u.last_login_at ? new Date(u.last_login_at).toLocaleString("pt-BR", {timeZone: "America/Fortaleza"}) : "—"}</td>
            <td className="user-actions">{u.local && !locked && <>
              <button type="button" className="btn" onClick={() => act(() => resetPassword(orgId, u.user_id))}>Nova senha</button>
              {u.user_id !== actorId && <button type="button" className="btn"
                onClick={() => act(() => changeUser(orgId, u.user_id, {active: !u.active}))}>{u.active ? "Desativar" : "Reativar"}</button>}
            </>}</td>
          </tr>;
        })}</tbody></table></div></section>
  </div>;
}

export function LicenseActivate() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ok: boolean; text: string} | null>(null);
  async function submit(form: FormData) {
    setBusy(true); setMessage(null);
    const result = await activateLicense(String(form.get("code") ?? ""));
    setBusy(false);
    if (!result.ok) return setMessage({ok: false, text: result.message});
    setMessage({ok: true, text: "Licença ativada."});
    router.refresh();
  }
  return <form className="form" action={submit}>
    <label>Código de ativação<textarea className="input" name="code" rows={3} required
      placeholder="Cole aqui o código recebido por e-mail depois do pagamento"/></label>
    {message && <p className={message.ok ? "diary-done" : "form-error"} role="status">{message.text}</p>}
    <button className="btn primary" disabled={busy}>{busy ? <Loader2 className="spin"/> : <ShieldCheck/>}Ativar licença</button>
  </form>;
}

export type {LicenseStatus};
