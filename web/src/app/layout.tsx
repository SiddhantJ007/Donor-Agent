import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CSAF | Prospect workspace",
  description: "Organization discovery, prospect context, and campaign learning for CSAF.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
