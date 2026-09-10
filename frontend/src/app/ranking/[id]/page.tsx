"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { Empty, Notice, Score } from "@/components/ui";
import { api, errorMessage, formatDateTime, type Ranking } from "@/lib/api";

export default function PublicRankingPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const [ranking, setRanking] = useState<Ranking | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!Number.isFinite(id)) return;
    api<Ranking>(`/api/v1/public/competitions/${id}/ranking`)
      .then(setRanking)
      .catch((err) => setError(errorMessage(err)));
  }, [id]);

  if (!Number.isFinite(id)) return <Notice kind="error">Đường dẫn không hợp lệ.</Notice>;
  if (error) return <Notice kind="error">{error}</Notice>;
  if (!ranking) return <p className="muted">Đang tải…</p>;

  return (
    <>
      <div className="kicker">Bảng xếp hạng công khai</div>
      <h2 className="headline">{ranking.competition_name}</h2>
      <p className="deck">
        Xếp hạng theo điểm F1-macro tốt nhất của mỗi thí sinh. Bằng điểm thì lượt đạt điểm sớm hơn đứng trước.
      </p>

      {!ranking.published ? (
        <Empty>Bảng xếp hạng chưa được ban tổ chức công khai.</Empty>
      ) : ranking.entries.length === 0 ? (
        <Empty>Chưa có lượt nộp nào được ghi nhận.</Empty>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th className="num">Hạng</th>
                <th>Họ và tên</th>
                <th className="num">Điểm tốt nhất</th>
                <th className="num">Số lượt nộp</th>
                <th>Thời gian đạt điểm tốt nhất</th>
              </tr>
            </thead>
            <tbody>
              {ranking.entries.map((e) => (
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
      )}
      <p className="muted" style={{ marginTop: 24 }}>
        <Link href="/">← Về trang chủ</Link>
      </p>
    </>
  );
}
