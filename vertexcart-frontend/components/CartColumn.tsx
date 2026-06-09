"use client";

import React from "react";
import { CartItem } from "../lib/types";
import { Clock, MapPin } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface CartColumnProps {
  vertical: "instamart" | "food" | "dineout";
  title: string;
  items: CartItem[];
  total: number;
  eta?: string;
  restaurantName?: string;
  accentColor: string;
  accentBg: string;
  accentBorder: string;
  animateX: number;
}

export function CartColumn({
  vertical,
  title,
  items,
  total,
  eta,
  restaurantName,
  accentColor,
  accentBg,
  accentBorder,
  animateX,
}: CartColumnProps) {
  const icons = { instamart: "🛒", food: "🍔", dineout: "🍽️" };

  return (
    <motion.div
      initial={{ opacity: 0, x: animateX, scale: 0.97 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: animateX, scale: 0.95 }}
      transition={{ type: "spring", stiffness: 280, damping: 22 }}
      className="flex-1 rounded-2xl overflow-hidden"
      style={{ background: accentBg, border: `1px solid ${accentBorder}` }}
    >
      {/* Column header */}
      <div className="px-5 pt-4 pb-3 flex items-center justify-between" style={{ borderBottom: `1px solid ${accentBorder}` }}>
        <div className="flex items-center gap-2.5">
          <span className="text-xl">{icons[vertical]}</span>
          <div>
            <h2 className="font-bold text-text-primary text-sm">{title}</h2>
            {restaurantName && (
              <div className="flex items-center gap-1 mt-0.5">
                <MapPin className="w-3 h-3" style={{ color: accentColor }} />
                <span className="text-xs text-text-secondary">{restaurantName}</span>
              </div>
            )}
          </div>
        </div>
        {eta && (
          <div
            className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-xl"
            style={{ color: accentColor, background: `${accentColor}15` }}
          >
            <Clock className="w-3 h-3" />
            {eta}
          </div>
        )}
      </div>

      {/* Items */}
      <div className="p-4 space-y-2.5">
        <AnimatePresence mode="popLayout">
          {items.map((item, i) => (
            <motion.div
              key={`${item.name}-${i}`}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8, height: 0 }}
              transition={{ type: "spring", stiffness: 350, damping: 25, delay: i * 0.05 }}
              className="flex items-center justify-between bg-background/60 rounded-xl px-4 py-3 border border-border-color/50"
            >
              <div className="flex-1 min-w-0 pr-3">
                <div className="text-text-primary text-sm font-semibold truncate">{item.name}</div>
                <div className="text-text-secondary text-xs mt-0.5">Qty: {item.quantity}</div>
              </div>
              <span className="text-text-primary text-sm font-bold shrink-0">₹{item.price * item.quantity}</span>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* Subtotal footer */}
      <div
        className="mx-4 mb-4 px-4 py-3 rounded-xl flex justify-between items-center"
        style={{ background: `${accentColor}12`, border: `1px solid ${accentBorder}` }}
      >
        <span className="text-text-secondary text-sm font-semibold">Subtotal</span>
        <span className="font-black text-base text-text-primary">₹{total}</span>
      </div>
    </motion.div>
  );
}
