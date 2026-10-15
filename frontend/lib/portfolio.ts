import {activities, contracts, locations, payroll, suppliers, type WeeklyItem} from "./tuntum-data";

/** Reference period of the imported records (FOPAG 28/08/2026 + report received 14/10/2026). */
export const SOURCE = {label: "FOPAG 28/08/2026", detail: "Importação de referência · não conciliada"};

export const sum = (values: number[]) => values.reduce((total, value) => total + value, 0);

export const slug = (name: string) =>
  name.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");

export const projectBySlug = (value: string) => locations.find(name => slug(name) === value) ?? null;

export type ProjectSummary = {
  name: string;
  slug: string;
  weekly: number;          // FOPAG items allocated to this project
  weeklyItems: number;
  contractTotal: number;
  contractAdvance: number;
  contractBalance: number;
  activity: string | null;
  flagged: number;         // FOPAG items with reconciliation notes
};

export function projectSummaries(): ProjectSummary[] {
  return locations.map(name => {
    const items = payroll.filter(item => item.project === name);
    const own = contracts.filter(contract => contract.project === name);
    return {
      name,
      slug: slug(name),
      weekly: sum(items.map(item => item.amount)),
      weeklyItems: items.length,
      contractTotal: sum(own.map(contract => contract.total)),
      contractAdvance: sum(own.map(contract => contract.advance)),
      contractBalance: sum(own.map(contract => contract.balance)),
      activity: activities.find(activity => activity.project === name)?.description ?? null,
      flagged: items.filter(item => item.notes).length,
    };
  });
}

export function totals() {
  const weekly = sum(payroll.map(item => item.amount));
  const labor = sum(payroll.filter(item => item.category === "Mão de obra").map(item => item.amount));
  return {
    weekly,
    labor,
    other: weekly - labor,
    items: payroll.length,
    laborItems: payroll.filter(item => item.category === "Mão de obra").length,
    supplierDebt: sum(suppliers.map(supplier => supplier.debt)),
    suppliers: suppliers.length,
    contractTotal: sum(contracts.map(contract => contract.total)),
    contractAdvance: sum(contracts.map(contract => contract.advance)),
    contractBalance: sum(contracts.map(contract => contract.balance)),
    projects: locations.length,
    flagged: payroll.filter(item => item.notes).length,
  };
}

export function byCategory() {
  const categories = Array.from(new Set(payroll.map(item => item.category)));
  return categories
    .map(category => ({category, amount: sum(payroll.filter(item => item.category === category).map(item => item.amount))}))
    .sort((a, b) => b.amount - a.amount);
}

export function topPayments(limit = 6): WeeklyItem[] {
  return [...payroll].sort((a, b) => b.amount - a.amount).slice(0, limit);
}

/** Divergences found while reconciling the source documents (docs/IMPORTACAO-TUNTUM-2026.md). */
export const reconciliation = [
  {title: "Posto Ana Luiza", detail: "Relato cita R$ 935,00; a folha e a soma dos abastecimentos dão R$ 985,87."},
  {title: "Renata — sondagem", detail: "Relato cita R$ 1.800,00; a FOPAG registra R$ 1.600,00 (parcela de R$ 3.200,00)."},
  {title: "Juarez — garagem", detail: "Relato cita R$ 2.000,00; a FOPAG registra R$ 1.500,00."},
  {title: "Laércio — pintura", detail: "Relato aponta Casa BDC; FOPAG anterior aponta MG Tabocal."},
  {title: "Rateio entre obras", detail: "Cabiludo e José das Cruz atuaram em várias obras; os valores precisam ser rateados."},
  {title: "Nomes a padronizar", detail: "Casa Barra/Casa BDC, Aider/Aide e JK Metalúrgica/Kleyton."},
];

export const money = (value: number) => value.toLocaleString("pt-BR", {style: "currency", currency: "BRL"});

export const compactMoney = (value: number) =>
  value >= 1_000_000 ? "R$ " + (value / 1_000_000).toLocaleString("pt-BR", {maximumFractionDigits: 2}) + " mi"
  : value >= 10_000 ? "R$ " + (value / 1000).toLocaleString("pt-BR", {maximumFractionDigits: 1}) + " mil"
  : money(value);

export const pct = (part: number, whole: number) => (whole > 0 ? Math.round((part / whole) * 1000) / 10 : 0);

/** Percentage label in Brazilian format, e.g. "37,9%". */
export const percent = (part: number, whole: number) => pct(part, whole).toLocaleString("pt-BR") + "%";
