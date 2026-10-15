"use client";
import {useMemo, useState} from "react";
import Link from "next/link";
import {useSearchParams} from "next/navigation";
import {AlertTriangle, Download} from "lucide-react";
import {money, slug, sum} from "../../../lib/portfolio";
import {Badge, type Tone} from "../../../components/ui";
import type {ScheduleRow} from "../../../lib/data";

const CATEGORY_TONE: Record<string, Tone> = {
  "Mão de obra": "info", Material: "brand", Serviço: "ok", Combustível: "warn", Equipamento: "danger", Outros: "brand",
};
const STATUS: Record<string, {label: string; tone: Tone}> = {SCHEDULED: {label: "Programado", tone: "warn"}, PAID: {label: "Pago", tone: "ok"}};

export function FopagTable({rows, fileName}: {rows: ScheduleRow[]; fileName: string}) {
  const params = useSearchParams();
  const projects = useMemo(() => Array.from(new Set(rows.map(row => row.project))).sort(), [rows]);
  const fromQuery = projects.find(name => slug(name) === params.get("obra"));
  const [search, setSearch] = useState(params.get("q") ?? "");
  const [project, setProject] = useState(fromQuery ?? "Todas as obras");
  const [category, setCategory] = useState("Todas");
  const categories = useMemo(() => ["Todas", ...Array.from(new Set(rows.map(row => row.category)))], [rows]);
  const filtered = useMemo(() => rows.filter(row =>
    (project === "Todas as obras" || row.project === project) && (category === "Todas" || row.category === category) &&
    [row.supplier, row.project, row.work, row.notes ?? ""].join(" ").toLowerCase().includes(search.toLowerCase())),
  [rows, project, category, search]);

  const exportCsv = () => {
    const lines = [["Fornecedor", "Obra", "Serviço", "Categoria", "Situação", "Data", "Valor (BRL)", "Observação"],
      ...filtered.map(row => [row.supplier, row.project, row.work, row.category, STATUS[row.status]?.label ?? row.status, row.date,
        row.amount.toFixed(2), row.notes ?? ""])];
    const csv = "﻿" + lines.map(line => line.map(value => '"' + String(value).replaceAll('"', '""') + '"').join(";")).join("\r\n");
    const url = URL.createObjectURL(new Blob([csv], {type: "text/csv;charset=utf-8"}));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = fileName;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return <section className="card">
    <div className="toolbar">
      <input className="input" aria-label="Pesquisar lançamentos" placeholder="Buscar fornecedor, serviço ou obra…" value={search}
             onChange={event => setSearch(event.target.value)}/>
      <select className="select" aria-label="Filtrar obra" value={project} onChange={event => setProject(event.target.value)}>
        <option>Todas as obras</option>
        {projects.map(name => <option key={name}>{name}</option>)}
      </select>
      <select className="select" aria-label="Filtrar categoria" value={category} onChange={event => setCategory(event.target.value)}>
        {categories.map(name => <option key={name}>{name}</option>)}
      </select>
      <button className="btn" type="button" onClick={exportCsv} disabled={!filtered.length}><Download/>Exportar CSV</button>
    </div>
    <div className="table-wrap">
      <table>
        <thead><tr><th>Fornecedor / equipe</th><th>Obra</th><th>Serviço</th><th>Categoria</th><th>Situação</th>
          <th className="num">Valor</th></tr></thead>
        <tbody>
          {filtered.map(row => <tr key={row.key}>
            <td><b>{row.supplier}</b>{row.notes && <div className="note"><AlertTriangle/>{row.notes}</div>}</td>
            <td><Link className="link" style={{fontWeight: 500}} href={row.projectHref}>{row.project}</Link></td>
            <td>{row.work}</td>
            <td><Badge tone={CATEGORY_TONE[row.category] ?? "neutral"}>{row.category}</Badge></td>
            <td><Badge tone={STATUS[row.status]?.tone ?? "neutral"}>{STATUS[row.status]?.label ?? row.status}</Badge></td>
            <td className="num"><b>{money(row.amount)}</b></td>
          </tr>)}
          {!filtered.length && <tr><td colSpan={6} className="empty">Nenhum lançamento com esses filtros.</td></tr>}
        </tbody>
        <tfoot><tr><td colSpan={5}>Total filtrado · {filtered.length} lançamentos</td>
          <td className="num">{money(sum(filtered.map(row => row.amount)))}</td></tr></tfoot>
      </table>
    </div>
  </section>;
}
