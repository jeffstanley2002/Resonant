import type {
  DataDeletionResponse,
  JobMatch,
  MatchRequest,
  MatchResponse,
  ResumeAnalysis,
  SavedJob,
  SessionResponse,
} from "@resonant/shared";
import { matchRequestSchema } from "@resonant/shared";

export type {
  DataDeletionResponse,
  JobMatch,
  MatchResponse,
  ResumeAnalysis,
  SavedJob,
  SessionResponse,
} from "@resonant/shared";

export type CreateMatchesRequest = MatchRequest & {
  token?: string | null;
  botToken?: string | null;
  csrfToken?: string | null;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export const demoResume = `AI engineer and full-stack developer with Python, TypeScript, React, Next.js, FastAPI, Postgres, Supabase, LangGraph, LLM evaluation, Playwright testing, and security experience. Built production-style dashboards, model routing, prompt evaluation, and cloud deployments on Vercel and Render.`;

export async function analyzeResume(
  file: File,
  token?: string | null,
  botToken?: string | null,
  csrfToken?: string | null,
): Promise<ResumeAnalysis> {
  const body = new FormData();
  body.append("file", file);
  const response = await fetch(`${API_BASE_URL}/resumes/analyze`, {
    method: "POST",
    headers: requestHeaders({ token, botToken, csrfToken }),
    credentials: "include",
    body,
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail ?? "Unable to analyze resume");
  }

  return camelize(await response.json()) as ResumeAnalysis;
}

export async function createMatches(request: CreateMatchesRequest): Promise<MatchResponse> {
  const payload = matchRequestSchema.parse({
    resumeId: request.resumeId,
    resumeText: request.resumeText,
    targetRole: request.targetRole,
    location: request.location,
    limit: request.limit,
  });
  const response = await fetch(`${API_BASE_URL}/agent/matches`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...requestHeaders({
        token: request.token,
        botToken: request.botToken,
        csrfToken: request.csrfToken,
      }),
    },
    body: JSON.stringify({
      ...(payload.resumeId ? { resume_id: payload.resumeId } : {}),
      ...(payload.resumeText ? { resume_text: payload.resumeText } : {}),
      target_role: payload.targetRole,
      location: payload.location,
      limit: payload.limit,
    }),
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail ?? "Unable to create job matches");
  }

  return camelize(await response.json()) as MatchResponse;
}

export async function saveJob(
  match: JobMatch,
  token?: string | null,
  csrfToken?: string | null,
): Promise<SavedJob> {
  const response = await fetch(`${API_BASE_URL}/saved-jobs`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...requestHeaders({ token, csrfToken }),
    },
    body: JSON.stringify({
      external_job_id: match.job.externalId,
      title: match.job.title,
      company: match.job.company,
      job_url: match.job.url,
    }),
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail ?? "Unable to save job");
  }

  return camelize(await response.json()) as SavedJob;
}

export async function listSavedJobs(
  token?: string | null,
  csrfToken?: string | null,
): Promise<SavedJob[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/saved-jobs`, {
      credentials: "include",
      headers: requestHeaders({ token, csrfToken }),
    });
    if (!response.ok) {
      return [];
    }
    const payload = camelize(await response.json());
    return Array.isArray(payload) ? (payload as SavedJob[]) : [];
  } catch {
    return [];
  }
}

export async function submitFeedback(
  runId: string,
  rating: number,
  token?: string | null,
  csrfToken?: string | null,
) {
  const response = await fetch(`${API_BASE_URL}/feedback`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...requestHeaders({ token, csrfToken }),
    },
    body: JSON.stringify({ run_id: runId, rating }),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail ?? "Unable to submit feedback");
  }
}

export async function establishBackendSession(token: string): Promise<SessionResponse | null> {
  const response = await fetch(`${API_BASE_URL}/session`, {
    method: "POST",
    credentials: "include",
    headers: requestHeaders({ token }),
  });
  if (!response.ok) {
    return null;
  }
  return camelize(await response.json()) as SessionResponse;
}

export async function clearBackendSession(csrfToken?: string | null): Promise<void> {
  await fetch(`${API_BASE_URL}/session`, {
    method: "DELETE",
    credentials: "include",
    headers: requestHeaders({ csrfToken }),
  });
}

export async function deleteAccountData(
  token?: string | null,
  csrfToken?: string | null,
): Promise<DataDeletionResponse> {
  const response = await fetch(`${API_BASE_URL}/account/data`, {
    method: "DELETE",
    credentials: "include",
    headers: requestHeaders({ token, csrfToken }),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail ?? "Unable to delete account data");
  }
  return camelize(await response.json()) as DataDeletionResponse;
}

function authHeaders(token?: string | null): Record<string, string> {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function requestHeaders({
  token,
  botToken,
  csrfToken,
}: {
  token?: string | null;
  botToken?: string | null;
  csrfToken?: string | null;
}): Record<string, string> {
  return {
    ...authHeaders(token),
    ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}),
    ...(botToken ? { "X-Turnstile-Token": botToken } : {}),
  };
}

function camelize(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(camelize);
  }
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, nested]) => [toCamel(key), camelize(nested)]),
    );
  }
  return value;
}

function toCamel(value: string): string {
  return value.replace(/_([a-z])/g, (_, letter: string) => letter.toUpperCase());
}
