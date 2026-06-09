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
  const verticalsToConfirm: string[] = [];
  if ((cart?.instamart?.items?.length || 0) > 0) verticalsToConfirm.push("instamart");
  if ((cart?.food?.items?.length || 0) > 0) verticalsToConfirm.push("food");
  if ((cart?.dineout_slots?.length || 0) > 0) verticalsToConfirm.push("dineout");

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
          items: cart.instamart?.items || [],
          total: cart.instamart?.subtotal || 0,
          warnings: (cart.instamart?.subtotal || 0) < 99 ? "Total below ₹99 minimum." : null,
        };
      case "food":
        return {
          title: "Confirm Food Delivery",
          color: "bg-swiggy-orange",
          text: "text-swiggy-orange",
          items: cart.food?.items || [],
          total: cart.food?.subtotal || 0,
          warnings: (cart.food?.subtotal || 0) > 1000 ? "Cart limit (₹1000) exceeded." : `₹${cart.food?.subtotal || 0} used of ₹1000 limit.`,
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
    <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex flex-col items-center pt-24 px-4">
      <div className="absolute top-6 right-6">
        <PoweredBySwiggy />
      </div>
      
      <div className="text-text-secondary text-sm font-semibold uppercase tracking-wider mb-6 bg-surface px-4 py-2 rounded-full border border-border-color shadow-sm">
        Step {currentIndex + 1} of {verticalsToConfirm.length}
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={currentVertical}
          initial={{ opacity: 0, y: 20, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -20, scale: 0.95 }}
          transition={{ duration: 0.2 }}
          className="w-full max-w-md bg-white border border-border-color rounded-3xl p-8 shadow-xl"
        >
          <h2 className={`text-2xl font-extrabold mb-8 pb-4 border-b border-border-color ${details.text}`}>{details.title}</h2>
          
          <div className="space-y-4 mb-8 max-h-60 overflow-y-auto pr-2 custom-scrollbar">
             {details.items.map((item, i) => (
                <div key={i} className="flex justify-between items-center text-text-primary text-sm font-medium bg-surface-elevated p-3 rounded-xl border border-border-color/50">
                  <span><span className="text-text-secondary mr-2">{item.quantity}x</span> {item.name}</span>
                  <span className="font-bold">₹{item.price}</span>
                </div>
             ))}
          </div>

          <div className="border-t border-border-color pt-6 mb-8">
             <div className="flex justify-between items-center text-xl font-extrabold text-text-primary mb-3">
                <span>Total (COD)</span>
                <span>₹{details.total}</span>
             </div>
             {details.warnings && (
               <div className="text-xs text-text-secondary flex items-start gap-1.5 bg-surface-elevated p-2 rounded-lg font-medium">
                 <AlertCircle className="w-4 h-4 mt-px shrink-0 text-amber-500" />
                 {details.warnings}
               </div>
             )}
          </div>

          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl text-red-600 text-sm font-medium flex items-start gap-2">
              <AlertCircle className="w-5 h-5 shrink-0" />
              {error}
            </div>
          )}

          <button
            onClick={handleConfirm}
            disabled={isConfirming || (currentVertical === 'food' && details.total > 1000) || (currentVertical === 'instamart' && details.total < 99)}
            className={`w-full py-4 rounded-2xl font-bold flex items-center justify-center gap-2 text-white disabled:opacity-50 transition-all shadow-md hover:shadow-lg active:scale-95 ${details.color}`}
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
