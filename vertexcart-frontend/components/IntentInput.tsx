"use client";

import React, { useState, useEffect, useRef } from "react";
import { motion, useMotionValue, useTransform } from "framer-motion";
import { ArrowRight, Sparkles } from "lucide-react";
import { PoweredBySwiggy } from "./PoweredBySwiggy";

interface IntentInputProps {
  onSubmit: (text: string) => void;
}

const chips = [
  { label: "Pasta + Tiramisu", icon: "🍝", full: "Cook pasta tonight and order tiramisu for dessert" },
  { label: "Book a Table", icon: "🍷", full: "Book a table for 2 this Friday + wine at home" },
  { label: "Usual Groceries", icon: "🛒", full: "Reorder my usual groceries + pizza delivery" },
  { label: "Sushi Night", icon: "🍱", full: "Order sushi for dinner and get some snacks from Instamart" },
];

const PLACEHOLDER_SUGGESTIONS = [
  "e.g. 'I want to cook pasta but order dessert'",
  "e.g. 'Sushi dinner + book a table for Saturday'",
  "e.g. 'Reorder groceries and get pizza'",
  "e.g. 'Biryani + wine + a table for Friday night'",
];

// Floating food particles in background
const PARTICLES = [
  { emoji: "🍕", x: 10, y: 15, delay: 0 },
  { emoji: "🥗", x: 85, y: 20, delay: 0.5 },
  { emoji: "🍜", x: 75, y: 70, delay: 1 },
  { emoji: "🥩", x: 15, y: 65, delay: 1.5 },
  { emoji: "🍰", x: 90, y: 50, delay: 0.8 },
  { emoji: "🫖", x: 5, y: 45, delay: 1.2 },
];

