import Link from "next/link";
import {AlertTriangle, Boxes, Info, Lock, LogIn, Package, Wallet} from "lucide-react";
import {PageHead} from "../../../components/app-shell";
import {Callout, Card, Kpi} from "../../../components/ui";
import {Coverage, Flags, brl, qty} from "../../../components/material-ui";
import {apiGet, type MaterialRow} from "../../../lib/api";

export const dynamic = "force-dynamic";

export default async function Materiais() {
  const data = await apiGet<{materials: MaterialRow[]; stock_value: string; flagged: number}>("/materials/overview");
  if (!data) return <>
    <PageHead title="Materiais" subtitle="Estoque por obra, custo médio, consumo e previsão de ruptura."/>
    <Callout tone="info" icon={Lock}>Entre para ver os materiais. <a className="link" href="/login"><LogIn size={14}/> Entrar</a></Callout>
  </>;
  const rows = [...data.materials].sort((a, b) => b.flags.length - a.flags.length || (a.project ?? "").localeCompare(b.project ?? "")
    || a.name.localeCompare(b.name));
  const projects = new Map(data.materials.map(m => [m.project_id, m.project ?? ""]));
  const consumed = data.materials.reduce((total, m) => total + Number(m.consumed_value), 0);
  return <>
    <PageHead eyebrow="Campo" title="Materiais"
              subtitle="Entradas e saídas alimentam o saldo a custo médio, comparam o consumo com o avanço medido e projetam quando o estoque acaba."/>
    <div className="kpis">
      <Kpi label="Valor em estoque" value={brl(data.stock_value)} note="saldo × custo médio ponderado" icon={Wallet}/>
      <Kpi label="Consumido" value={brl(String(consumed))} note="saídas valorizadas ao custo médio" icon={Boxes} tone="info"/>
      <Kpi label="Itens controlados" value={String(data.materials.length)} note={projects.size + " obras"} icon={Package} tone="ok"/>
      <Kpi label="Com sinal de atenção" value={String(data.flagged)} note="estoque baixo, ruptura ou consumo acima" icon={AlertTriangle}
           tone={data.flagged ? "danger" : "ok"}/>
    </div>
    <div className="grid-main">
      <Card flush title="Estoque de todas as obras" subtitle="Itens com sinal de atenção aparecem primeiro">
        <div className="table-wrap"><table>
          <thead><tr><th>Material</th><th>Obra</th><th className="num">Saldo</th><th className="num">Custo médio</th><th className="num">Valor</th>
            <th>Cobertura</th><th>Situação</th></tr></thead>
          <tbody>{rows.map(m => <tr key={m.id}>
            <td><b>{m.name}</b>{m.category && <span className="cell-sub">{m.category}</span>}</td>
            <td><Link className="link" href={"/obras/" + m.project_id + "/materiais"}>{m.project}</Link></td>
            <td className="num">{qty(m.balance)} {m.unit}</td>
            <td className="num">{brl(m.avg_cost)}</td>
            <td className="num">{brl(m.stock_value)}</td>
            <td><Coverage days={m.coverage_days}/></td>
            <td><Flags flags={m.flags}/></td>
          </tr>)}
          {!rows.length && <tr><td colSpan={7} className="empty">Nenhum material cadastrado. Abra uma obra e cadastre os materiais que quer controlar.</td></tr>}</tbody>
        </table></div>
      </Card>
      <div className="stack">
        <Card flush title="Por obra" subtitle="Abra para lançar entradas e saídas">
          {[...projects].map(([id, name]) => {
            const items = data.materials.filter(m => m.project_id === id);
            return <Link key={id} href={"/obras/" + id + "/materiais"} className="list-item">
              <div style={{flex: 1}}><b>{name}</b><small>{items.length} itens · {items.filter(m => m.flags.length).length} com atenção</small></div>
              <b>{brl(String(items.reduce((t, m) => t + Number(m.stock_value), 0)))}</b></Link>;
          })}
          {!projects.size && <p className="empty">Nenhuma obra com materiais ainda. Abra uma obra e use “Materiais”.</p>}
        </Card>
        <Callout tone="info" icon={Info}>Consumo acima do avanço compara o que saiu do estoque com o previsto × avanço aprovado do serviço vinculado
          (tolerância de 15%). A cobertura usa a média de saídas dos últimos 30 dias.</Callout>
      </div>
    </div>
  </>;
}
