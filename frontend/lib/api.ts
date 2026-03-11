/**
 * API client для /app маршрутов.
 * Использует credentials: 'include' для отправки cookie сессии.
 * Все endpoints /me/* — from_user определяется на backend из сессии.
 */
import { BackEnd_URL } from "@/config/url";

const defaultHeaders: Record<string, string> = {
  "Content-Type": "application/json",
};

function apiUrl(path: string): string {
  return `${BackEnd_URL}/api/v1${path}`;
}

export async function authExchangeToken(token: string): Promise<{ ok: boolean; telegram_id?: number }> {
  const res = await fetch(apiUrl("/auth/exchange"), {
    method: "POST",
    headers: defaultHeaders,
    credentials: "include",
    body: JSON.stringify({ token }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail = err?.detail;
    if (process.env.NODE_ENV === "development") {
      console.debug("[auth] Exchange failed:", res.status, typeof detail === "string" ? detail : "invalid token");
    }
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail) && detail[0]?.msg
          ? detail[0].msg
          : detail?.message || "Ошибка входа";
    throw new Error(message);
  }
  return res.json();
}

export async function authMe(): Promise<{ telegram_id: number } | null> {
  const res = await fetch(apiUrl("/auth/me"), { credentials: "include" });
  if (res.status === 401) return null;
  if (!res.ok) return null;
  return res.json();
}

export async function meBestResult(): Promise<{ items: any[] }> {
  const res = await fetch(apiUrl("/me/best_result"), { credentials: "include" });
  if (!res.ok) return { items: [] };
  return res.json();
}

export async function meLike(toUserId: number, isSuperlike = false): Promise<void> {
  const res = await fetch(apiUrl("/me/likes"), {
    method: "POST",
    headers: defaultHeaders,
    credentials: "include",
    body: JSON.stringify({ to_user: toUserId, is_superlike: isSuperlike }),
  });
  if (res.status === 403) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data?.detail?.error || "Лимит лайков исчерпан");
  }
  if (!res.ok) throw new Error("Ошибка лайка");
}

export async function meDislike(toUserId: number): Promise<void> {
  const res = await fetch(apiUrl("/me/dislike"), {
    method: "POST",
    headers: defaultHeaders,
    credentials: "include",
    body: JSON.stringify({ to_user: toUserId }),
  });
  if (!res.ok) throw new Error("Ошибка дизлайка");
}

export async function meMatches(): Promise<{ items: any[]; bot_username?: string }> {
  const res = await fetch(apiUrl("/me/matches"), { credentials: "include" });
  if (!res.ok) return { items: [] };
  return res.json();
}
