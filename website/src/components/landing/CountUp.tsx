"use client";

import React, { useEffect, useRef, useState } from "react";

interface Props {
  target: number;
  duration?: number; // ms
  decimals?: number;
  prefix?: string;
  suffix?: string;
  className?: string;
  /** If true, counts DOWN from a high start to target */
  countDown?: boolean;
  startFrom?: number;
}

export function CountUp({
  target,
  duration = 1600,
  decimals = 2,
  prefix = "",
  suffix = "%",
  className = "",
  countDown = false,
  startFrom,
}: Props) {
  const ref = useRef<HTMLSpanElement>(null);
  const [started, setStarted] = useState(false);
  const [displayed, setDisplayed] = useState(countDown ? (startFrom ?? 99.9) : 0);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setStarted(true);
          observer.unobserve(el);
        }
      },
      { threshold: 0.5 }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!started) return;

    const from = countDown ? (startFrom ?? 99.9) : 0;
    const to = target;
    const startTime = performance.now();

    const easeOut = (t: number) => 1 - Math.pow(1 - t, 3);

    const tick = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = easeOut(progress);
      const current = from + (to - from) * eased;
      setDisplayed(current);
      if (progress < 1) requestAnimationFrame(tick);
    };

    requestAnimationFrame(tick);
  }, [started, target, duration, countDown, startFrom]);

  return (
    <span ref={ref} className={className}>
      {prefix}
      {displayed.toFixed(decimals)}
      {suffix}
    </span>
  );
}
