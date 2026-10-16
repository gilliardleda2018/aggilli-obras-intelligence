import Link from "next/link";
import {AlertTriangle, FileSignature, HandCoins, Landmark, Scale} from "lucide-react";
import {PageHead} from "../../../components/app-shell";
import {PrintButton} from "../../../components/print-button";
import {Callout, Card, Kpi, Meter} from "../../../components/ui";
import {getDataset, summarize} from "../../../lib/data";
import {apiGet, type FinancialDiagnosis} from "../../../lib/api";
import {FinancialDiagnosisPanel} from "../../../components/financial-diagnosis";
import {compactMoney, money, pct, percent, sum} from "../../../lib/portfolio";

export const dynamic = "force-dynamic";

export default async function Financeiro() {
  const [data, diagnosis] = await Promise.all([getDataset(), apiGet<FinancialDiagnosis>("/finance-agent/diagnosis")]);
  const t = summarize(data);
  const contracts = [...data.contracts].sort((a, b) => (b.balance ?? 0) - (a.balance ?? 0));
  const payables = data.payables;
  return <>
    {data.error && <div style={{marginBottom: 16}}><Callout icon={AlertTriangle}>{data.error}</Callout></div>}
    <PageHead eyebrow={data.sourceLabel} title="Contratos e obrigações"
              subtitle="Empreitadas de mão de obra, adiantamentos e o que ainda está em aberto com fornecedores." actions={<PrintButton/>}/>
    <div className="kpis">
      <Kpi label="Contratado" value={compactMoney(t.contractTotal)} note={t.contractCount + " contratos"} icon={FileSignature}/>
      <Kpi label="Adiantado (informado)" value={compactMoney(t.contractAdvance)} note={percent(t.contractAdvanceValued, t.contractTotal) + " dos contratos com valor"}
           icon={HandCoins} tone="info"/>
      <Kpi label="Saldo informado" value={compactMoney(t.contractBalance)} note="conforme a planilha · a conferir" icon={Landmark} tone="ok"/>
      <Kpi label="Obrigações em aberto" value={compactMoney(sum(payables.map(p => p.outstanding)))} note={payables.length + " despesas sem pagamento comprovado"}
           icon={Scale} tone="warn"/>
    </div>

    <FinancialDiagnosisPanel data={diagnosis}/>
    <div className="stack">
      <Card flush title="Empreiteiros e contratos" subtitle="Adiantamento e saldo como informados na fonte; o saldo nem sempre é contrato menos adiantamento">
        <div className="table-wrap"><table>
          <thead><tr><th>Empreiteiro</th><th>Obra</th><th className="num">Contrato</th><th className="num">Adiantado</th>
            <th style={{width: 180}}>Execução financeira</th><th className="num">Saldo informado</th></tr></thead>
          <tbody>{contracts.map((contract, index) => <tr key={index}>
            <td><b>{contract.contractor}</b></td>
            <td><Link className="link" style={{fontWeight: 500}} href={contract.projectHref}>{contract.project}</Link></td>
            <td className="num">{contract.total === null ? "sem valor" : money(contract.total)}</td>
            <td className="num">{contract.advance === null ? "—" : money(contract.advance)}</td>
            <td>{contract.total ? <><div className="meter-label"><span>{percent(contract.advance ?? 0, contract.total)} adiantado</span></div>
              <Meter value={pct(contract.advance ?? 0, contract.total)}/></> : <span className="cell-sub">sem valor de contrato</span>}</td>
            <td className="num"><b>{contract.balance === null ? "—" : money(contract.balance)}</b></td>
          </tr>)}</tbody>
          <tfoot><tr><td colSpan={2}>Total</td><td className="num">{money(t.contractTotal)}</td><td className="num">{money(t.contractAdvance)}</td>
            <td/><td className="num">{money(t.contractBalance)}</td></tr></tfoot>
        </table></div>
      </Card>

      <Card flush title="Obrigações em aberto" subtitle="Despesas registradas e ainda sem pagamento comprovado">
        <div className="table-wrap"><table>
          <thead><tr><th>Fornecedor</th><th>Obra</th><th className="num">Valor</th><th className="num">Programado</th>
            <th className="num">Pago</th><th className="num">Em aberto</th></tr></thead>
          <tbody>{payables.map((row, index) => <tr key={index}>
            <td><b>{row.supplier}</b><span className="cell-sub">{row.description}</span></td>
            <td>{row.project}</td>
            <td className="num">{money(row.amount)}</td>
            <td className="num">{money(row.scheduled)}</td>
            <td className="num">{money(row.paid)}</td>
            <td className="num"><b>{money(row.outstanding)}</b></td>
          </tr>)}
          {!payables.length && <tr><td colSpan={6} className="empty">Nenhuma obrigação em aberto.</td></tr>}</tbody>
          <tfoot><tr><td colSpan={2}>Total</td><td className="num">{money(sum(payables.map(p => p.amount)))}</td>
            <td className="num">{money(sum(payables.map(p => p.scheduled)))}</td><td className="num">{money(sum(payables.map(p => p.paid)))}</td>
            <td className="num">{money(sum(payables.map(p => p.outstanding)))}</td></tr></tfoot>
        </table></div>
      </Card>
    </div>
  </>;
}
