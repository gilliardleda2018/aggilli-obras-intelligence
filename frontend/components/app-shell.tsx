"use client";
import Link from "next/link";
import {usePathname, useRouter} from "next/navigation";
import {useState, type ReactNode} from "react";
import {
  BellRing, BrainCircuit, Building2, CalendarClock, Upload, ClipboardList, FileBarChart, HardHat, LayoutDashboard, Map, Package, Scale, Search, Wallet,
} from "lucide-react";
import {SOURCE} from "../lib/portfolio";

type Item = {href: string; label: string; icon: typeof LayoutDashboard; soon?: boolean};
const NAV: {group: string; items: Item[]}[] = [
  {group: "Visão", items: [
    {href: "/", label: "Visão geral", icon: LayoutDashboard},
    {href: "/inteligencia", label: "Inteligência", icon: BrainCircuit},
    {href: "/alertas", label: "Alertas", icon: BellRing},
    {href: "/obras", label: "Obras", icon: Building2},
    {href: "/mapa", label: "Mapa", icon: Map, soon: true},
  ]},
  {group: "Alimentar", items: [
    {href: "/importar", label: "Importar planilha", icon: Upload},
  ]},
  {group: "Financeiro", items: [
    {href: "/fopag", label: "FOPAG semanal", icon: CalendarClock},
    {href: "/financeiro", label: "Contratos e obrigações", icon: Wallet},
    {href: "/conciliacao", label: "Conciliação", icon: Scale},
  ]},
  {group: "Campo", items: [
    {href: "/atividades", label: "Atividades", icon: HardHat},
    {href: "/medicoes", label: "Medições", icon: ClipboardList},
    {href: "/materiais", label: "Materiais", icon: Package},
    {href: "/relatorios", label: "Relatórios", icon: FileBarChart},
  ]},
];
const MOBILE = ["/", "/inteligencia", "/obras", "/fopag", "/medicoes"];

function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(href + "/");
}

export function AppShell({children, source, alertsOpen = 0}: {children: ReactNode; source: "api" | "reference"; alertsOpen?: number}) {
  const pathname = usePathname();
  const router = useRouter();
  const [query, setQuery] = useState("");
  const items = NAV.flatMap(group => group.items);
  return <div className="app">
    <aside className="sidebar" aria-label="Navegação principal">
      <Link href="/" className="brand brand-logo" aria-label="Aggilli Obras Intelligence — início">
        <img src="/aggilli-intelligence.webp" alt="Aggilli Intelligence" width={1400} height={320}/>
        <small>OBRAS INTELLIGENCE</small></Link>
      {NAV.map(group => <div key={group.group}>
        <div className="nav-group">{group.group}</div>
        {group.items.map(item => {
          const Icon = item.icon;
          if (item.soon) {
            return <span key={item.href} className="nav-link" aria-disabled="true" title="Em desenvolvimento">
              <Icon/>{item.label}<span className="soon">em breve</span></span>;
          }
          return <Link key={item.href} href={item.href} className={"nav-link" + (isActive(pathname, item.href) ? " active" : "")}>
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
          ? <a className="btn" href="/api/auth/logout" title="Sair">Sair</a>
          : <a className="btn primary" href="/login">Entrar</a>}
      </header>
      <main className="content">{children}</main>
    </div>
    <nav className="mobile-nav" aria-label="Navegação">
      {MOBILE.map(href => {
        const item = items.find(entry => entry.href === href)!;
        const Icon = item.icon;
        return <Link key={href} href={href} className={isActive(pathname, href) ? "active" : ""}><Icon/>{item.label.split(" ")[0]}</Link>;
      })}
    </nav>
  </div>;
}

export function PageHead({eyebrow, title, subtitle, actions}: {eyebrow?: string; title: string; subtitle?: string; actions?: ReactNode}) {
  return <div className="page-head">
    <div>{eyebrow && <div className="eyebrow">{eyebrow}</div>}<h1>{title}</h1>{subtitle && <p>{subtitle}</p>}</div>
    {actions && <div className="actions">{actions}</div>}
  </div>;
}
