import type { ReactNode } from "react";
export const metadata = { title: "Aggilli Obras Intelligence", description: "Gestão inteligente de obras" };
export default function Layout({ children }: { children: ReactNode }) {
  return <html lang="pt-BR"><body style={{fontFamily:"Arial,sans-serif",margin:0,background:"#f4f7fb",color:"#18253b"}}>{children}</body></html>;
}
