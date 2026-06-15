import type { Metadata } from "next";
import "./globals.css";
import NavLinks from "@/components/NavLinks";

export const metadata: Metadata = {
  title: "Agent Trace Viewer",
  description: "Distributed trace viewer for SCO Agent Engine",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen">
        <header className="bg-brand-900 text-white px-6 py-3 flex items-center gap-6 shadow-md">
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-semibold tracking-tight">Agent Trace Viewer</h1>
            <span className="text-xs bg-brand-700 px-2 py-0.5 rounded">SCO Agents</span>
          </div>
          <NavLinks />
        </header>
        <main className="max-w-[1600px] mx-auto p-6">{children}</main>
      </body>
    </html>
  );
}
