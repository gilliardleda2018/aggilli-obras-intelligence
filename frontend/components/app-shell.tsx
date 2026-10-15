"use client";
import Link from "next/link";
import {usePathname, useRouter} from "next/navigation";
import {useEffect, useState, type ReactNode} from "react";
import {
  BellRing, BrainCircuit, Menu as MenuIcon, X, Camera, CircleHelp, FileText, KeyRound, ShieldCheck, UserCog, Users, Sun, Building2, CalendarClock, Upload, ClipboardList, FileBarChart, HardHat, LayoutDashboard, Map, Package, Scale, Search, Wallet,
} from "lucide-react";
import {SOURCE} from "../lib/portfolio";
import type {LicenseInfo} from "../lib/api";

type Item = {href: string; label: string; icon: typeof LayoutDashboard; soon?: boolean; manager?: boolean};
type Account = {mustChange: boolean; manager: boolean; license: LicenseInfo} | null;
const NAV: {group: string; items: Item[]}[] = [
  {group: "Visão", items: [
    {href: "/simples", label: "Modo simples", icon: Sun},
    {href: "/", label: "Visão geral", icon: LayoutDashboard},
    {href: "/inteligencia", label: "Inteligência", icon: BrainCircuit},
    {href: "/alertas", label: "Alertas", icon: BellRing},
    {href: "/obras", label: "Obras", icon: Building2},
    {href: "/mapa", label: "Mapa", icon: Map},
  ]},
  {group: "Alimentar", items: [
    {href: "/importar", label: "Importar planilha", icon: Upload},
    {href: "/ajuda", label: "Como usar", icon: CircleHelp},
  ]},
  {group: "Financeiro", items: [
    {href: "/fopag", label: "FOPAG semanal", icon: CalendarClock},
    {href: "/financeiro", label: "Contratos e obrigações", icon: Wallet},
    {href: "/conciliacao", label: "Conciliação", icon: Scale},
  ]},
  {group: "Campo", items: [
    {href: "/diario", label: "Diário de obra", icon: Camera},
    {href: "/documentos", label: "Notas e recibos", icon: FileText},
    {href: "/atividades", label: "Atividades", icon: HardHat},
    {href: "/medicoes", label: "Medições", icon: ClipboardList},
    {href: "/materiais", label: "Materiais", icon: Package},
    {href: "/relatorios", label: "Relatórios", icon: FileBarChart},
  ]},
  {group: "Administração", items: [
    {href: "/usuarios", label: "Usuários", icon: Users, manager: true},
    {href: "/licenca", label: "Licença do sistema", icon: ShieldCheck, manager: true},
    {href: "/conta", label: "Minha conta", icon: UserCog},
  ]},
];
const MOBILE = ["/simples", "/", "/obras", "/diario"];  // + "Menu", which opens the full sidebar as a drawer

function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(href + "/");
}

const when = (iso: string | null) => iso ? new Date(iso).toLocaleDateString("pt-BR", {timeZone: "America/Fortaleza"}) : "";

/** License notice, as in MG Transportes: 7 days before the end, during the 5-day grace, and when suspended. */
function LicenseBanner({license, manager}: {license: LicenseInfo; manager: boolean}) {
  if (!license.enforced || license.state === "active") return null;
  const text = license.state === "expiring" ? `A licença do sistema vence em ${when(license.expires_at)}. Renove pelo link de pagamento enviado pela Aggilli.`
    : license.state === "grace" ? `A licença venceu em ${when(license.expires_at)}. O acesso será suspenso em ${when(license.grace_ends)} se não for renovada.`
    : license.state === "blocked" ? "Acesso suspenso: licença do sistema vencida. Nenhum dado foi apagado; ao renovar, tudo volta como estava."
    : "Licença do sistema ainda não ativada.";
  return <div className={"license-banner" + (license.state === "expiring" ? "" : " danger")} role="status">
    <ShieldCheck/><span>{text}</span>{manager && <Link className="link" href="/licenca">Abrir licença</Link>}
  </div>;
}

