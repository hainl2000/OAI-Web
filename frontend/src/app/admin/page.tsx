"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, type FormEvent } from "react";

import { Empty, Notice, SectionHead } from "@/components/ui";
import { api, errorMessage, formatDateTime, json, type AdminCompetition } from "@/lib/api";
import { RequireRole } from "@/lib/auth";

export default function AdminPage() {
  return (
    <RequireRole role="admin">
      <AdminCompetitions />
    </RequireRole>
  );
}

function AdminCompetitions() {
  const [items, setItems] = useState<AdminCompetition[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingName, setEditingName] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);

  const load = useCallback(async () => {
    try {
      setItems(await api<AdminCompetition[]>("/api/v1/admin/competitions"));
      setError(null);
    } catch (err) {
      setError(errorMessage(err));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  function replaceItem(updated: AdminCompetition) {
    setItems((prev) => (prev ? prev.map((c) => (c.id === updated.id ? updated : c)) : prev));
  }

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    if (!newName.trim()) return;
    setCreating(true);
    setError(null);
    try {
      const created = await api<AdminCompetition>("/api/v1/admin/competitions", {
        method: "POST",
        body: json({ name: newName.trim() }),
      });
      setItems((prev) => [created, ...(prev ?? [])]);
      setNewName("");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setCreating(false);
    }
  }

  function startEdit(c: AdminCompetition) {
    setEditingId(c.id);
    setEditingName(c.name);
  }

  async function saveEdit(c: AdminCompetition) {
    const name = editingName.trim();
    if (!name || name === c.name) {
      setEditingId(null);
      return;
    }
    setBusyId(c.id);
    setError(null);
    try {
      replaceItem(
        await api<AdminCompetition>(`/api/v1/admin/competitions/${c.id}`, {
          method: "PATCH",
          body: json({ name }),
        }),
      );
      setEditingId(null);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusyId(null);
    }
  }

  async function toggleRanking(c: AdminCompetition) {
    setBusyId(c.id);
    setError(null);
    try {
      replaceItem(
        await api<AdminCompetition>(`/api/v1/admin/competitions/${c.id}`, {
          method: "PATCH",
          body: json({ ranking_published: !c.ranking_published }),
        }),
      );
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <>
      <div className="kicker">Quản trị</div>
      <h2 className="headline">Danh sách cuộc thi</h2>
      <p className="deck">Tạo cuộc thi, đổi tên trực tiếp trong bảng và bật/tắt công khai bảng xếp hạng.</p>

      <form className="form-row" onSubmit={handleCreate}>
        <div className="field" style={{ flex: 1, minWidth: 240 }}>
          <label htmlFor="new-name">Tên cuộc thi mới</label>
          <input
            id="new-name"
            type="text"
            maxLength={200}
            placeholder="Ví dụ: Vòng loại OlympicAI 2026"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
          />
        </div>
        <button className="btn btn-primary" type="submit" disabled={creating || !newName.trim()}>
          {creating ? "Đang tạo…" : "Tạo cuộc thi"}
        </button>
      </form>

      {error && <Notice kind="error">{error}</Notice>}

      <section className="section">
        <SectionHead title="Cuộc thi" kicker={items ? `${items.length} cuộc thi` : undefined} />
        {items === null ? (
          <p className="muted">Đang tải…</p>
        ) : items.length === 0 ? (
          <Empty>Chưa có cuộc thi nào. Hãy tạo cuộc thi đầu tiên ở trên.</Empty>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Tên cuộc thi</th>
                  <th>Đáp án</th>
                  <th className="num">Đăng ký</th>
                  <th className="num">Lượt nộp</th>
                  <th>Bảng xếp hạng</th>
                  <th>Tạo lúc</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {items.map((c) => (
                  <tr key={c.id}>
                    <td className="title-cell">
                      {editingId === c.id ? (
                        <form
                          className="inline-edit"
                          onSubmit={(e) => {
                            e.preventDefault();
                            void saveEdit(c);
                          }}
                        >
                          <input
                            className="inline-input"
                            autoFocus
                            maxLength={200}
                            value={editingName}
                            onChange={(e) => setEditingName(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === "Escape") setEditingId(null);
                            }}
                          />
                          <button className="btn btn-sm btn-primary" type="submit" disabled={busyId === c.id}>
                            Lưu
                          </button>
                          <button className="btn btn-sm" type="button" onClick={() => setEditingId(null)}>
                            Huỷ
                          </button>
                        </form>
                      ) : (
                        <div className="inline-edit">
                          <Link href={`/admin/competitions/${c.id}`}>{c.name}</Link>
                          <button className="linklike kicker" type="button" onClick={() => startEdit(c)} title="Đổi tên">
                            Sửa
                          </button>
                        </div>
                      )}
                    </td>
                    <td>
                      {c.has_ground_truth ? (
                        <span className="badge">Phiên bản {c.ground_truth_version}</span>
                      ) : (
                        <span className="badge badge-muted">Chưa có</span>
                      )}
                    </td>
                    <td className="num">{c.registration_count}</td>
                    <td className="num">{c.submission_count}</td>
                    <td>
                      <span className={`badge ${c.ranking_published ? "" : "badge-muted"}`}>
                        {c.ranking_published ? "Công khai" : "Ẩn"}
                      </span>{" "}
                      <button
                        className="btn btn-sm"
                        type="button"
                        disabled={busyId === c.id}
                        onClick={() => toggleRanking(c)}
                      >
                        {c.ranking_published ? "Ẩn đi" : "Công khai"}
                      </button>
                    </td>
                    <td className="muted">{formatDateTime(c.created_at)}</td>
                    <td className="actions">
                      <Link className="btn btn-sm" href={`/admin/competitions/${c.id}`}>
                        Chi tiết
                      </Link>
                    </td>
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
