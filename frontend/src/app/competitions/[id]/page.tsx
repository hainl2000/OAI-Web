"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState, type FormEvent } from "react";

import { Empty, Notice, Score, SectionHead } from "@/components/ui";
import {
  api,
  ApiError,
  errorMessage,
  formatDateTime,
  type CandidateCompetitionDetail,
  type Submission,
} from "@/lib/api";
import { RequireRole } from "@/lib/auth";

export default function CandidateCompetitionPage() {
  return (
    <RequireRole role="candidate">
      <CompetitionUpload />
    </RequireRole>
  );
}

function CompetitionUpload() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);

  const [competition, setCompetition] = useState<CandidateCompetitionDetail | null>(null);
  const [history, setHistory] = useState<Submission[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [inputKey, setInputKey] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<{ message: string; details?: string[] } | null>(null);
  const [lastResult, setLastResult] = useState<Submission | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const detail = await api<CandidateCompetitionDetail>(`/api/v1/competitions/${id}`);
      setCompetition(detail);
      setHistory(detail.registered ? await api<Submission[]>(`/api/v1/competitions/${id}/submissions/me`) : []);
      setError(null);
    } catch (err) {
      setError(errorMessage(err));
    }
  }, [id]);

  useEffect(() => {
    if (Number.isFinite(id)) void load();
  }, [id, load]);

  async function register() {
    setBusy(true);
    setError(null);
    try {
      await api(`/api/v1/competitions/${id}/registration`, { method: "PUT" });
      await load();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    setUploading(true);
    setUploadError(null);
    setLastResult(null);
    const form = new FormData();
    form.append("file", file);
    try {
      const result = await api<Submission>(`/api/v1/competitions/${id}/submissions`, { method: "POST", body: form });
      setLastResult(result);
      setFile(null);
      setInputKey((k) => k + 1);
      await load();
    } catch (err) {
      if (err instanceof ApiError && err.code === "uuid_set_mismatch") {
        const missing = Number(err.detail.missing_count ?? 0);
        const extra = Number(err.detail.extra_count ?? 0);
        const samples: string[] = [];
        if (Array.isArray(err.detail.missing_sample) && err.detail.missing_sample.length) {
          samples.push(`Thiếu (${missing}): ${(err.detail.missing_sample as string[]).join(", ")}${missing > 10 ? ", …" : ""}`);
        }
        if (Array.isArray(err.detail.extra_sample) && err.detail.extra_sample.length) {
          samples.push(`Thừa (${extra}): ${(err.detail.extra_sample as string[]).join(", ")}${extra > 10 ? ", …" : ""}`);
        }
        setUploadError({ message: err.message, details: samples });
      } else {
        setUploadError({ message: errorMessage(err) });
      }
    } finally {
      setUploading(false);
    }
  }

  if (!Number.isFinite(id)) return <Notice kind="error">Đường dẫn không hợp lệ.</Notice>;
  if (!competition) return error ? <Notice kind="error">{error}</Notice> : <p className="muted">Đang tải…</p>;

  const canSubmit = competition.registered && competition.has_ground_truth;

  return (
    <>
      <div className="kicker">
        <Link href="/competitions">Cuộc thi</Link> / #{competition.id}
      </div>
      <h2 className="headline">{competition.name}</h2>
      <div className="stat-row">
        <div className="stat">
          <span className="kicker">Trạng thái</span>
          <span className="stat-value">
            {!competition.registered ? "Chưa đăng ký" : competition.has_ground_truth ? "Đang nhận bài" : "Chưa có đáp án"}
          </span>
        </div>
        <div className="stat">
          <span className="kicker">Số lượt đã nộp</span>
          <span className="stat-value">{competition.my_submission_count}</span>
        </div>
        <div className="stat">
          <span className="kicker">Điểm tốt nhất</span>
          <span className="stat-value">
            <Score value={competition.best_score} />
          </span>
        </div>
        <div className="stat">
          <span className="kicker">Bảng xếp hạng</span>
          <span className="stat-value">{competition.ranking_published ? "Công khai" : "Chưa công khai"}</span>
          {competition.ranking_published && (
            <Link className="btn btn-sm" href={`/ranking/${competition.id}`}>
              Xem bảng xếp hạng
            </Link>
          )}
        </div>
      </div>

      {error && <Notice kind="error">{error}</Notice>}

      {!competition.registered && (
        <Notice kind="info">
          Bạn chưa đăng ký cuộc thi này.{" "}
          <button className="btn btn-sm btn-primary" type="button" disabled={busy} onClick={register}>
            {busy ? "Đang đăng ký…" : "Đăng ký ngay"}
          </button>
        </Notice>
      )}

      <section className="section">
        <SectionHead title="Nộp file dự đoán" kicker="Không giới hạn số lượt nộp" />
        {!competition.has_ground_truth && competition.registered && (
          <Notice kind="info">Ban tổ chức chưa tải đáp án. Bạn có thể nộp bài sau khi đáp án được cập nhật.</Notice>
        )}
        <form className="form" onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="pred-file">File CSV (uuid,is_spoof)</label>
            <input
              key={inputKey}
              id="pred-file"
              type="file"
              accept=".csv,text/csv"
              disabled={!canSubmit}
              onChange={(e) => {
                setFile(e.target.files?.[0] ?? null);
                setUploadError(null);
                setLastResult(null);
              }}
            />
            <span className="muted">
              UTF-8, tối đa 5 MB và 50.000 dòng. Tập uuid phải khớp chính xác với đáp án; is_spoof là TRUE (spoof) hoặc FALSE
              (live). File của bạn chỉ được dùng để chấm điểm và không được lưu lại.
            </span>
          </div>
          <div className="form-row">
            <button className="btn btn-primary" type="submit" disabled={!canSubmit || !file || uploading}>
              {uploading ? "Đang chấm…" : "Nộp và chấm điểm"}
            </button>
          </div>
        </form>
        {uploadError && (
          <Notice kind="error">
            <div>{uploadError.message} Lượt nộp không được ghi nhận.</div>
            {uploadError.details?.map((line) => (
              <div key={line} className="mono" style={{ marginTop: 4, wordBreak: "break-all" }}>
                {line}
              </div>
            ))}
          </Notice>
        )}
        {lastResult && (
          <Notice kind="success">
            Lượt #{lastResult.attempt_number} đã được chấm: F1-macro = <Score value={lastResult.score} /> (
            {formatDateTime(lastResult.submitted_at)}).
          </Notice>
        )}
      </section>

      <section className="section">
        <SectionHead title="Lịch sử điểm của tôi" kicker={history ? `${history.length} lượt` : undefined} />
        {history === null ? (
          <p className="muted">Đang tải…</p>
        ) : history.length === 0 ? (
          <Empty>Chưa có lượt nộp nào. Lịch sử sẽ được làm mới nếu ban tổ chức thay đáp án.</Empty>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th className="num">Lượt</th>
                  <th className="num">F1-macro</th>
                  <th>Thời gian nộp</th>
                  <th className="num">Phiên bản đáp án</th>
                </tr>
              </thead>
              <tbody>
                {history.map((s) => (
                  <tr key={s.id}>
                    <td className="num rank">{s.attempt_number}</td>
                    <td className="num">
                      <Score value={s.score} />
                      {competition.best_score === s.score && <span className="badge" style={{ marginLeft: 8 }}>Tốt nhất</span>}
                    </td>
                    <td className="muted">{formatDateTime(s.submitted_at)}</td>
                    <td className="num">{s.ground_truth_version}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
