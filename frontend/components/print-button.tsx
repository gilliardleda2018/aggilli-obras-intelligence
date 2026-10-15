"use client";
import {Printer} from "lucide-react";

export function PrintButton({label = "Imprimir"}: {label?: string}) {
  return <button className="btn" type="button" onClick={() => window.print()}><Printer/>{label}</button>;
}
