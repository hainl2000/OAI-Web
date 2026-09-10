"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState, type FormEvent } from "react";

import { Empty, Notice, Score, SectionHead } from "@/components/ui";
import {
  api,
  ApiError,
  errorMessage,
  formatBytes,
  formatDateTime,
  json,
  type AdminCompetition,
  type GroundTruthPreview,
  type GroundTruthReplaceResult,
  type Ranking,
  type Registration,
} from "@/lib/api";
import { RequireRole } from "@/lib/auth";

const CONFIRM_WORD = "RESET";
const PAGE_SIZE = 25;

export default function AdminCompetitionPage() {
  return (
    <RequireRole role="admin">
      <CompetitionDetail />
    </RequireRole>
  );
}

function CompetitionDetail() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);

  const [competition, setCompetition] = useState<AdminCompetition | null>(null);
  const [registrations, setRegistrations] = useState<Registration[] | null>(null);
  const [ranking, setRanking] = useState<Ranking | null>(null);
  const [preview, setPreview] = useState<GroundTruthPreview | null>(null);
  const [page, setPage] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const loadCompetition = useCallback(async () => {
    const all = await api<AdminCompetition[]>("/api/v1/admin/competitions");
    const found = all.find((c) => c.id === id) ?? null;
    setCompetition(found);
    if (!found) setError("Không tìm thấy cuộc thi.");
    return found;
  }, [id]);

  const loadRegistrations = useCallback(async () => {
    setRegistrations(await api<Registration[]>(`/api/v1/admin/competitions/${id}/registrations`));
  }, [id]);

  const loadRanking = useCallback(async () => {
    setRanking(await api<Ranking>(`/api/v1/admin/competitions/${id}/ranking`));
  }, [id]);

  const loadPreview = useCallback(
    async (targetPage: number) => {
      try {
        setPreview(
          await api<GroundTruthPreview>(
            `/api/v1/admin/competitions/${id}/ground-truth?page=${targetPage}&page_size=${PAGE_SIZE}`,
          ),
        );
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          setPreview(null);
          return;
        }
        throw err;
      }
    },
    [id],
  );

  const loadAll = useCallback(async () => {
    try {
      const found = await loadCompetition();
      if (!found) return;
      await Promise.all([loadRegistrations(), loadRanking(), loadPreview(1)]);
      setPage(1);
      setError(null);
    } catch (err) {
      setError(errorMessage(err));
    }
  }, [loadCompetition, loadRegistrations, loadRanking, loadPreview]);

  useEffect(() => {
    if (Number.isFinite(id)) void loadAll();
  }, [id, loadAll]);

  async function changePage(next: number) {
    setPage(next);
    try {
      await loadPreview(next);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function toggleRanking() {
    if (!competition) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await api<AdminCompetition>(`/api/v1/admin/competitions/${id}`, {
        method: "PATCH",
        body: json({ ranking_published: !competition.ranking_published }),
      });
      setCompetition(updated);
      setRanking((prev) => (prev ? { ...prev, published: updated.ranking_published } : prev));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  if (!Number.isFinite(id)) return <Notice kind="error">Đường dẫn không hợp lệ.</Notice>;
  if (!competition) return error ? <Notice kind="error">{error}</Notice> : <p className="muted">Đang tải…</p>;

  const totalPages = preview ? Math.max(1, Math.ceil(preview.total / preview.page_size)) : 1;

  return (
    <>
      <div className="kicker">
        <Link href="/admin">Quản trị</Link> / Cuộc thi #{competition.id}
      </div>
      <h2 className="headline">{competition.name}</h2>
      <div className="stat-row">
        <div className="stat">
          <span className="kicker">Đáp án</span>
          <span className="stat-value">
            {competition.has_ground_truth ? `Phiên bản ${competition.ground_truth_version}` : "Chưa có"}
          </span>
        </div>
        <div className="stat">
          <span className="kicker">Thí sinh đăng ký</span>
          <span className="stat-value">{competition.registration_count}</span>
        </div>
        <div className="stat">
          <span className="kicker">Lượt nộp</span>
          <span className="stat-value">{competition.submission_count}</span>
        </div>
        <div className="stat">
          <span className="kicker">Bảng xếp hạng</span>
          <span className="stat-value">{competition.ranking_published ? "Công khai" : "Ẩn"}</span>
          <span>
            <button className="btn btn-sm" type="button" disabled={busy} onClick={toggleRanking}>
              {competition.ranking_published ? "Ẩn bảng xếp hạng" : "Công khai bảng xếp hạng"}
            </button>{" "}
            <Link className="btn btn-sm" href={`/ranking/${competition.id}`} target="_blank">
              Xem trang công khai
            </Link>
          </span>
        </div>
      </div>

      {error && <Notice kind="error">{error}</Notice>}

      <GroundTruthSection
        competition={competition}
        preview={preview}
        page={page}
        totalPages={totalPages}
        onPage={changePage}
        onReplaced={loadAll}
      />

      <section className="section">
        <SectionHead
          title="Thí sinh đăng ký"
          kicker={registrations ? `${registrations.length} thí sinh` : undefined}
        />
        {registrations === null ? (
          <p className="muted">Đang tải…</p>
        ) : registrations.length === 0 ? (
          <Empty>Chưa có thí sinh nào đăng ký.</Empty>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th className="num">#</th>
                  <th>Họ và tên</th>
                  <th>Email</th>
                  <th>Đăng ký lúc</th>
                  <th className="num">Lượt nộp</th>
                  <th className="num">Điểm tốt nhất</th>
                </tr>
              </thead>
              <tbody>
                {registrations.map((r, index) => (
                  <tr key={r.id}>
                    <td className="num">{index + 1}</td>
                    <td className="title-cell">{r.user.name}</td>
                    <td className="mono">{r.user.email ?? "—"}</td>
                    <td className="muted">{formatDateTime(r.created_at)}</td>
                    <td className="num">{r.submission_count}</td>
                    <td className="num">
                      <Score value={r.best_score} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="section">
        <SectionHead
          title="Bảng xếp hạng"
          kicker={ranking ? (ranking.published ? "Đang công khai" : "Chỉ quản trị viên xem được") : undefined}
        />
        {ranking === null ? (
          <p className="muted">Đang tải…</p>
        ) : ranking.entries.length === 0 ? (
          <Empty>Chưa có lượt nộp nào được chấm.</Empty>
        ) : (
          <RankingTable entries={ranking.entries} />
        )}
      </section>
    </>
  );
}

function GroundTruthSection({
  competition,
  preview,
  page,
  totalPages,
  onPage,
  onReplaced,
}: {
  competition: AdminCompetition;
  preview: GroundTruthPreview | null;
  page: number;
  totalPages: number;
  onPage: (page: number) => void;
  onReplaced: () => Promise<void>;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [inputKey, setInputKey] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [pendingReset, setPendingReset] = useState<number | null>(null);
  const [confirmText, setConfirmText] = useState("");

  function resetForm() {
    setFile(null);
    setInputKey((k) => k + 1);
    setPendingReset(null);
    setConfirmText("");
  }

  async function upload(confirm: boolean) {
    if (!file) return;
    setUploading(true);
    setUploadError(null);
    setSuccess(null);
    const form = new FormData();
    form.append("file", file);
    if (confirm) form.append("confirm_reset", "true");
    try {
      const result = await api<GroundTruthReplaceResult>(`/api/v1/admin/competitions/${competition.id}/ground-truth`, {
        method: "PUT",
        body: form,
      });
      setSuccess(
        `Đã cập nhật đáp án phiên bản ${result.ground_truth_version} (${result.metadata.row_count} dòng).` +
          (result.submissions_deleted > 0 ? ` Đã xoá ${result.submissions_deleted} lượt nộp cũ.` : ""),
      );
      resetForm();
      await onReplaced();
    } catch (err) {
      if (err instanceof ApiError && err.code === "score_reset_confirmation_required") {
        setPendingReset(Number(err.detail.submissions_to_delete ?? 0));
        setConfirmText("");
      } else {
        setUploadError(errorMessage(err));
      }
    } finally {
      setUploading(false);
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    void upload(false);
  }

  return (
    <section className="section">
      <SectionHead
        title="Đáp án (ground truth)"
        kicker="Mỗi cuộc thi có đúng một file đáp án đang hoạt động"
        aside={
          competition.has_ground_truth ? (
            <a className="btn btn-sm" href={`/api/v1/admin/competitions/${competition.id}/ground-truth/download`}>
              Tải file gốc
            </a>
          ) : null
        }
      />

      <div className="columns">
        <div>
          {preview ? (
            <dl className="meta">
              <dt>Tên file</dt>
              <dd className="mono">{preview.metadata.filename}</dd>
              <dt>Phiên bản</dt>
              <dd>{preview.metadata.version}</dd>
              <dt>Số dòng</dt>
              <dd>{preview.metadata.row_count.toLocaleString("vi-VN")}</dd>
              <dt>Kích thước</dt>
              <dd>{formatBytes(preview.metadata.size_bytes)}</dd>
              <dt>SHA-256</dt>
              <dd className="mono" style={{ wordBreak: "break-all" }}>
                {preview.metadata.checksum_sha256}
              </dd>
              <dt>Tải lên lúc</dt>
              <dd>{formatDateTime(preview.metadata.uploaded_at)}</dd>
            </dl>
          ) : (
            <Empty>Chưa có đáp án. Thí sinh chưa thể nộp bài cho tới khi đáp án được tải lên.</Empty>
          )}

          <form className="form" onSubmit={handleSubmit}>
            <div className="field">
              <label htmlFor="gt-file">{competition.has_ground_truth ? "Thay đáp án (CSV uuid,is_spoof)" : "Tải đáp án (CSV uuid,is_spoof)"}</label>
              <input
                key={inputKey}
                id="gt-file"
                type="file"
                accept=".csv,text/csv"
                onChange={(e) => {
                  setFile(e.target.files?.[0] ?? null);
                  setPendingReset(null);
                  setSuccess(null);
                  setUploadError(null);
                }}
              />
              <span className="muted">UTF-8, tối đa 5 MB và 50.000 dòng. Cột uuid không trùng, is_spoof là TRUE/FALSE.</span>
            </div>

            {pendingReset !== null ? (
              <Notice kind="warning">
                <strong>Cảnh báo:</strong> cuộc thi đã có <strong>{pendingReset}</strong> lượt nộp. Thay đáp án sẽ xoá toàn bộ
                điểm và lịch sử nộp bài của mọi thí sinh (danh sách đăng ký và trạng thái bảng xếp hạng được giữ nguyên). Số lượt
                nộp sẽ bắt đầu lại từ 1.
                <div className="form-row" style={{ marginTop: 10 }}>
                  <div className="field">
                    <label htmlFor="confirm-reset">Nhập {CONFIRM_WORD} để xác nhận</label>
                    <input
                      id="confirm-reset"
                      type="text"
                      autoComplete="off"
                      value={confirmText}
                      onChange={(e) => setConfirmText(e.target.value)}
                    />
                  </div>
                  <button
                    className="btn btn-danger"
                    type="button"
                    disabled={uploading || confirmText.trim().toUpperCase() !== CONFIRM_WORD}
                    onClick={() => upload(true)}
                  >
                    {uploading ? "Đang thay…" : `Xoá ${pendingReset} lượt nộp và thay đáp án`}
                  </button>
                  <button className="btn" type="button" onClick={resetForm} disabled={uploading}>
                    Huỷ
                  </button>
                </div>
              </Notice>
            ) : (
              <div className="form-row">
                <button className="btn btn-primary" type="submit" disabled={!file || uploading}>
                  {uploading ? "Đang kiểm tra…" : competition.has_ground_truth ? "Thay đáp án" : "Tải đáp án"}
                </button>
              </div>
            )}
            {uploadError && <Notice kind="error">{uploadError}</Notice>}
            {success && <Notice kind="success">{success}</Notice>}
          </form>
        </div>

        <div>
          {preview && (
            <>
              <div className="kicker">Xem trước đáp án · {preview.total.toLocaleString("vi-VN")} dòng</div>
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th className="num">#</th>
                      <th>uuid</th>
                      <th>is_spoof</th>
                    </tr>
                  </thead>
                  <tbody>
                    {preview.items.map((row, index) => (
                      <tr key={row.uuid}>
                        <td className="num muted">{(preview.page - 1) * preview.page_size + index + 1}</td>
                        <td className="mono">{row.uuid}</td>
                        <td>{row.is_spoof ? "TRUE" : "FALSE"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="pager">
                <button className="btn btn-sm" type="button" disabled={page <= 1} onClick={() => onPage(page - 1)}>
                  ‹ Trước
                </button>
                <span className="kicker">
                  Trang {page} / {totalPages}
                </span>
                <button className="btn btn-sm" type="button" disabled={page >= totalPages} onClick={() => onPage(page + 1)}>
                  Sau ›
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </section>
  );
}

function RankingTable({ entries }: { entries: Ranking["entries"] }) {
  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            <th className="num">Hạng</th>
            <th>Họ và tên</th>
            <th className="num">Điểm tốt nhất (F1-macro)</th>
            <th className="num">Số lượt nộp</th>
            <th>Thời gian đạt điểm tốt nhất</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((e) => (
            <tr key={e.user_id}>
              <td className="num rank">{e.rank}</td>
              <td className="title-cell">{e.name}</td>
              <td className="num">
                <Score value={e.best_score} />
              </td>
              <td className="num">{e.submission_count}</td>
              <td className="muted">{formatDateTime(e.best_submitted_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
