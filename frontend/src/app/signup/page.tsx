"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { Notice } from "@/components/ui";
import { api, errorMessage, json, type User } from "@/lib/api";
import { homeFor, useAuth } from "@/lib/auth";

export default function SignupPage() {
  const { user, loading, setUser } = useAuth();
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!loading && user) router.replace(homeFor(user));
  }, [loading, user, router]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const me = await api<User>("/api/v1/auth/signup", {
        method: "POST",
        body: json({ name: name.trim(), email: email.trim(), password }),
      });
      setUser(me);
      router.replace(homeFor(me));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="auth-card">
      <div className="kicker">Tài khoản thí sinh</div>
      <h2>Đăng ký</h2>
      <p className="deck">Họ tên đầy đủ sẽ được hiển thị trên bảng xếp hạng khi cuộc thi công khai kết quả.</p>
      <form className="form" onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="name">Họ và tên</label>
          <input id="name" type="text" required maxLength={200} value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="email">Email</label>
          <input id="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="password">Mật khẩu (tối thiểu 8 ký tự)</label>
          <input
            id="password"
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        {error && <Notice kind="error">{error}</Notice>}
        <div className="form-row">
          <button className="btn btn-primary" type="submit" disabled={busy}>
            {busy ? "Đang tạo tài khoản…" : "Tạo tài khoản"}
          </button>
          <span className="muted">
            Đã có tài khoản? <Link href="/login">Đăng nhập</Link>
          </span>
        </div>
      </form>
    </section>
  );
}
