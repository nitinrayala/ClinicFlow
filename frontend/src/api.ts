import type { Appointment, Audit, Encounter, Generation, Health, Note, ProposedTask, Task, User } from './types';

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) { super(message); this.status = status; }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, { ...options, credentials: 'include', headers: { 'Content-Type': 'application/json', ...options.headers } });
  } catch { throw new ApiError('We couldn’t reach the server. Check your connection and try again. Your edits are still here.', 0); }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const message = typeof body.detail === 'string' ? body.detail : response.status === 422 ? 'Please check the entered values and try again.' : 'Something went wrong. Please try again.';
    if (response.status === 401 && !path.startsWith('/auth/')) window.dispatchEvent(new CustomEvent('clinicflow:session-expired'));
    throw new ApiError(message, response.status);
  }
  return response.json() as Promise<T>;
}
const post = <T,>(path: string, data?: unknown) => request<T>(path, { method: 'POST', body: data === undefined ? undefined : JSON.stringify(data) });
export const api = {
  health: () => request<Health>('/health'),
  me: () => request<User>('/auth/me'),
  login: (email: string, password: string) => post<User>('/auth/login', { email, password }),
  logout: () => post<{ ok: boolean }>('/auth/logout'),
  appointments: () => request<Appointment[]>('/appointments'),
  openEncounter: (id: string) => post<Encounter>(`/appointments/${id}/encounter`),
  encounter: (id: string) => request<Encounter>(`/encounters/${id}`),
  save: (id: string, body: { draft_revision: number; transcript_revision: number; transcript: string; note: Note; proposed_tasks: ProposedTask[] }) => request<Encounter>(`/encounters/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
  generate: (id: string, draft_revision: number, transcript_revision: number) => post<Generation>(`/encounters/${id}/generate`, { draft_revision, transcript_revision }),
  apply: (id: string, generationId: string, draft_revision: number, transcript_revision: number) => post<Encounter>(`/encounters/${id}/generations/${generationId}/apply`, { draft_revision, transcript_revision }),
  approve: (id: string, draft_revision: number, transcript_revision: number) => post<Encounter>(`/encounters/${id}/approve`, { draft_revision, transcript_revision }),
  audit: (id: string) => request<Audit[]>(`/encounters/${id}/audit`),
  team: () => request<User[]>('/team'),
  tasks: () => request<Task[]>('/tasks'),
  claim: (id: string) => post<Task>(`/tasks/${id}/claim`),
  updateTask: (id: string, values: { status?: Task['status']; assignee_id?: string | null }) => request<Task>(`/tasks/${id}`, { method: 'PATCH', body: JSON.stringify(values) }),
};
export const errorMessage = (error: unknown) => error instanceof Error ? error.message : 'Something went wrong. Please try again.';
