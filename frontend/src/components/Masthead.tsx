"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { homeFor, useAuth } from "@/lib/auth";

export function Masthead() {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  const today = new Date().toLocaleDateString("vi-VN", {
    weekday: "long",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });

  async function handleLogout() {
    await logout();
    router.replace("/login");
  }

  const navLinks = user
    ? user.role === "admin"
      ? [{ href: "/admin", label: "Quản trị cuộc thi" }]
      : [{ href: "/competitions", label: "Cuộc thi của tôi" }]
    : [
        { href: "/login", label: "Đăng nhập" },
        { href: "/signup", label: "Đăng ký thí sinh" },
      ];

  return (
    <header className="masthead">
      <div className="masthead-top">
        <span className="kicker">{today}</span>
        <span className="kicker">
          {loading ? "…" : user ? (
            <>
              {user.role === "admin" ? "Quản trị viên" : "Thí sinh"} · <strong>{user.name}</strong> ·{" "}
              <button type="button" className="linklike" onClick={handleLogout}>
                Đăng xuất
              </button>
            </>
          ) : (
            "Khách"
          )}
        </span>
      </div>
      <h1 className="masthead-title">
        <Link href={homeFor(user)}>OlympicAI Scoring</Link>
      </h1>
      <p className="masthead-sub">Hệ thống chấm điểm F1-macro cho bài toán phát hiện giả mạo</p>
      <nav className="masthead-nav">
        {navLinks.map((link) => (
          <Link key={link.href} href={link.href} className={pathname.startsWith(link.href) ? "active" : ""}>
            {link.label}
          </Link>
        ))}
      </nav>
    </header>
  );
}
