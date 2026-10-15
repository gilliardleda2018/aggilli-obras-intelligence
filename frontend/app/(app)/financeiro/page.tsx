import {FileSignature, HandCoins, Landmark, Truck} from "lucide-react";
import {PageHead} from "../../../components/app-shell";
import {PrintButton} from "../../../components/print-button";
import {Card, Kpi, Meter} from "../../../components/ui";
import {contracts, suppliers} from "../../../lib/tuntum-data";
import {compactMoney, money, pct, percent, SOURCE, sum, totals} from "../../../lib/portfolio";

export default function Financeiro() {
  const t = totals();
  const sorted = [...contracts].sort((a, b) => b.balance - a.balance);
  return <>
    <PageHead eyebrow={SOURCE.label} title="Contratos e fornecedores"
              subtitle="Empreitadas de mão de obra, adiantamentos e dívidas com fornecedores de materiais." actions={<PrintButton/>}/>
    <div className="kpis">
      <Kpi label="Contratado" value={compactMoney(t.contractTotal)} note={contracts.length + " contratos na folha"} icon={FileSignature}/>
      <Kpi label="Adiantado" value={compactMoney(t.contractAdvance)} note={percent(t.contractAdvance, t.contractTotal) + " do contratado"}
           icon={HandCoins} tone="info"/>
      <Kpi label="Saldo registrado" value={compactMoney(t.contractBalance)} note="conforme a planilha · a conferir" icon={Landmark} tone="ok"/>
      <Kpi label="Dívidas com fornecedores" value={money(t.supplierDebt)} note={suppliers.length + " fornecedores"} icon={Truck} tone="warn"/>
    </div>

    <div className="stack">
      <Card flush title="Empreiteiros e contratos" subtitle="Valores reproduzidos da planilha, sujeitos a conferência">
        <div className="table-wrap"><table>
          <thead><tr><th>Profissional</th><th>Obra</th><th className="num">Contrato</th><th className="num">Adiantado</th>
            <th style={{width: 180}}>Execução financeira</th><th className="num">Saldo na folha</th></tr></thead>
          <tbody>{sorted.map((contract, index) => <tr key={index}>
            <td><b>{contract.name}</b></td>
            <td>{contract.project}</td>
            <td className="num">{money(contract.total)}</td>
            <td className="num">{money(contract.advance)}</td>
            <td><div className="meter-label"><span>{percent(contract.advance, contract.total)} adiantado</span></div>
              <Meter value={pct(contract.advance, contract.total)}/></td>
            <td className="num"><b>{money(contract.balance)}</b></td>
          </tr>)}</tbody>
          <tfoot><tr><td colSpan={2}>Total</td><td className="num">{money(t.contractTotal)}</td><td className="num">{money(t.contractAdvance)}</td>
            <td/><td className="num">{money(t.contractBalance)}</td></tr></tfoot>
        </table></div>
      </Card>

      <Card flush title="Fornecedores de materiais" subtitle="Dívidas relatadas e valores programados para abatimento — não são comprovantes">
        <div className="table-wrap"><table>
          <thead><tr><th>Fornecedor</th><th className="num">Dívida informada</th><th className="num">Programado na semana</th>
            <th className="num">Saldo se o programado for pago</th></tr></thead>
          <tbody>{suppliers.map(supplier => <tr key={supplier.name}>
            <td><b>{supplier.name}</b></td>
            <td className="num">{money(supplier.debt)}</td>
            <td className="num">{money(supplier.planned)}</td>
            <td className="num"><b>{money(supplier.debt - supplier.planned)}</b></td>
          </tr>)}</tbody>
          <tfoot><tr><td>Total</td><td className="num">{money(t.supplierDebt)}</td>
            <td className="num">{money(sum(suppliers.map(supplier => supplier.planned)))}</td>
            <td className="num">{money(t.supplierDebt - sum(suppliers.map(supplier => supplier.planned)))}</td></tr></tfoot>
        </table></div>
      </Card>
    </div>
  </>;
}
