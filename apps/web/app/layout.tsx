import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Resonant | Explainable AI career matching",
  description: "Find Singapore job matches and repeated skill gaps grounded in your resume.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
