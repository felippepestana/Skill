import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "APEX-LEGAL PERFORMANCE",
  description: "Workspace jurídico multi-agente com IA",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <body className="bg-gray-950 text-gray-100 antialiased">{children}</body>
    </html>
  );
}
