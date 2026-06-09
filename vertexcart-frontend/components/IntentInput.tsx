"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { PoweredBySwiggy } from "./PoweredBySwiggy";

interface IntentInputProps {
  onSubmit: (text: string) => void;
}

export function IntentInput({ onSubmit }: IntentInputProps) {
  const [text, setText] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (text.trim()) {
      onSubmit(text.trim());
    }
  };

  const chips = [
    "Pasta tonight + dessert delivery",
    "Friday dinner out + wine at home",
    "Reorder my usual groceries + pizza",
  ];

  return (
    <div className="flex flex-col items-center justify-center min-h-screen relative px-4">
      <div className="absolute top-6 left-6">
        <span className="text-white font-bold tracking-tight text-lg">VertexCart</span>
      </div>
      
      <div className="absolute bottom-6 right-6">
        <PoweredBySwiggy />
      </div>

      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="text-center mb-10"
      >
        <h1 className="text-3xl md:text-4xl font-semibold text-white mb-3">
          What are you planning tonight?
        </h1>
        <p className="text-text-secondary text-base">
          I&apos;ll handle food, groceries, and reservations.
        </p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.2 }}
        className="w-full max-w-2xl"
      >
        <form onSubmit={handleSubmit} className="relative mb-8">
          <input
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Tell me what you need..."
            className="w-full bg-surface-elevated text-white rounded-full px-6 py-4 pr-16 focus:outline-none focus:ring-2 focus:ring-swiggy-orange shadow-lg transition-all placeholder:text-text-secondary"
          />
          <button
            type="submit"
            disabled={!text.trim()}
            className="absolute right-2 top-1/2 -translate-y-1/2 w-10 h-10 bg-swiggy-orange rounded-full flex items-center justify-center disabled:opacity-50 transition-opacity hover:opacity-90"
          >
            <ArrowRight className="w-5 h-5 text-white" />
          </button>
        </form>

        <div className="flex flex-wrap justify-center gap-3">
          {chips.map((chip, idx) => (
            <motion.button
              key={idx}
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => setText(chip)}
              className="px-4 py-2 bg-surface rounded-full text-sm text-text-secondary hover:text-white transition-colors border border-surface-elevated hover:border-text-secondary"
            >
              {chip}
            </motion.button>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
