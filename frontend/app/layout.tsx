import type { ReactNode } from "react";
import "./globals.css";
export const metadata={title:"Aggilli Obras Intelligence",description:"Gestão inteligente de obras"};
export default function Layout({children}:{children:ReactNode}){
 return <html lang="pt-BR"><body>{children}</body></html>;
}
