"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { Notice } from "@/components/ui";
import { api, errorMessage, json, type User } from "@/lib/api";
import { homeFor, useAuth } from "@/lib/auth";

export default function LoginPage() {
  const { user, loading, setUser } = useAuth();
  const router = useRouter();
  const [identifier, setIdentifier] = useState("");
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
      const me = await api<User>("/api/v1/auth/login", {
        method: "POST",
        body: json({ identifier: identifier.trim(), password }),
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
      <div className="kicker">Tài khoản</div>
      <h2>Đăng nhập</h2>
      <p className="deck">Thí sinh đăng nhập bằng email. Quản trị viên đăng nhập bằng tên đăng nhập.</p>
      <form className="form" onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="identifier">Email hoặc tên đăng nhập</label>
          <input
            id="identifier"
            type="text"
            autoComplete="username"
            required
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="password">Mật khẩu</label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        {error && <Notice kind="error">{error}</Notice>}
        <div className="form-row">
          <button className="btn btn-primary" type="submit" disabled={busy}>
            {busy ? "Đang đăng nhập…" : "Đăng nhập"}
          </button>
          <span className="muted">
            Chưa có tài khoản? <Link href="/signup">Đăng ký thí sinh</Link>
          </span>
        </div>
      </form>
    </section>
  );
}
