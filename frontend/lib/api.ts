import type {
  DocumentDetailRead,
  DocumentRead,
  LoginResponse,
  QuestionAnswerRead,
  ReviewFlagRead,
  UserRead,
} from "./types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export const TOKEN_STORAGE_KEY = "compliance-doc-assistant.token";

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setStoredToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (token) {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } else {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  }
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getStoredToken();
  const headers = new Headers(options.headers);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const message =
      (body && typeof body === "object" && "detail" in body
        ? String((body as { detail: unknown }).detail)
        : null) ?? `Request to ${path} failed with status ${response.status}`;
    throw new ApiError(response.status, message);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export function login(
  username: string,
  password: string,
): Promise<LoginResponse> {
  return apiFetch<LoginResponse>("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
}

export function getCurrentUser(): Promise<UserRead> {
  return apiFetch<UserRead>("/me");
}

export function logout(): Promise<void> {
  return apiFetch<void>("/auth/logout", { method: "POST" });
}

export function listDocuments(): Promise<DocumentRead[]> {
  return apiFetch<DocumentRead[]>("/documents");
}

export function getDocument(documentId: number): Promise<DocumentDetailRead> {
  return apiFetch<DocumentDetailRead>(`/documents/${documentId}`);
}

export function uploadDocument(file: File): Promise<DocumentRead> {
  const formData = new FormData();
  formData.append("file", file);
  return apiFetch<DocumentRead>("/documents", {
    method: "POST",
    body: formData,
  });
}

export function askQuestion(
  documentId: number,
  questionText: string,
): Promise<QuestionAnswerRead> {
  return apiFetch<QuestionAnswerRead>(`/documents/${documentId}/questions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question_text: questionText }),
  });
}

export function listReviewFlags(): Promise<ReviewFlagRead[]> {
  return apiFetch<ReviewFlagRead[]>("/review-flags");
}

export function resolveReviewFlag(
  flagId: number,
  status: "resolved" | "dismissed",
): Promise<ReviewFlagRead> {
  return apiFetch<ReviewFlagRead>(`/review-flags/${flagId}/resolve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
}
