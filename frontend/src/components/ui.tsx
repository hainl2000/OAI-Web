import type { ReactNode } from "react";

export function Notice({ kind = "info", children }: { kind?: "info" | "error" | "success" | "warning"; children: ReactNode }) {
  return <div className={`notice notice-${kind}`}>{children}</div>;
}

export function SectionHead({ title, kicker, aside }: { title: string; kicker?: string; aside?: ReactNode }) {
  return (
    <div className="section-head">
      <div>
        {kicker && <div className="kicker">{kicker}</div>}
        <h2>{title}</h2>
      </div>
      {aside && <div className="section-aside">{aside}</div>}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="empty">{children}</p>;
}

export function Score({ value }: { value: string | null | undefined }) {
  return <span className="score">{value ?? "—"}</span>;
}
