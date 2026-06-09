import React from "react";
import { CartItem } from "../lib/types";
import { Clock, MapPin } from "lucide-react";
import { motion } from "framer-motion";

interface CartColumnProps {
  vertical: "instamart" | "food" | "dineout";
  title: string;
  items: CartItem[];
  total: number;
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
        <h2 className="font-semibold text-white">{title}</h2>
        {eta && (
          <span className={`ml-auto text-xs ${accentBgClass} ${colorClass.replace('bg-', 'text-')} px-2 py-1 rounded-full flex items-center gap-1`}>
            <Clock className="w-3 h-3" /> {eta}
          </span>
        )}
      </div>
      
      {vertical === "food" && restaurantName && (
        <div className="mb-3 text-sm text-text-secondary flex items-center gap-1">
          <MapPin className="w-3 h-3" /> From: {restaurantName}
        </div>
      )}

      <div className="space-y-3">
        {items.map((item, i) => (
          <div key={i} className="bg-surface p-3 rounded-lg border border-surface-elevated flex justify-between">
            <div>
              <div className="text-white text-sm font-medium">{item.name}</div>
              <div className="text-text-secondary text-xs mt-1">Qty: {item.quantity}</div>
            </div>
            <div className="text-white text-sm">₹{item.price}</div>
          </div>
        ))}
        <div className="pt-2 border-t border-surface-elevated flex justify-between font-medium">
          <span className="text-text-secondary">Subtotal</span>
          <span className="text-white">₹{total}</span>
        </div>
      </div>
    </motion.div>
  );
}
