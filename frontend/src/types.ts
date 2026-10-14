export type User = { id: string; name: string; email: string; role: 'doctor' | 'staff'; clinic_id: string; clinic_name: string };
export type Health = { status: string; database: string; ai_mode: 'demo' | 'live' | 'disabled' };
export type Appointment = { id: string; patient_id: string; patient_name: string; patient_age: number; patient_initials: string; scheduled_at: string; reason: string; status: string; encounter_id: string | null };
export type Evidence = { segment_id: string; quote: string; transcript_revision: number; source_text?: string };
export type Fact = { id: string; text: string; origin: 'manual' | 'ai' | 'doctor-edited'; evidence: Evidence[]; evidence_reviewed: boolean };
export type Section = 'symptoms' | 'history' | 'findings' | 'plan';
export type Note = Record<Section, Fact[]>;
export type ProposedTask = { id: string; description: string; due_date: string | null; assignee_id: string | null; evidence: Evidence[]; timing_text?: string | null };
export type Encounter = { id: string; appointment_id: string; patient_name: string; patient_age: number; reason: string; scheduled_at: string; status: 'draft' | 'approved'; transcript: string; transcript_revision: number; draft_revision: number; note: Note; proposed_tasks: ProposedTask[]; generation_status: string; approved_at: string | null; approved_by: string | null };
export type Generation = { id: string; note: Note; proposed_tasks: ProposedTask[]; transcript_revision: number; draft_revision: number; provider: string; created_at: string };
export type Task = { id: string; encounter_id: string; patient_name: string; description: string; due_date: string | null; assignee_id: string | null; assignee_name: string | null; status: 'open' | 'in_progress' | 'done'; created_at: string };
export type Audit = { id: string; action: string; actor_name: string; created_at: string; details: Record<string, unknown> };
export const sections: { key: Section; label: string; hint: string }[] = [
  { key: 'symptoms', label: 'Symptoms', hint: 'What the patient reports' },
  { key: 'history', label: 'Relevant history', hint: 'Relevant context from the visit' },
  { key: 'findings', label: 'Findings', hint: 'Documented clinical observations' },
  { key: 'plan', label: 'Stated plan', hint: 'Only the clinician’s documented plan' },
];
