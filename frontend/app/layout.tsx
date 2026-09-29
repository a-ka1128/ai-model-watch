import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Model Watch",
  description: "Evidence-backed weekly intelligence for AI models and tools",
  icons: { icon: "/icon.svg" }
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="ko"><body>{children}</body></html>;
}
