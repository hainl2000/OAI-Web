import type { Metadata } from "next";
import type { ReactNode } from "react";

import { Masthead } from "@/components/Masthead";
import { AuthProvider } from "@/lib/auth";

import "./globals.css";

export const metadata: Metadata = {
  title: "OlympicAI Scoring",
  description: "Hệ thống chấm điểm F1-macro cho các cuộc thi OlympicAI",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="vi">
      <body>
        <AuthProvider>
          <div className="page">
            <Masthead />
            <main>{children}</main>
          </div>
        </AuthProvider>
      </body>
    </html>
  );
}
