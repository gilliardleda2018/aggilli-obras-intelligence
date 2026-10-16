import type {ReactNode} from "react";
import {redirect} from "next/navigation";
import {AppShell} from "../../components/app-shell";
import {hasSession} from "../../lib/data";
import {apiGet, type AlertsResponse, type Me} from "../../lib/api";

export default async function AppLayout({children}: {children: ReactNode}) {
  const session = await hasSession();
  if (!session) redirect("/login");
  const [alerts, me] = session ? await Promise.all([apiGet<AlertsResponse>("/alerts"), apiGet<Me>("/me")]) : [null, null];
  const manager = Boolean(me?.organizations.some(o => o.role === "OWNER" || o.role === "ADMIN"));
  return <AppShell source="api" alertsOpen={alerts?.open ?? 0}
                   account={me ? {mustChange: me.must_change_password, manager, license: me.license} : null}>{children}</AppShell>;
}
