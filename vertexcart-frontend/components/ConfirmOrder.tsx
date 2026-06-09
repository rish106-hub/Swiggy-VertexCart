"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, Loader2, AlertCircle } from "lucide-react";
import { CartState } from "../lib/types";
import { PoweredBySwiggy } from "./PoweredBySwiggy";

interface ConfirmOrderProps {
  cart: CartState;
  onConfirm: (vertical: string) => Promise<void>;
  onAllConfirmed: () => void;
}

export function ConfirmOrder({ cart, onConfirm, onAllConfirmed }: ConfirmOrderProps) {
  const verticalsToConfirm = [];
  if (cart?.instamart?.items?.length > 0) verticalsToConfirm.push("instamart");
  if (cart?.food?.items?.length > 0) verticalsToConfirm.push("food");
  if (cart?.dineout?.slots) verticalsToConfirm.push("dineout");

  const [currentIndex, setCurrentIndex] = useState(0);
  const [isConfirming, setIsConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const currentVertical = verticalsToConfirm[currentIndex];

  const handleConfirm = async () => {
    if (!currentVertical) return;
    
    setIsConfirming(true);
    setError(null);
    try {
      await onConfirm(currentVertical);
      // Wait a moment to show success state before moving to next
      setTimeout(() => {
        if (currentIndex < verticalsToConfirm.length - 1) {
          setCurrentIndex(c => c + 1);
          setIsConfirming(false);
        } else {
          onAllConfirmed();
        }
      }, 1000);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : "Failed to place order.";
      setError(errorMessage);
      setIsConfirming(false);
    }
  };

  if (!currentVertical) return null;

  const getVerticalDetails = () => {
    switch (currentVertical) {
      case "instamart":
        return {
          title: "Confirm Instamart Groceries",
          color: "bg-instamart-green",
          text: "text-instamart-green",
          items: cart.instamart.items,
          total: cart.instamart.total,
          warnings: cart.instamart.total < 99 ? "Total below ₹99 minimum." : null,
        };
      case "food":
        return {
          title: "Confirm Food Delivery",
          color: "bg-swiggy-orange",
          text: "text-swiggy-orange",
          items: cart.food.items,
          total: cart.food.total,
          warnings: cart.food.total > 1000 ? "Cart limit (₹1000) exceeded." : `₹${cart.food.total} used of ₹1000 limit.`,
        };
      case "dineout":
        return {
          title: "Confirm Dineout Reservation",
          color: "bg-dineout-purple",
          text: "text-dineout-purple",
          items: [],
          total: 0,
          warnings: null,
        };
      default: return null;
    }
  };

  const details = getVerticalDetails();
  if (!details) return null;

  return (
    <div className="fixed inset-0 bg-background z-50 flex flex-col items-center pt-20 px-4">
      <div className="absolute top-6 right-6">
        <PoweredBySwiggy />
      </div>
      
      <div className="text-text-secondary text-sm mb-8">
        Step {currentIndex + 1} of {verticalsToConfirm.length}
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={currentVertical}
          initial={{ opacity: 0, x: 50 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -50 }}
          className="w-full max-w-md bg-surface border border-surface-elevated rounded-2xl p-6"
        >
          <h2 className={`text-2xl font-bold mb-6 ${details.text}`}>{details.title}</h2>
          
          <div className="space-y-4 mb-8 max-h-60 overflow-y-auto pr-2">
             {details.items.map((item, i) => (
                <div key={i} className="flex justify-between items-center text-white text-sm">
                  <span>{item.quantity}x {item.name}</span>
                  <span>₹{item.price}</span>
                </div>
             ))}
          </div>

          <div className="border-t border-surface-elevated pt-4 mb-6">
             <div className="flex justify-between items-center text-lg font-bold text-white mb-2">
                <span>Total (COD)</span>
                <span>₹{details.total}</span>
             </div>
             {details.warnings && (
               <div className="text-xs text-text-secondary flex items-start gap-1">
                 <AlertCircle className="w-3 h-3 mt-0.5 shrink-0" />
                 {details.warnings}
               </div>
             )}
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
              {error}
            </div>
          )}

          <button
            onClick={handleConfirm}
            disabled={isConfirming || (currentVertical === 'food' && details.total > 1000) || (currentVertical === 'instamart' && details.total < 99)}
            className={`w-full py-4 rounded-xl font-bold flex items-center justify-center gap-2 text-white disabled:opacity-50 transition-opacity ${details.color}`}
          >
            {isConfirming ? (
              <>Placing Order <Loader2 className="w-5 h-5 animate-spin" /></>
            ) : (
              <>Place Order <CheckCircle2 className="w-5 h-5" /></>
            )}
          </button>
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
