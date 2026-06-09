"use client";

import React, { useState, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { ArrowRight, Sparkles } from "lucide-react";
import { PoweredBySwiggy } from "./PoweredBySwiggy";

interface IntentInputProps {
  onSubmit: (text: string) => void;
}

export function IntentInput({ onSubmit }: IntentInputProps) {
  const [text, setText] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-focus input on load for convenience
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (text.trim()) {
      onSubmit(text.trim());
    }
  };

  const chips = [
    { label: "Pasta + Dessert", icon: "🍝", full: "Pasta tonight + dessert delivery" },
    { label: "Friday Dinner", icon: "🍷", full: "Friday dinner out + wine at home" },
    { label: "Usual Groceries", icon: "🛒", full: "Reorder my usual groceries + pizza" },
  ];

  return (
    <div className="flex flex-col items-center justify-center min-h-screen relative px-4 bg-background">
      <div className="absolute top-6 left-6 flex items-center gap-2">
        <div className="w-8 h-8 rounded-full bg-swiggy-orange flex items-center justify-center">
           <span className="text-white font-bold text-lg leading-none">S</span>
        </div>
        <span className="text-text-primary font-bold tracking-tight text-xl">VertexCart</span>
      </div>
      
      <div className="absolute bottom-6 right-6">
        <PoweredBySwiggy />
      </div>

      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="text-center mb-12"
      >
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-swiggy-orange/10 text-swiggy-orange text-sm font-semibold mb-6">
           <Sparkles className="w-4 h-4" /> AI Powered Ordering
        </div>
        <h1 className="text-4xl md:text-5xl font-extrabold text-text-primary mb-4 tracking-tight">
          What are you planning tonight?
        </h1>
        <p className="text-text-secondary text-lg max-w-lg mx-auto">
          Just describe your evening. I&apos;ll handle food, groceries, and reservations in one go.
        </p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.2 }}
        className="w-full max-w-2xl"
      >
        <form onSubmit={handleSubmit} className="relative mb-10 group">
          <div className="absolute inset-0 bg-swiggy-orange/20 blur-xl rounded-full opacity-0 group-focus-within:opacity-100 transition-opacity duration-500"></div>
          <input
            ref={inputRef}
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="e.g. 'I want to cook pasta but order a dessert'"
            className="relative w-full bg-surface text-text-primary rounded-full px-8 py-5 pr-16 focus:outline-none focus:ring-2 focus:ring-swiggy-orange shadow-sm border border-border-color transition-all placeholder:text-text-secondary/60 text-lg"
          />
          <button
            type="submit"
            disabled={!text.trim()}
            className="absolute right-3 top-1/2 -translate-y-1/2 w-12 h-12 bg-swiggy-orange rounded-full flex items-center justify-center disabled:opacity-50 disabled:bg-surface-elevated disabled:text-text-secondary text-white transition-all hover:shadow-md hover:scale-105 active:scale-95"
          >
            <ArrowRight className="w-6 h-6" />
          </button>
        </form>

        <div className="flex flex-wrap justify-center gap-4">
          {chips.map((chip, idx) => (
            <motion.button
              key={idx}
              whileHover={{ scale: 1.05, y: -2 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setText(chip.full)}
              className="flex items-center gap-2 px-5 py-3 bg-surface rounded-full text-sm font-medium text-text-primary hover:text-swiggy-orange transition-colors border border-border-color shadow-sm hover:shadow hover:border-swiggy-orange/50"
            >
              <span className="text-lg">{chip.icon}</span> {chip.label}
            </motion.button>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
