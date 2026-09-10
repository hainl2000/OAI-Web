"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { homeFor, useAuth } from "@/lib/auth";

export default function IndexPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading) router.replace(homeFor(user));
  }, [loading, user, router]);

  return <p className="muted">Đang chuyển hướng…</p>;
}
