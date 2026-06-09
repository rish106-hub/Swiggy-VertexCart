"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Zap, Eye } from "lucide-react";
import { IntentResult } from "../lib/types";

interface AgentReasoningProps {
  intent: IntentResult;
  onLiveCorrection: (text: string) => void;
  onCorrectionSubmit: (text: string) => void;
}

const VERTICAL_COLORS: Record<string, { text: string; bg: string; border: string }> = {
  instamart: { text: "text-instamart-green", bg: "bg-instamart-green/10", border: "border-instamart-green/30" },
  food: { text: "text-swiggy-orange", bg: "bg-swiggy-orange/10", border: "border-swiggy-orange/30" },
  dineout: { text: "text-dineout-purple", bg: "bg-dineout-purple/10", border: "border-dineout-purple/30" },
};

export function AgentReasoning({ intent, onLiveCorrection, onCorrectionSubmit }: AgentReasoningProps) {
  const [correctionText, setCorrectionText] = useState("");
  const [isPreviewMode, setIsPreviewMode] = useState(false);

  // Fire live update on every keystroke
  useEffect(() => {
    if (correctionText.trim()) {
      onLiveCorrection(correctionText);
      setIsPreviewMode(true);
    } else {
      setIsPreviewMode(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [correctionText]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (correctionText.trim()) {
      onCorrectionSubmit(correctionText.trim());
      setCorrectionText("");
      setIsPreviewMode(false);
    }
  };

  return (
    <div className="bg-surface border border-border-color rounded-2xl p-5 sticky top-8 shadow-sm">
      {/* Header */}
      <div className="flex items-center gap-2 mb-5">
        <div className="w-7 h-7 rounded-lg bg-swiggy-orange/15 flex items-center justify-center">
          <Zap className="w-3.5 h-3.5 text-swiggy-orange" />
        </div>
        <h3 className="text-text-primary font-bold text-sm">Intent Breakdown</h3>
      </div>

      {/* Entity list */}
      <div className="space-y-2.5 mb-6">
        <AnimatePresence mode="popLayout">
          {intent.entities.map((ent, i) => {
            const vc = VERTICAL_COLORS[ent.vertical] || VERTICAL_COLORS.food;
            return (
              <motion.div
                key={`${ent.text}-${ent.vertical}`}
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10, height: 0 }}
                transition={{ type: "spring", stiffness: 300, damping: 25, delay: i * 0.05 }}
                className={`flex items-center justify-between px-3 py-2.5 rounded-xl border ${vc.bg} ${vc.border}`}
              >
                <span className="text-text-primary text-sm font-medium truncate max-w-[130px]">
                  &quot;{ent.text}&quot;
                </span>
                <span className={`text-xs font-bold uppercase px-2 py-0.5 rounded-md ${vc.text} bg-background/50`}>
                  {ent.vertical}
                </span>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>

      {/* Occasion + urgency tags */}
      <div className="flex gap-2 flex-wrap mb-6">
        <span className="text-xs text-text-secondary bg-surface-elevated px-2.5 py-1 rounded-lg border border-border-color font-medium capitalize">
          {intent.occasion?.replace(/_/g, " ")}
        </span>
        <span className="text-xs text-text-secondary bg-surface-elevated px-2.5 py-1 rounded-lg border border-border-color font-medium capitalize">
          {intent.urgency}
        </span>
      </div>

      {/* Live correction input */}
      <div className="border-t border-border-color pt-5">
        <label className="text-xs text-text-secondary mb-2 block font-semibold uppercase tracking-wider flex items-center gap-1.5">
          <Eye className="w-3 h-3" />
          {isPreviewMode ? "Previewing changes live" : "Make a correction"}
        </label>

        <AnimatePresence>
          {isPreviewMode && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="mb-2 text-xs text-swiggy-orange bg-swiggy-orange/10 border border-swiggy-orange/20 rounded-lg px-3 py-2 font-medium"
            >
              ↑ Cart updating in real time
            </motion.div>
          )}
        </AnimatePresence>

        <form onSubmit={handleSubmit} className="relative">
          <input
            type="text"
            value={correctionText}
            onChange={(e) => setCorrectionText(e.target.value)}
            placeholder="e.g. drop the dessert, add coffee..."
            className="w-full bg-surface-elevated border border-border-color rounded-xl px-4 py-3 text-sm text-text-primary placeholder:text-text-secondary/50 focus:outline-none focus:border-swiggy-orange/50 focus:ring-1 focus:ring-swiggy-orange/20 pr-12 transition-all"
          />
          <motion.button
            type="submit"
            disabled={!correctionText.trim()}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.92 }}
            className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 flex items-center justify-center rounded-lg bg-swiggy-orange text-white disabled:opacity-30 disabled:bg-surface-elevated disabled:text-text-secondary transition-all"
          >
            <Send className="w-3.5 h-3.5" />
          </motion.button>
        </form>

        <p className="text-xs text-text-secondary/60 mt-2 leading-relaxed">
          Type to preview changes instantly. Hit send to confirm.
        </p>
      </div>
    </div>
  );
}
