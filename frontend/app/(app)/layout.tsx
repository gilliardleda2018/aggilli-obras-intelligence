import type {ReactNode} from "react";
import {AppShell} from "../../components/app-shell";
import {hasSession} from "../../lib/data";
import {apiGet, type AlertsResponse} from "../../lib/api";

export default async function AppLayout({children}: {children: ReactNode}) {
  const session = await hasSession();
  const alerts = session ? await apiGet<AlertsResponse>("/alerts") : null;
  return <AppShell source={session ? "api" : "reference"} alertsOpen={alerts?.open ?? 0}>{children}</AppShell>;
}
