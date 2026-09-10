"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Empty, Notice, SectionHead } from "@/components/ui";
import { api, errorMessage, formatDateTime, type CandidateCompetition, type CompetitionList } from "@/lib/api";
import { RequireRole } from "@/lib/auth";

export default function CandidateHomePage() {
  return (
    <RequireRole role="candidate">
      <CandidateHome />
    </RequireRole>
  );
}

function CandidateHome() {
  const [data, setData] = useState<CompetitionList | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  const load = useCallback(async () => {
    try {
      setData(await api<CompetitionList>("/api/v1/competitions"));
      setError(null);
    } catch (err) {
      setError(errorMessage(err));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function register(c: CandidateCompetition) {
    setBusyId(c.id);
    setError(null);
    try {
      await api(`/api/v1/competitions/${c.id}/registration`, { method: "PUT" });
      await load();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <>
      <div className="kicker">Thí sinh</div>
      <h2 className="headline">Cuộc thi</h2>
      <p className="deck">Đăng ký cuộc thi để nộp file dự đoán và theo dõi điểm F1-macro của bạn.</p>
      {error && <Notice kind="error">{error}</Notice>}

      {data === null ? (
        <p className="muted">Đang tải…</p>
      ) : (
        <div className="columns">
          <section className="section">
            <SectionHead title="Đã đăng ký" kicker={`${data.registered.length} cuộc thi`} />
            {data.registered.length === 0 ? (
              <Empty>Bạn chưa đăng ký cuộc thi nào.</Empty>
            ) : (
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Cuộc thi</th>
                      <th>Trạng thái</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.registered.map((c) => (
                      <tr key={c.id}>
                        <td className="title-cell">
                          <Link href={`/competitions/${c.id}`}>{c.name}</Link>
                          <div className="muted" style={{ fontFamily: "var(--sans)", fontSize: 12, fontWeight: 400 }}>
                            Đăng ký lúc {formatDateTime(c.registered_at)}
                          </div>
                        </td>
                        <td>
                          <StatusBadges c={c} />
                        </td>
                        <td className="actions">
                          <Link className="btn btn-sm btn-primary" href={`/competitions/${c.id}`}>
                            Nộp bài
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="section">
            <SectionHead title="Chưa đăng ký" kicker={`${data.unregistered.length} cuộc thi`} />
            {data.unregistered.length === 0 ? (
              <Empty>Không còn cuộc thi nào để đăng ký.</Empty>
            ) : (
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Cuộc thi</th>
                      <th>Trạng thái</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.unregistered.map((c) => (
                      <tr key={c.id}>
                        <td className="title-cell">{c.name}</td>
                        <td>
                          <StatusBadges c={c} />
                        </td>
                        <td className="actions">
                          <button className="btn btn-sm" type="button" disabled={busyId === c.id} onClick={() => register(c)}>
                            {busyId === c.id ? "Đang đăng ký…" : "Đăng ký"}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>
      )}
    </>
  );
}

function StatusBadges({ c }: { c: CandidateCompetition }) {
  return (
    <span style={{ display: "inline-flex", gap: 6, flexWrap: "wrap" }}>
      <span className={`badge ${c.has_ground_truth ? "" : "badge-muted"}`}>
        {c.has_ground_truth ? "Đang nhận bài" : "Chưa có đáp án"}
      </span>
      {c.ranking_published && (
        <Link className="badge" href={`/ranking/${c.id}`} style={{ textDecoration: "none" }}>
          Bảng xếp hạng
        </Link>
      )}
    </span>
  );
}
