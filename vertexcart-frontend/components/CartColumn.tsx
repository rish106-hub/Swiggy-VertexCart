import React from "react";
import { CartItem } from "../lib/types";
import { Clock, MapPin } from "lucide-react";
import { motion } from "framer-motion";

interface CartColumnProps {
  vertical: "instamart" | "food" | "dineout";
  title: string;
  items: CartItem[];
  total: number; // mapped from subtotal in parent
  eta?: string;
  restaurantName?: string;
  colorClass: string;
  borderColorClass: string;
  accentBgClass: string;
  animateX: number;
}

export function CartColumn({
  vertical,
  title,
  items,
  total,
  eta,
  restaurantName,
  colorClass,
  borderColorClass,
  accentBgClass,
  animateX
}: CartColumnProps) {
  return (
    <motion.div
      initial={{ opacity: 0, x: animateX }}
      animate={{ opacity: 1, x: 0 }}
      className="flex-1"
    >
      <div className={`flex items-center gap-2 mb-4 border-b ${borderColorClass} pb-2`}>
        <div className={`w-3 h-3 rounded-full ${colorClass}`}></div>
        <h2 className="font-bold text-text-primary">{title}</h2>
        {eta && (
          <span className={`ml-auto text-xs ${accentBgClass} ${colorClass.replace('bg-', 'text-')} px-2 py-1 rounded-full flex items-center gap-1 font-medium`}>
            <Clock className="w-3 h-3" /> {eta}
          </span>
        )}
      </div>
      
      {vertical === "food" && restaurantName && (
        <div className="mb-3 text-sm text-text-secondary flex items-center gap-1 font-medium bg-surface-elevated px-3 py-2 rounded-lg">
          <MapPin className="w-4 h-4" /> From: {restaurantName}
        </div>
      )}

      <div className="space-y-3">
        {items.map((item, i) => (
          <div key={i} className="bg-surface p-4 rounded-xl border border-border-color flex justify-between shadow-sm hover:shadow transition-shadow">
            <div>
              <div className="text-text-primary text-sm font-semibold">{item.name}</div>
              <div className="text-text-secondary text-xs mt-1 font-medium bg-surface-elevated inline-block px-2 py-0.5 rounded">Qty: {item.quantity}</div>
            </div>
            <div className="text-text-primary font-semibold text-sm">₹{item.price}</div>
          </div>
        ))}
        <div className="pt-4 mt-2 border-t border-border-color flex justify-between font-bold text-lg">
          <span className="text-text-secondary">Subtotal</span>
          <span className="text-text-primary">₹{total}</span>
        </div>
      </div>
    </motion.div>
  );
}
