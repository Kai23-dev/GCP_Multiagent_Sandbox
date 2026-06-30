import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Spend Intelligence Console | EY GDS SCO",
  description: "Supplier Cost Optimisation — Multi-Agent Sandbox on Google Cloud Vertex AI",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body style={{ fontFamily: '"Segoe UI", Arial, sans-serif', margin: 0, padding: 0 }}>
        {children}
      </body>
    </html>
  );
}
