import type {ReactNode} from "react";
import {AppShell} from "../../components/app-shell";
import {hasSession} from "../../lib/data";

export default async function AppLayout({children}: {children: ReactNode}) {
  return <AppShell source={(await hasSession()) ? "api" : "reference"}>{children}</AppShell>;
}
