import type { Metadata } from "next";
import "./globals.css";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { PrototypeBanner } from "@/components/layout/PrototypeBanner";

export const metadata: Metadata = {
  title: "StainShift — Histopathology Stain Domain Shift Benchmark",
  description:
    "Scientific AI benchmark & inference platform evaluating deep neural network robustness under Hematoxylin and Eosin stain variations.",
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
    <html lang="en" className="bg-[#FAF8F5]">
      <body className="min-h-screen flex flex-col bg-[#FAF8F5] text-charcoal-900 selection:bg-terracotta-100 selection:text-terracotta-900 antialiased">
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
