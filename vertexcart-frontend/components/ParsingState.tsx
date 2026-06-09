"use client";

import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { IntentResult } from "../lib/types";

interface ParsingStateProps {
  query: string;
  intent?: IntentResult;
  isTakingLong?: boolean; // If backend takes > 1.5s
}

export function ParsingState({ query, intent, isTakingLong }: ParsingStateProps) {
  const [dots, setDots] = useState("");

  useEffect(() => {
    const interval = setInterval(() => {
      setDots((prev) => (prev.length >= 3 ? "" : prev + "."));
    }, 400);
    return () => clearInterval(interval);
  }, []);

  const getVerticalColor = (vertical: string) => {
    switch (vertical) {
      case "instamart": return "border-instamart-green text-instamart-green";
      case "food": return "border-swiggy-orange text-swiggy-orange";
      case "dineout": return "border-dineout-purple text-dineout-purple";
      default: return "border-surface-elevated text-text-secondary";
    }
  };

  const getVerticalBg = (vertical: string) => {
    switch (vertical) {
      case "instamart": return "bg-instamart-green/10";
      case "food": return "bg-swiggy-orange/10";
      case "dineout": return "bg-dineout-purple/10";
      default: return "bg-surface-elevated/10";
    }
  };

  // Unique verticals from parsed intent
  const activeVerticals = intent 
    ? Array.from(new Set(intent.entities.map(e => e.vertical)))
    : [];

  return (
    <div className="flex flex-col items-center min-h-screen pt-20 px-6 max-w-5xl mx-auto w-full">
      <motion.div
        initial={{ y: 50, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="w-full text-center mb-16"
      >
        <div className="bg-surface-elevated inline-block px-6 py-3 rounded-full text-text-secondary italic">
          &quot;{query}&quot;
        </div>
      </motion.div>

      <div className="text-center mb-12 h-8">
        <span className="text-white text-lg">Reading your intent{dots}</span>
      </div>

      <div className="flex flex-col md:flex-row w-full gap-6 justify-center">
        <AnimatePresence>
          {(!intent && isTakingLong) ? (
            // Skeleton loaders
            ["instamart", "food", "dineout"].map((v) => (
               <motion.div
                key={`skel-${v}`}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="flex-1 border border-surface-elevated rounded-xl p-6 bg-surface min-h-[200px]"
              >
                <div className="h-4 w-24 bg-surface-elevated rounded mb-6 animate-pulse"></div>
                <div className="space-y-4">
                  <div className="h-12 w-full bg-surface-elevated rounded animate-pulse"></div>
                  <div className="h-12 w-full bg-surface-elevated rounded animate-pulse"></div>
                </div>
              </motion.div>
            ))
          ) : intent ? (
             // Actual active vertical lanes based on intent
             activeVerticals.map((vertical, idx) => (
                <motion.div
                  key={vertical}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.1 }}
                  className={`flex-1 border rounded-xl p-6 ${getVerticalColor(vertical)} ${getVerticalBg(vertical)}`}
                >
                  <h3 className="font-semibold uppercase tracking-wider text-sm mb-6 flex items-center justify-between">
                    {vertical}
                    <span className="animate-spin h-4 w-4 border-2 border-current border-t-transparent rounded-full opacity-50"></span>
                  </h3>
                  <div className="space-y-3">
                    {intent.entities
                      .filter(e => e.vertical === vertical)
                      .map((entity, eIdx) => (
                        <motion.div
                          key={eIdx}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: (idx * 0.1) + (eIdx * 0.1) + 0.3 }}
                          className="bg-background/50 rounded p-3 text-white border border-white/5"
                        >
                          <span className="text-sm font-medium">{entity.text}</span>
                          <span className="block text-xs opacity-60 mt-1 capitalize">{entity.type.replace('_', ' ')}</span>
                        </motion.div>
                    ))}
                  </div>
                </motion.div>
             ))
          ) : (
             // Initial empty state before timeout
             <div className="w-full flex justify-center opacity-0">...</div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