export function IntentInput({ onSubmit }: IntentInputProps) {
  const [text, setText] = useState("");
  const [placeholderIdx, setPlaceholderIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const gradientX = useTransform(mouseX, [0, typeof window !== "undefined" ? window.innerWidth : 1440], [0, 100]);
  const gradientY = useTransform(mouseY, [0, typeof window !== "undefined" ? window.innerHeight : 900], [0, 100]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    const id = setInterval(() => {
      setPlaceholderIdx(i => (i + 1) % PLACEHOLDER_SUGGESTIONS.length);
    }, 3000);
    return () => clearInterval(id);
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (text.trim()) onSubmit(text.trim());
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    mouseX.set(e.clientX);
    mouseY.set(e.clientY);
  };

  return (
    <div
      className="flex flex-col items-center justify-center min-h-screen relative px-4 overflow-hidden"
      onMouseMove={handleMouseMove}
    >
      {/* Animated gradient orb following cursor */}
      <motion.div
        className="pointer-events-none fixed inset-0 opacity-20"
        style={{
          background: `radial-gradient(600px circle at ${gradientX}% ${gradientY}%, rgba(255,82,0,0.15), transparent 60%)`,
        }}
      />

      {/* Background particles */}
      {PARTICLES.map((p, i) => (
        <motion.div
          key={i}
          className="absolute text-2xl opacity-10 select-none pointer-events-none"
          style={{ left: `${p.x}%`, top: `${p.y}%` }}
          animate={{
            y: [0, -20, 0],
            rotate: [0, 10, -10, 0],
            opacity: [0.06, 0.12, 0.06],
          }}
          transition={{
            duration: 4 + i,
            delay: p.delay,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        >
          {p.emoji}
        </motion.div>
      ))}

      {/* Top-left logo */}
      <div className="absolute top-6 left-6 flex items-center gap-2.5 z-10">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 400, damping: 15 }}
          className="w-9 h-9 rounded-xl bg-swiggy-orange flex items-center justify-center shadow-lg"
          style={{ boxShadow: "0 0 20px rgba(255,82,0,0.4)" }}
        >
          <span className="text-white font-black text-lg leading-none">V</span>
        </motion.div>
        <motion.span
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.15 }}
          className="text-text-primary font-bold tracking-tight text-xl"
        >
          VertexCart
        </motion.span>
      </div>

      <div className="absolute bottom-6 right-6 z-10">
        <PoweredBySwiggy />
      </div>

      {/* Main content */}
      <div className="w-full max-w-2xl relative z-10">
        {/* Badge */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="flex justify-center mb-6"
        >
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-swiggy-orange/30 bg-swiggy-orange/10 text-swiggy-orange text-sm font-semibold">
            <Sparkles className="w-3.5 h-3.5" />
            Powered by Swiggy MCP · 35 tools
          </div>
        </motion.div>

        {/* Headline */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, delay: 0.05 }}
          className="text-center mb-10"
        >
          <h1 className="text-4xl md:text-6xl font-black text-text-primary mb-4 tracking-tight leading-tight">
            What are you{" "}
            <span className="text-swiggy-orange relative">
              planning
              <motion.div
                className="absolute -bottom-1 left-0 right-0 h-0.5 bg-swiggy-orange/40 rounded"
                initial={{ scaleX: 0 }}
                animate={{ scaleX: 1 }}
                transition={{ delay: 0.6, duration: 0.4 }}
              />
            </span>{" "}
            tonight?
          </h1>
          <p className="text-text-secondary text-lg max-w-md mx-auto leading-relaxed">
            Describe your evening. I&apos;ll handle food delivery, groceries, and restaurant reservations in one shot.
          </p>
        </motion.div>

        {/* Input */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.15 }}
        >
          <form onSubmit={handleSubmit} className="relative mb-8 group">
            {/* Glow ring on focus */}
            <div className="absolute -inset-0.5 bg-swiggy-orange/20 blur-xl rounded-2xl opacity-0 group-focus-within:opacity-100 transition-opacity duration-500 pointer-events-none" />

            <div className="relative flex items-center bg-surface border border-border-color rounded-2xl overflow-hidden focus-within:border-swiggy-orange/60 transition-colors shadow-lg">
              <input
                ref={inputRef}
                type="text"
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder={PLACEHOLDER_SUGGESTIONS[placeholderIdx]}
                className="flex-1 bg-transparent text-text-primary px-6 py-5 focus:outline-none text-base md:text-lg placeholder:text-text-secondary/40 transition-all"
              />
              <motion.button
                type="submit"
                disabled={!text.trim()}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.92 }}
                className="btn-ripple mr-3 w-12 h-12 bg-swiggy-orange rounded-xl flex items-center justify-center disabled:opacity-30 disabled:bg-surface-elevated text-white transition-all shadow-md"
                style={{ boxShadow: text.trim() ? "0 0 16px rgba(255,82,0,0.4)" : undefined }}
              >
                <ArrowRight className="w-5 h-5" />
              </motion.button>
            </div>
          </form>

          {/* Suggestion chips */}
          <div className="flex flex-wrap justify-center gap-3">
            {chips.map((chip, idx) => (
              <motion.button
                key={idx}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.25 + idx * 0.06 }}
                whileHover={{ scale: 1.04, y: -2 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setText(chip.full)}
                className="flex items-center gap-2.5 px-4 py-2.5 bg-surface rounded-xl text-sm font-medium text-text-secondary hover:text-text-primary transition-all border border-border-color hover:border-swiggy-orange/40 hover:bg-surface-elevated shadow-sm"
              >
                <span className="text-base">{chip.icon}</span>
                {chip.label}
              </motion.button>
            ))}
          </div>
        </motion.div>

        {/* Bottom verticals badge row */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="flex justify-center gap-6 mt-12"
        >
          {[
            { label: "Food", color: "text-swiggy-orange", dot: "bg-swiggy-orange" },
            { label: "Instamart", color: "text-instamart-green", dot: "bg-instamart-green" },
            { label: "Dineout", color: "text-dineout-purple", dot: "bg-dineout-purple" },
          ].map((v) => (
            <div key={v.label} className="flex items-center gap-1.5 text-xs font-semibold text-text-secondary">
              <div className={`w-1.5 h-1.5 rounded-full ${v.dot} live-dot`} />
              <span>{v.label}</span>
            </div>
          ))}
        </motion.div>
      </div>
    </div>
  );
}
