"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Sparkles, BarChart3, Eye, Menu, X, Microscope, ExternalLink } from "lucide-react";

const NAV_ITEMS = [
  { name: "AI Workspace", href: "/", icon: Sparkles },
  { name: "Results Dashboard", href: "/dashboard/", icon: BarChart3 },
  { name: "Demo Explorer", href: "/demo/", icon: Eye },
];

export function Navbar() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 bg-[#FAF8F5]/90 backdrop-blur-md border-b border-[#E8E4DD]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo / Brand */}
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center gap-2.5 group">
              <div className="w-8 h-8 rounded-full bg-[#CC785C] flex items-center justify-center text-white shadow-sm group-hover:bg-[#B96449] transition">
                <Microscope className="w-4 h-4 text-white" />
              </div>
              <span className="font-serif text-xl font-medium tracking-tight text-charcoal-900 group-hover:text-charcoal-700 transition">
                StainShift
              </span>
            </Link>
          </div>

          {/* Desktop Navigation Links */}
          <nav className="hidden md:flex items-center space-x-1" aria-label="Main Navigation">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const isActive =
                pathname === item.href ||
                (item.href !== "/" && pathname?.startsWith(item.href));
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-medium transition ${
                    isActive
                      ? "bg-[#EDE7DE] text-charcoal-900 font-semibold"
                      : "text-charcoal-500 hover:text-charcoal-900 hover:bg-[#F3EFEA]"
                  }`}
                  aria-current={isActive ? "page" : undefined}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </nav>

          {/* Right Action: Clean GitHub Link */}
          <div className="hidden sm:flex items-center gap-3">
            <a
              href="https://github.com/tanuja-talupula/StainShift"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium text-charcoal-600 bg-white border border-[#E8E4DD] hover:bg-[#F7F4EE] hover:text-charcoal-900 transition shadow-2xs"
            >
              <span>GitHub</span>
              <ExternalLink className="w-3 h-3 text-charcoal-400" />
            </a>
          </div>

          {/* Mobile menu toggle */}
          <div className="md:hidden flex items-center">
            <button
              type="button"
              onClick={() => setMobileOpen(!mobileOpen)}
              className="p-2 rounded-full text-charcoal-600 hover:text-charcoal-900 hover:bg-[#EDE7DE] transition"
              aria-label="Toggle navigation menu"
              aria-expanded={mobileOpen}
            >
              {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileOpen && (
        <div className="md:hidden border-b border-[#E8E4DD] bg-[#FAF8F5] px-4 pt-2 pb-4 space-y-1">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileOpen(false)}
                className={`flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl text-sm font-medium transition ${
                  isActive
                    ? "bg-[#EDE7DE] text-charcoal-900 font-semibold"
                    : "text-charcoal-600 hover:bg-[#F3EFEA]"
                }`}
                aria-current={isActive ? "page" : undefined}
              >
                <Icon className="w-4 h-4 text-charcoal-500" />
                <span>{item.name}</span>
              </Link>
            );
          })}
          <div className="pt-2 border-t border-[#E8E4DD]">
            <a
              href="https://github.com/tanuja-talupula/StainShift"
              target="_blank"
              rel="noopener noreferrer"
              className="block text-center py-2 text-xs font-medium text-charcoal-700 bg-white border border-[#E8E4DD] rounded-full"
            >
              GitHub Repository
            </a>
          </div>
        </div>
      )}
    </header>
  );
}
