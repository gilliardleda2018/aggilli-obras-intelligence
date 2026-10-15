import Link from "next/link";
import {AlertTriangle, ArrowLeft, Boxes, Lock, Package, Wallet} from "lucide-react";
import {PageHead} from "../../../../../components/app-shell";
import {Badge, Callout, Card, Kpi, Meter} from "../../../../../components/ui";
import {MaterialForm, MovementForm} from "../../../../../components/material-forms";
import {Coverage, Flags, brl, qty} from "../../../../../components/material-ui";
import {apiGet, type MaterialRow, type MovementRow, type ServiceRow} from "../../../../../lib/api";

export const dynamic = "force-dynamic";
const br = (iso: string) => iso.slice(0, 10).split("-").reverse().join("/");

export default async function MateriaisObra({params}: {params: Promise<{id: string}>}) {
  const {id} = await params;
  const back = <Link href={"/obras/" + id} className="back"><ArrowLeft/>Obra</Link>;
  const [details, materials, services] = await Promise.all([
    apiGet<{name: string}>("/projects/" + encodeURIComponent(id) + "/details"),
    apiGet<MaterialRow[]>("/projects/" + encodeURIComponent(id) + "/materials"),
    apiGet<{services: ServiceRow[]}>("/projects/" + encodeURIComponent(id) + "/services"),
  ]);
  if (!details || !materials) return <>{back}<Callout icon={Lock}>Obra indisponível, sem sessão ou sem autorização.</Callout></>;
  const movements = (await Promise.all(materials.slice(0, 40).map(m => apiGet<MovementRow[]>("/materials/" + m.id + "/movements"))))
    .flatMap((list, i) => (list ?? []).map(mv => ({...mv, material: materials[i]})))
    .sort((a, b) => b.date.localeCompare(a.date)).slice(0, 25);
  const value = materials.reduce((t, m) => t + Number(m.stock_value), 0);
  const consumed = materials.reduce((t, m) => t + Number(m.consumed_value), 0);
  const flagged = materials.filter(m => m.flags.length).length;
  return <>
    {back}
    <PageHead eyebrow="Materiais" title={details.name}
              subtitle="Lance entradas (compras) e saídas (consumo). O sistema calcula saldo, custo médio e cobertura e compara o consumo com o avanço."/>
    <div className="kpis">
      <Kpi label="Valor em estoque" value={brl(String(value))} note="a custo médio ponderado" icon={Wallet}/>
      <Kpi label="Consumido" value={brl(String(consumed))} note="saídas valorizadas" icon={Boxes} tone="info"/>
      <Kpi label="Itens" value={String(materials.length)} note="materiais controlados" icon={Package} tone="ok"/>
      <Kpi label="Com atenção" value={String(flagged)} note="estoque baixo, ruptura ou consumo acima" icon={AlertTriangle} tone={flagged ? "danger" : "ok"}/>
    </div>
    <div className="grid-main">
      <div className="stack">
        <Card flush title="Estoque" subtitle="Saldo, custo, cobertura e consumo × avanço do serviço">
          {materials.map(m => {
            const expected = m.expected_consumption === null ? null : Number(m.expected_consumption);
            const ratio = expected ? Number(m.consumed) / expected * 100 : null;
            return <div key={m.id} className="list-item" style={{alignItems: "flex-start"}}>
              <div style={{flex: 1}}>
                <b>{m.name}</b> <Flags flags={m.flags}/>
                <small>{[m.category, m.service && "serviço: " + m.service, m.min_stock && "mínimo " + qty(m.min_stock) + " " + m.unit]
                  .filter(Boolean).join(" · ") || "sem categoria"}</small>
                <div className="meter-label" style={{marginTop: 8}}>
                  <span>Saldo <b>{qty(m.balance)} {m.unit}</b> · custo médio {brl(m.avg_cost)} · valor {brl(m.stock_value)}</span>
                  <span>Cobertura <Coverage days={m.coverage_days}/></span></div>
                {ratio !== null && <>
                  <div className="meter-label" style={{marginTop: 8}}>
                    <span>Consumido {qty(m.consumed)} de {qty(m.expected_consumption)} {m.unit} justificados pelo avanço
                      ({(m.service_progress ?? 0).toLocaleString("pt-BR")}%)</span>
                    <span>{ratio.toLocaleString("pt-BR", {maximumFractionDigits: 0})}%</span></div>
                  <Meter value={Math.min(100, ratio)} tone={ratio > 115 ? "var(--danger)" : "var(--ok)"}/></>}
              </div>
            </div>;
          })}
          {!materials.length && <p className="empty">Nenhum material cadastrado. Use o formulário ao lado.</p>}
        </Card>
        <Card flush title="Últimas movimentações" subtitle="Entradas e saídas mais recentes">
          <div className="table-wrap"><table>
            <thead><tr><th>Data</th><th>Material</th><th>Tipo</th><th className="num">Quantidade</th><th className="num">Custo unit.</th><th>Detalhe</th></tr></thead>
            <tbody>{movements.map(mv => <tr key={mv.id}>
              <td>{br(mv.date)}</td>
              <td><b>{mv.material.name}</b></td>
              <td><Badge tone={mv.kind === "IN" ? "ok" : "info"}>{mv.kind === "IN" ? "Entrada" : "Saída"}</Badge></td>
              <td className="num">{qty(mv.quantity)} {mv.material.unit}</td>
              <td className="num">{brl(mv.unit_cost)}</td>
              <td>{[mv.supplier, mv.note].filter(Boolean).join(" — ") || "—"}{mv.expense_id && <span className="cell-sub">gerou despesa</span>}
                <span className="cell-sub">por {mv.recorded_by}</span></td>
            </tr>)}
            {!movements.length && <tr><td colSpan={6} className="empty">Nenhuma movimentação registrada.</td></tr>}</tbody>
          </table></div>
        </Card>
      </div>
      <div className="stack">
        <Card title="Entrada ou saída" subtitle="Compra recebida ou consumo na obra">
          {materials.length ? <MovementForm projectId={id} materials={materials}/> : <p className="empty">Cadastre um material primeiro.</p>}
        </Card>
        <Card title="Novo material" subtitle="Item a controlar nesta obra">
          <MaterialForm projectId={id} services={(services?.services ?? []).map(s => ({id: s.id, name: s.name}))}/>
        </Card>
      </div>
    </div>
  </>;
}
