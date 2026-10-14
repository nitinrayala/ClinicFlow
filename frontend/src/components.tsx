import { useEffect, useRef, type ReactNode } from 'react';
import { AlertCircle, Check, LoaderCircle, X, Plus } from 'lucide-react';

export function Brand({ light = false }: { light?: boolean }) {
  return <div className={`brand ${light ? 'brand-light' : ''}`}><span className="brand-symbol"><Plus size={27} strokeWidth={3} /></span><span>Clinic<span className="brand-flow">Flow</span><small>THOUGHTFUL CARE, CONNECTED</small></span></div>;
}
export function Spinner({ label = 'Loading…' }: { label?: string }) { return <div className="loading" role="status"><LoaderCircle className="spin" size={22} />{label}</div>; }
export function ErrorNotice({ message, children }: { message: string; children?: ReactNode }) { return <div className="notice error" role="alert"><AlertCircle size={20} /><div>{message}{children}</div></div>; }
export function Success({ children }: { children: ReactNode }) { return <div className="notice success" role="status"><Check size={19} /><div>{children}</div></div>; }
export function Badge({ status }: { status: string }) {
  const label: Record<string, string> = { draft: 'In review', scheduled: 'Scheduled', approved: 'Approved', completed: 'Approved', open: 'Open', in_progress: 'In progress', done: 'Completed', checked_in: 'Checked in' };
  return <span className={`badge badge-${status}`}><span className="status-dot" />{label[status] || status.replaceAll('_', ' ')}</span>;
}
export function Modal({ title, children, onClose, wide = false }: { title: string; children: ReactNode; onClose: () => void; wide?: boolean }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => { const el = ref.current!; el.showModal(); return () => el.close(); }, []);
  return <dialog ref={ref} className={wide ? 'modal modal-wide' : 'modal'} aria-labelledby="modal-title" onCancel={(e) => { e.preventDefault(); onClose(); }}>
    <div className="modal-heading"><h2 id="modal-title">{title}</h2><button type="button" className="icon-button" onClick={onClose} aria-label="Close dialog"><X size={20} /></button></div>{children}
  </dialog>;
}
export function EmptyState({ title, detail, children }: { title: string; detail: string; children?: ReactNode }) { return <div className="empty-state"><div className="empty-icon"><Check size={28} /></div><h3>{title}</h3><p>{detail}</p>{children}</div>; }
export const dateLabel = (iso: string) => new Date(iso).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
export const timeLabel = (iso: string) => new Date(iso).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
