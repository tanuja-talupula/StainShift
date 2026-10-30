"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  ChevronDown,
  Cpu,
  Zap,
  TrendingUp,
  ShieldCheck,
  Microscope,
  FlaskConical,
  BarChart3,
  Sparkles,
} from "lucide-react";
import { fetchBenchmarkDataClient } from "@/lib/fetchBenchmarkClient";
import { StainShiftBenchmark } from "@/lib/types";
import { ScrollReveal } from "@/components/landing/ScrollReveal";
import { CountUp } from "@/components/landing/CountUp";
import { AnimatedBarChart } from "@/components/landing/AnimatedBarChart";
import { ConfusionMatrixViewer } from "@/components/charts/ConfusionMatrixViewer";

export default function LandingPage() {
  const [data, setData] = useState<StainShiftBenchmark | null>(null);

  useEffect(() => {
    fetchBenchmarkDataClient().then(setData).catch(console.error);
  }, []);

  const origRow = data?.comparison_table.find((r) => r.condition === "original");
  const deconvRow = data?.comparison_table.find((r) => r.condition === "reconstruction_only");
  const latencyMs =
    data?.latency_benchmarks.profiles.baseline_mps?.model_forward_batch1.mean_ms ?? 3.91;

  return (
    <div className="space-y-0 -mt-8 md:-mt-12 -mx-4 sm:-mx-6 lg:-mx-8">

      {/* ─── SCREEN 1: HERO ─────────────────────────────────────────── */}
      <section className="relative min-h-[92vh] flex flex-col items-center justify-center text-center px-6 sm:px-12 overflow-hidden">
        {/* Subtle warm radial gradient backdrop */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0"
          style={{
            background:
              "radial-gradient(ellipse 80% 60% at 50% 0%, rgba(204,120,92,0.08) 0%, transparent 70%)",
          }}
        />

        {/* Eyebrow */}
        <div className="relative z-10 flex flex-col items-center gap-6 max-w-4xl mx-auto">
          <span className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-[#EDE7DE] text-charcoal-700 text-xs font-semibold tracking-wide border border-[#E0DAD1]">
            <FlaskConical className="w-3.5 h-3.5 text-[#CC785C]" />
            Histopathology CNN Benchmark · CRC-VAL-HE-7K
          </span>

          {/* Headline */}
          <h1 className="font-serif text-4xl sm:text-5xl lg:text-6xl font-normal text-charcoal-900 tracking-tight leading-[1.1]">
            Your CNN gets{" "}
            <span className="italic text-[#A8A196]">99.9%</span>{" "}
            on clean slides.
            <br />
            What happens when the{" "}
            <span className="italic text-[#CC785C]">stain shifts?</span>
          </h1>

          {/* Sub-headline */}
          <p className="text-base sm:text-lg text-charcoal-600 leading-relaxed max-w-2xl">
            Standard CNN training fails catastrophically under H&amp;E stain variation —
            collapsing from <strong className="text-charcoal-800">99.9%</strong> to{" "}
            <strong className="text-[#9B2A2A]">33.9%</strong> accuracy.
            Physics-informed Beer-Lambert augmentation recovers to{" "}
            <strong className="text-[#2D5A46]">97.7%</strong> across all 8 stain profiles.
          </p>

          {/* Quick stats ribbon */}
          <div className="flex flex-wrap items-center justify-center gap-6 mt-4 text-xs text-charcoal-500">
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#2D5A46]" />
              N = 1,077 held-out patches
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#CC785C]" />
              8 stain conditions
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#A8A196]" />
              MobileNetV3-Small · Apple Silicon
            </span>
          </div>
        </div>

        {/* Scroll cue */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-1 text-charcoal-300 animate-bounce">
          <ChevronDown className="w-5 h-5" />
        </div>
      </section>

      {/* ─── SCREEN 2: ANIMATED KPIs + BAR CHART ───────────────────── */}
      <section
        id="benchmark"
        className="px-6 sm:px-12 lg:px-20 py-24 space-y-14 max-w-7xl mx-auto w-full"
      >
        {/* Section label */}
        <ScrollReveal>
          <div className="flex items-center gap-3">
            <span className="w-6 h-px bg-[#CC785C]" />
            <span className="text-xs font-bold uppercase tracking-widest text-[#CC785C]">
              The Collapse &amp; Recovery
            </span>
          </div>
        </ScrollReveal>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {/* Card 1 — Baseline clean */}
          <ScrollReveal delay={0}>
            <div className="bg-white rounded-2xl border border-[#E8E4DD] p-5 shadow-warm space-y-1.5 h-full">
              <span className="text-[10px] uppercase font-bold tracking-wider text-charcoal-400">
                Original H&amp;E — Baseline
              </span>
              <div className="text-3xl font-serif font-bold text-charcoal-900">
                {data ? (
                  <CountUp target={origRow?.baseline_accuracy_pct ?? 99.91} />
                ) : (
                  "99.91%"
                )}
              </div>
              <p className="text-[11px] text-charcoal-500 leading-snug">
                Standard CNN on clean, unperturbed slides. Peak performance in the lab.
              </p>
            </div>
          </ScrollReveal>

          {/* Card 2 — Baseline collapses */}
          <ScrollReveal delay={80}>
            <div className="bg-[#FAF5F5] rounded-2xl border border-[#F2D6D6] p-5 shadow-warm space-y-1.5 h-full">
              <span className="text-[10px] uppercase font-bold tracking-wider text-[#9B2A2A]">
                Under Stain Shift — Baseline
              </span>
              <div className="text-3xl font-serif font-bold text-[#9B2A2A]">
                {data ? (
                  <CountUp
                    target={deconvRow?.baseline_accuracy_pct ?? 33.89}
                    countDown
                    startFrom={99.9}
                  />
                ) : (
                  "33.89%"
                )}
              </div>
              <p className="text-[11px] text-[#9B2A2A] leading-snug">
                <strong>−66.02%</strong> collapse under deconvolution. CNN memorised stain
                colour, not tissue morphology.
              </p>
            </div>
          </ScrollReveal>

          {/* Card 3 — Robust recovery */}
          <ScrollReveal delay={160}>
            <div className="bg-[#F6FAF7] rounded-2xl border border-[#D5E5DA] p-5 shadow-warm space-y-1.5 h-full">
              <span className="text-[10px] uppercase font-bold tracking-wider text-[#2D5A46]">
                Stain-Robust Recovery
              </span>
              <div className="text-3xl font-serif font-bold text-[#2D5A46]">
                {data ? (
                  <CountUp
                    target={deconvRow?.net_recovery_pct ?? 63.79}
                    prefix="+"
                  />
                ) : (
                  "+63.79%"
                )}
              </div>
              <p className="text-[11px] text-[#244737] leading-snug">
                Beer-Lambert augmentation restores high accuracy. Maximum net recovery
                across all 8 profiles.
              </p>
            </div>
          </ScrollReveal>

          {/* Card 4 — Latency */}
          <ScrollReveal delay={240}>
            <div className="bg-white rounded-2xl border border-[#E8E4DD] p-5 shadow-warm space-y-1.5 h-full">
              <span className="text-[10px] uppercase font-bold tracking-wider text-charcoal-400">
                MPS Forward Latency
              </span>
              <div className="flex items-baseline gap-1.5">
                <span className="text-3xl font-serif font-bold text-charcoal-900">
                  {data ? (
                    <CountUp
                      target={latencyMs}
                      suffix=" ms"
                      decimals={2}
                    />
                  ) : (
                    "3.91 ms"
                  )}
                </span>
              </div>
              <p className="text-[11px] text-charcoal-500 leading-snug flex items-center gap-1">
                <Cpu className="w-3 h-3 inline text-[#CC785C]" />
                Apple Silicon MPS · Pure model forward, batch 1
              </p>
            </div>
          </ScrollReveal>
        </div>

        {/* Animated bar chart */}
        <ScrollReveal delay={100}>
          <div className="bg-white rounded-2xl border border-[#E8E4DD] p-6 shadow-warm space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
              <div>
                <h2 className="font-serif text-xl font-medium text-charcoal-900">
                  Accuracy Across All 8 Stain Profiles
                </h2>
                <p className="text-xs text-charcoal-500 mt-1">
                  Frozen held-out test cohort · N = 1,077 patches · CRC-VAL-HE-7K
                </p>
              </div>
              <Link
                href="/dashboard/"
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-[#FAF4ED] hover:bg-[#F5ECE0] text-[#CC785C] text-xs font-semibold border border-[#EDD7C7] transition whitespace-nowrap"
              >
                <BarChart3 className="w-3.5 h-3.5" />
                Full Dashboard
              </Link>
            </div>

            {data ? (
              <AnimatedBarChart data={data.comparison_table} />
            ) : (
              <div className="h-48 animate-pulse bg-[#F3EFEA] rounded-xl" />
            )}
          </div>
        </ScrollReveal>
      </section>

      {/* ─── SCREEN 3: CONFUSION MATRIX + LATENCY BADGE ────────────── */}
      <section className="px-6 sm:px-12 lg:px-20 py-20 bg-[#F7F5F1] border-y border-[#E8E4DD] space-y-10">
        <div className="max-w-7xl mx-auto w-full space-y-10">
          <ScrollReveal>
            <div className="flex items-center gap-3">
              <span className="w-6 h-px bg-[#CC785C]" />
              <span className="text-xs font-bold uppercase tracking-widest text-[#CC785C]">
                Interactive Evidence
              </span>
            </div>
          </ScrollReveal>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
            {/* Confusion matrix (2 cols wide) */}
            <div className="lg:col-span-2">
              <ScrollReveal>
                <h2 className="font-serif text-xl font-medium text-charcoal-900 mb-4">
                  Watch the Off-Diagonal Errors Disappear
                </h2>
              </ScrollReveal>
              <ScrollReveal delay={80}>
                {data ? (
                  <ConfusionMatrixViewer
                    baselineResults={data.results.baseline}
                    robustResults={data.results.robust_stain_aug}
                    conditions={data.conditions_evaluated}
                    classNames={data.dataset_metadata.class_names}
                  />
                ) : (
                  <div className="h-64 animate-pulse bg-white rounded-2xl border border-[#E8E4DD]" />
                )}
              </ScrollReveal>
            </div>

            {/* Right sidebar: latency badge + proof points */}
            <div className="space-y-5">
              <ScrollReveal delay={120}>
                <div className="bg-white rounded-2xl border border-[#E8E4DD] p-6 shadow-warm space-y-4">
                  <div className="flex items-center gap-2">
                    <Zap className="w-4 h-4 text-[#CC785C]" />
                    <span className="text-xs font-bold uppercase tracking-wider text-charcoal-500">
                      Inference Speed
                    </span>
                  </div>
                  <div className="text-4xl font-serif font-bold text-charcoal-900">
                    {data ? (
                      <CountUp target={latencyMs} suffix=" ms" decimals={2} />
                    ) : (
                      "3.91 ms"
                    )}
                  </div>
                  <p className="text-xs text-charcoal-500 leading-relaxed">
                    Apple Silicon MPS · mean over 200 timed runs · pure model
                    forward on batch 1
                  </p>
                  <div className="pt-1 border-t border-[#E8E4DD] text-[11px] font-mono text-charcoal-400 space-y-1">
                    <div className="flex justify-between">
                      <span>p95</span>
                      <span>
                        {data?.latency_benchmarks.profiles.baseline_mps?.model_forward_batch1.p95_ms.toFixed(2)} ms
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Batch-16 throughput</span>
                      <span>
                        {data?.latency_benchmarks.profiles.baseline_mps?.batched_throughput_batch16.samples_per_second.toFixed(0)} img/s
                      </span>
                    </div>
                  </div>
                </div>
              </ScrollReveal>

              <ScrollReveal delay={200}>
                <div className="bg-white rounded-2xl border border-[#E8E4DD] p-6 shadow-warm space-y-3">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-[#2D5A46]" />
                    <span className="text-xs font-bold uppercase tracking-wider text-charcoal-500">
                      Benchmark Integrity
                    </span>
                  </div>
                  <ul className="space-y-2 text-xs text-charcoal-600">
                    <li className="flex items-start gap-2">
                      <span className="mt-0.5 w-1.5 h-1.5 rounded-full bg-[#2D5A46] shrink-0" />
                      Frozen split manifest — SHA-256 verified
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="mt-0.5 w-1.5 h-1.5 rounded-full bg-[#2D5A46] shrink-0" />
                      MLflow Run ID tracked &amp; reproducible
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="mt-0.5 w-1.5 h-1.5 rounded-full bg-[#2D5A46] shrink-0" />
                      Zero data leakage — test set never seen during training
                    </li>
                  </ul>
                  <Link
                    href="/dashboard/"
                    className="inline-flex items-center gap-1 text-xs font-semibold text-[#CC785C] hover:underline mt-1"
                  >
                    View full technical details
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </ScrollReveal>

              <ScrollReveal delay={280}>
                <div className="bg-white rounded-2xl border border-[#E8E4DD] p-6 shadow-warm space-y-3">
                  <div className="flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-[#CC785C]" />
                    <span className="text-xs font-bold uppercase tracking-wider text-charcoal-500">
                      Key Result
                    </span>
                  </div>
                  <p className="text-sm text-charcoal-700 leading-relaxed">
                    Stain-Robust model stays{" "}
                    <strong className="text-[#2D5A46]">≥ 94%</strong> accurate
                    across <em>all</em> 8 stain perturbations. Baseline collapses
                    as low as <strong className="text-[#9B2A2A]">33.9%</strong>.
                  </p>
                </div>
              </ScrollReveal>
            </div>
          </div>
        </div>
      </section>

      {/* ─── SCREEN 4: LAUNCH BANNER ────────────────────────────────── */}
      <section className="px-6 sm:px-12 lg:px-20 py-28 max-w-7xl mx-auto w-full">
        <ScrollReveal>
          <div className="relative rounded-3xl bg-charcoal-900 overflow-hidden px-8 sm:px-16 py-16 sm:py-20 text-center space-y-7">
            {/* Warm glow */}
            <div
              aria-hidden
              className="pointer-events-none absolute inset-0"
              style={{
                background:
                  "radial-gradient(ellipse 70% 80% at 50% 120%, rgba(204,120,92,0.25) 0%, transparent 70%)",
              }}
            />

            <div className="relative z-10 space-y-7">
              <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-white/10 text-white/70 text-xs font-semibold border border-white/10">
                <Microscope className="w-3.5 h-3.5 text-[#CC785C]" />
                Live PyTorch Inference · MobileNetV3-Small
              </div>

              <h2 className="font-serif text-3xl sm:text-4xl lg:text-5xl font-normal text-white leading-tight">
                Ready to perturb H&amp;E patches
                <br className="hidden sm:block" /> in real time?
              </h2>

              <p className="text-charcoal-300 text-base sm:text-lg max-w-xl mx-auto leading-relaxed">
                Upload a histology patch, apply any of 8 synthetic stain conditions,
                and compare how both models classify tissue — live, in under 4 ms.
              </p>

              <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-2">
                <Link
                  href="/workspace/"
                  className="inline-flex items-center gap-2.5 px-8 py-4 rounded-full bg-[#CC785C] hover:bg-[#B96449] text-white text-base font-semibold shadow-warm-md transition active:scale-[0.98]"
                >
                  <Sparkles className="w-5 h-5" />
                  Launch AI Workspace
                  <ArrowRight className="w-5 h-5" />
                </Link>
                <Link
                  href="/demo/"
                  className="inline-flex items-center gap-2 px-6 py-4 rounded-full bg-white/10 hover:bg-white/15 text-white text-sm font-medium border border-white/20 transition"
                >
                  Browse Precomputed Demo
                </Link>
              </div>

              <p className="text-xs text-charcoal-400 pt-2">
                No upload required — explore 72 precomputed patches instantly in the Demo Explorer.
              </p>
            </div>
          </div>
        </ScrollReveal>
      </section>

    </div>
  );
}
