"use client";

import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { IntentResult } from "../lib/types";

interface ParsingStateProps {
  query: string;
  intent?: IntentResult;
}

const VERTICAL_META = {
  instamart: { label: "Instamart", emoji: "🛒", color: "#00B383", bg: "rgba(0,179,131,0.08)", border: "rgba(0,179,131,0.25)" },
  food: { label: "Swiggy Food", emoji: "🍔", color: "#FF5200", bg: "rgba(255,82,0,0.08)", border: "rgba(255,82,0,0.25)" },
  dineout: { label: "Dineout", emoji: "🍽️", color: "#8B5CF6", bg: "rgba(139,92,246,0.08)", border: "rgba(139,92,246,0.25)" },
};

const SCANNING_MESSAGES = [
  "Figuring out your verticals...",
  "Searching the menu...",
  "Checking real-time availability...",
  "Building your cart...",
  "Almost done...",
];

export function ParsingState({ query, intent }: ParsingStateProps) {
  const [msgIdx, setMsgIdx] = useState(0);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const msgInterval = setInterval(() => setMsgIdx(i => Math.min(i + 1, SCANNING_MESSAGES.length - 1)), 700);
    return () => clearInterval(msgInterval);
  }, []);

  useEffect(() => {
    const start = Date.now();
    const animate = () => {
      const elapsed = Date.now() - start;
      // Fast to 70%, then stall until intent arrives
      const target = intent ? 100 : Math.min(70, (elapsed / 1500) * 70);
      setProgress(p => {
        const next = Math.max(p, target);
        if (next < 100) requestAnimationFrame(animate);
        return next;
      });
    };
    const raf = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(raf);
  }, [intent]);

  const activeVerticals = intent
    ? Array.from(new Set(intent.entities.map(e => e.vertical)))
    : [];

  return (
    <div className="min-h-screen flex flex-col items-center px-4 pt-16 pb-8 max-w-3xl mx-auto w-full">
      {/* Query bubble */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-12 w-full"
      >
        <div className="mx-auto max-w-xl bg-surface border border-border-color rounded-2xl px-6 py-4 text-center">
          <span className="text-text-secondary text-xs font-semibold uppercase tracking-wider block mb-1.5">Your order</span>
          <span className="text-text-primary font-semibold text-lg">&quot;{query}&quot;</span>
        </div>
      </motion.div>

      {/* Progress bar */}
      <div className="w-full max-w-xl mb-3">
        <div className="h-1 bg-surface-elevated rounded-full overflow-hidden">
          <motion.div
            className="h-full rounded-full"
            style={{ background: "linear-gradient(90deg, #FF5200, #FF7A35)" }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.3, ease: "linear" }}
          />
        </div>
      </div>

      {/* Status message */}
      <AnimatePresence mode="wait">
        <motion.p
          key={msgIdx}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -4 }}
          transition={{ duration: 0.2 }}
          className="text-text-secondary text-sm font-medium mb-12"
        >
          {SCANNING_MESSAGES[msgIdx]}
        </motion.p>
      </AnimatePresence>

      {/* Vertical lanes */}
      <div className="w-full flex flex-col md:flex-row gap-4">
        <AnimatePresence>
          {activeVerticals.length === 0 ? (
            // Skeleton lanes while parsing
            ["instamart", "food", "dineout"].map((v, i) => (
              <motion.div
                key={`sk-${v}`}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.08 }}
                className="flex-1 rounded-2xl p-5 border border-border-color bg-surface min-h-[140px]"
              >
                <div className="skeleton h-3 w-20 rounded mb-4" />
                <div className="space-y-3">
                  <div className="skeleton h-10 w-full rounded-xl" />
                  <div className="skeleton h-10 w-4/5 rounded-xl" />
                </div>
              </motion.div>
            ))
          ) : (
            activeVerticals.map((vertical, idx) => {
              const meta = VERTICAL_META[vertical as keyof typeof VERTICAL_META];
              if (!meta) return null;
              return (
                <motion.div
                  key={vertical}
                  initial={{ opacity: 0, scale: 0.94, y: 16 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  transition={{ type: "spring", stiffness: 300, damping: 22, delay: idx * 0.1 }}
                  className="flex-1 rounded-2xl p-5 min-h-[140px]"
                  style={{ background: meta.bg, border: `1px solid ${meta.border}` }}
                >
                  <div className="flex items-center justify-between mb-5">
                    <div className="flex items-center gap-2">
                      <span className="text-xl">{meta.emoji}</span>
                      <span className="text-xs font-bold uppercase tracking-wider" style={{ color: meta.color }}>
                        {meta.label}
                      </span>
                    </div>
                    {/* Spinning indicator */}
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                      className="w-4 h-4 rounded-full border-2 border-t-transparent"
                      style={{ borderColor: `${meta.color}40`, borderTopColor: meta.color }}
                    />
                  </div>

                  <div className="space-y-2.5">
                    {intent!.entities
                      .filter(e => e.vertical === vertical)
                      .map((entity, eIdx) => (
                        <motion.div
                          key={eIdx}
                          initial={{ opacity: 0, x: -12 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: idx * 0.1 + eIdx * 0.08 + 0.2 }}
                          className="bg-background/60 rounded-xl px-4 py-2.5 border border-border-color"
                        >
                          <span className="text-sm font-semibold text-text-primary block capitalize">
                            {entity.text}
                          </span>
                          <span className="text-xs mt-0.5 block capitalize" style={{ color: meta.color }}>
                            {entity.type.replace("_", " ")}
                          </span>
                        </motion.div>
                      ))}
                  </div>
                </motion.div>
              );
            })
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
