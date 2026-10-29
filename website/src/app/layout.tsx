import type { Metadata } from "next";
import "./globals.css";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { PrototypeBanner } from "@/components/layout/PrototypeBanner";

export const metadata: Metadata = {
  title: "StainShift — Histopathology Stain Domain Shift Benchmark",
  description:
    "Scientific benchmark of deep neural network robustness under Hematoxylin and Eosin stain shifts on colorectal tissue.",
  icons: {
    icon: "/favicon.ico",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen flex flex-col bg-slate-50 text-slate-900">
        <PrototypeBanner />
        <Navbar />
        <main className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 md:py-12">
          {children}
        </main>
        <Footer />
      </body>
    </html>
  );
}
