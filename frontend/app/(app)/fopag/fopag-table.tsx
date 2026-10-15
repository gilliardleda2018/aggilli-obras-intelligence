"use client";
import {useMemo, useState} from "react";
import {useSearchParams} from "next/navigation";
import {AlertTriangle, Download} from "lucide-react";
import {locations, payroll} from "../../../lib/tuntum-data";
import {money, projectBySlug, sum} from "../../../lib/portfolio";
import {Badge, type Tone} from "../../../components/ui";

const CATEGORY_TONE: Record<string, Tone> = {
  "Mão de obra": "info", Material: "brand", Serviço: "ok", Combustível: "warn", Equipamento: "danger", Outros: "brand",
};

export function FopagTable() {
  const params = useSearchParams();
  const [search, setSearch] = useState(params.get("q") ?? "");
  const [project, setProject] = useState(projectBySlug(params.get("obra") ?? "") ?? "Todas as obras");
  const [category, setCategory] = useState("Todas");
  const categories = useMemo(() => ["Todas", ...Array.from(new Set(payroll.map(item => item.category)))], []);
  const rows = useMemo(() => payroll.filter(item =>
    (project === "Todas as obras" || item.project === project) && (category === "Todas" || item.category === category) &&
    [item.name, item.project, item.work, item.notes ?? ""].join(" ").toLowerCase().includes(search.toLowerCase())),
  [project, category, search]);

  const exportCsv = () => {
    const lines = [["Fornecedor", "Obra", "Serviço", "Categoria", "Programado (BRL)", "Observação"],
      ...rows.map(item => [item.name, item.project, item.work, item.category, item.amount.toFixed(2), item.notes ?? ""])];
    const csv = "﻿" + lines.map(line => line.map(value => '"' + String(value).replaceAll('"', '""') + '"').join(";")).join("\r\n");
    const url = URL.createObjectURL(new Blob([csv], {type: "text/csv;charset=utf-8"}));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "fopag-tuntum-28-08-2026.csv";
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return <section className="card">
    <div className="toolbar">
      <input className="input" aria-label="Pesquisar lançamentos" placeholder="Buscar fornecedor, serviço ou obra…" value={search}
             onChange={event => setSearch(event.target.value)}/>
      <select className="select" aria-label="Filtrar obra" value={project} onChange={event => setProject(event.target.value)}>
        <option>Todas as obras</option>
        <option>Diversas obras</option>
        {locations.map(name => <option key={name}>{name}</option>)}
      </select>
      <select className="select" aria-label="Filtrar categoria" value={category} onChange={event => setCategory(event.target.value)}>
        {categories.map(name => <option key={name}>{name}</option>)}
      </select>
      <button className="btn" type="button" onClick={exportCsv} disabled={!rows.length}><Download/>Exportar CSV</button>
    </div>
    <div className="table-wrap">
      <table>
        <thead><tr><th>Fornecedor / equipe</th><th>Obra</th><th>Serviço</th><th>Categoria</th><th className="num">Programado</th></tr></thead>
        <tbody>
          {rows.map((item, index) => <tr key={index}>
            <td><b>{item.name}</b>{item.notes && <div className="note"><AlertTriangle/>{item.notes}</div>}</td>
            <td>{item.project}</td>
            <td>{item.work}</td>
            <td><Badge tone={CATEGORY_TONE[item.category] ?? "neutral"}>{item.category}</Badge></td>
            <td className="num"><b>{money(item.amount)}</b></td>
          </tr>)}
          {!rows.length && <tr><td colSpan={5} className="empty">Nenhum lançamento com esses filtros.</td></tr>}
        </tbody>
        <tfoot><tr><td colSpan={4}>Total filtrado · {rows.length} lançamentos</td>
          <td className="num">{money(sum(rows.map(item => item.amount)))}</td></tr></tfoot>
      </table>
    </div>
  </section>;
}
