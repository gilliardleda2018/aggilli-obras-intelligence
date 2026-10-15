import {accessToken} from "./session";

const API = process.env.API_BASE_URL || "http://localhost:8000";

/** Authenticated GET against the API; null when there is no session or the call fails. */
export async function apiGet<T>(path: string): Promise<T | null> {
  const token = await accessToken();
  if (!token) return null;
  try {
    const response = await fetch(API + "/api/v1" + path, {headers: {Authorization: "Bearer " + token}, cache: "no-store"});
    return response.ok ? ((await response.json()) as T) : null;
  } catch {
    return null;
  }
}

export type ServiceRow = {
  id: string; name: string; unit: string; planned_quantity: string; weight: string; approved_quantity: string;
  pending_quantity: string; remaining_quantity: string; progress: number;
};
export type MeasurementRow = {
  id: string; project_id: string; project: string; service_id: string; service: string; unit: string; quantity: string;
  status: "PENDING" | "APPROVED" | "REJECTED"; recorded_by: string; measured_on: string | null; notes: string | null;
  created_at: string; decided_by: string | null; decided_at: string | null; decision_reason: string | null;
};