export function AppShell({children, source, alertsOpen = 0, account = null}:
  {children: ReactNode; source: "api" | "reference"; alertsOpen?: number; account?: Account}) {
  const pathname = usePathname();
  const router = useRouter();
  const [query, setQuery] = useState("");
  const items = NAV.flatMap(group => group.items);
  const mustChange = Boolean(account?.mustChange) && pathname !== "/conta";
  useEffect(() => { if (mustChange) router.replace("/conta?trocar=1"); }, [mustChange, router]);
  const [menu, setMenu] = useState(false);
  useEffect(() => setMenu(false), [pathname]);  // close the phone drawer after navigating
  return <div className="app">
    {menu && <div className="menu-backdrop" onClick={() => setMenu(false)} aria-hidden/>}
    <aside className={"sidebar" + (menu ? " open" : "")} aria-label="Navegação principal" id="menu-principal">
      <button type="button" className="menu-close" onClick={() => setMenu(false)} aria-label="Fechar menu"><X/></button>
      <Link href="/" className="brand brand-logo" aria-label="Aggilli Obras Intelligence — início">
        <img src="/aggilli-intelligence.webp" alt="Aggilli Intelligence" width={1400} height={320}/>
        <small>OBRAS INTELLIGENCE</small></Link>
      {NAV.map(group => <div key={group.group}>
        <div className="nav-group">{group.group}</div>
        {group.items.filter(item => !item.manager || account?.manager).map(item => {
          const Icon = item.icon;
          if (item.soon) {
            return <span key={item.href} className="nav-link" aria-disabled="true" title="Em desenvolvimento">
              <Icon/>{item.label}<span className="soon">em breve</span></span>;
          }
          return <Link key={item.href} href={item.href} onClick={() => setMenu(false)}
                       className={"nav-link" + (isActive(pathname, item.href) ? " active" : "")}>
            <Icon/>{item.label}{item.href === "/alertas" && alertsOpen > 0 && <span className="count">{alertsOpen}</span>}</Link>;
        })}
      </div>)}
      <div className="sidebar-foot"><b>Tuntum · Maranhão</b>{source === "api" ? "Dados do banco, com acesso por empresa e função" : SOURCE.label + " · " + SOURCE.detail}</div>
    </aside>
    <div className="main">
      <header className="topbar">
        <form className="search" role="search" onSubmit={event => {
          event.preventDefault();
          if (query.trim()) router.push("/fopag?q=" + encodeURIComponent(query.trim()));
        }}>
          <Search/>
          <input aria-label="Buscar lançamentos" placeholder="Buscar obra, fornecedor ou serviço…" value={query}
                 onChange={event => setQuery(event.target.value)}/>
          <kbd>Enter</kbd>
        </form>
        <span className="spacer"/>
        {source === "api"
          ? <span className="source-pill live"><i/><span>Banco de dados</span></span>
          : <span className="source-pill" title={SOURCE.detail}><i/><span>Importação de referência</span></span>}
        {source === "api"
          ? <><Link className="btn" href="/conta" title="Minha conta"><KeyRound/></Link><a className="btn" href="/api/auth/logout" title="Sair">Sair</a></>
          : <a className="btn primary" href="/login">Entrar</a>}
      </header>
      <main className="content">{account && <LicenseBanner license={account.license} manager={account.manager}/>}{children}</main>
    </div>
    <nav className="mobile-nav" aria-label="Navegação">
      {MOBILE.map(href => {
        const item = items.find(entry => entry.href === href)!;
        const Icon = item.icon;
        return <Link key={href} href={href} className={isActive(pathname, href) ? "active" : ""}><Icon/>{item.label.split(" ")[0]}</Link>;
      })}
      <button type="button" className={menu ? "active" : ""} onClick={() => setMenu(open => !open)} aria-expanded={menu}
              aria-controls="menu-principal"><MenuIcon/>Menu</button>
    </nav>
  </div>;
}

export function PageHead({eyebrow, title, subtitle, actions}: {eyebrow?: string; title: string; subtitle?: string; actions?: ReactNode}) {
  return <div className="page-head">
    <div>{eyebrow && <div className="eyebrow">{eyebrow}</div>}<h1>{title}</h1>{subtitle && <p>{subtitle}</p>}</div>
    {actions && <div className="actions">{actions}</div>}
  </div>;
}
