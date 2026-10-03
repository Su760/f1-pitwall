import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PitWall Arena — Make the call",
  description:
    "A playable, deterministic pit-strategy arena. Three synthetic situations. One decision at a time.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
