"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, Loader2, AlertCircle, ChevronLeft, Shield } from "lucide-react";
import { CartState } from "../lib/types";
import { PoweredBySwiggy } from "./PoweredBySwiggy";

interface ConfirmOrderProps {
  cart: CartState;
  onConfirm: (vertical: string) => Promise<void>;
  onAllConfirmed: () => void;
  onBack: () => void;
}

const VERTICAL_CONFIG = {
  instamart: {
    title: "Instamart Groceries",
    emoji: "🛒",
    accentColor: "#00B383",
    accentBg: "rgba(0,179,131,0.08)",
    accentBorder: "rgba(0,179,131,0.25)",
    gradientFrom: "#00B383",
    gradientTo: "#00D49B",
  },
  food: {
    title: "Food Delivery",
    emoji: "🍔",
    accentColor: "#FF5200",
    accentBg: "rgba(255,82,0,0.08)",
    accentBorder: "rgba(255,82,0,0.25)",
    gradientFrom: "#FF5200",
    gradientTo: "#FF7A35",
  },
  dineout: {
    title: "Dineout Reservation",
    emoji: "🍽️",
    accentColor: "#8B5CF6",
    accentBg: "rgba(139,92,246,0.08)",
    accentBorder: "rgba(139,92,246,0.25)",
    gradientFrom: "#8B5CF6",
    gradientTo: "#A78BFA",
  },
};

export function ConfirmOrder({ cart, onConfirm, onAllConfirmed, onBack }: ConfirmOrderProps) {
  const verticalsToConfirm: string[] = [];
  if ((cart?.instamart?.items?.length || 0) > 0) verticalsToConfirm.push("instamart");
  if ((cart?.food?.items?.length || 0) > 0) verticalsToConfirm.push("food");
  if ((cart?.dineout_slots?.length || 0) > 0) verticalsToConfirm.push("dineout");

  const [currentIndex, setCurrentIndex] = useState(0);
  const [isConfirming, setIsConfirming] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const currentVertical = verticalsToConfirm[currentIndex];
  const config = VERTICAL_CONFIG[currentVertical as keyof typeof VERTICAL_CONFIG];

  const getItems = () => {
    if (currentVertical === "instamart") return cart.instamart?.items || [];
    if (currentVertical === "food") return cart.food?.items || [];
    return [];
  };

  const getTotal = () => {
    if (currentVertical === "instamart") return cart.instamart?.subtotal || 0;
    if (currentVertical === "food") return cart.food?.subtotal || 0;
    return 0;
  };

  const getWarning = () => {
    if (currentVertical === "food" && getTotal() > 1000) return "Cart exceeds ₹1000 limit for this session.";
    if (currentVertical === "instamart" && getTotal() < 99) return "Add more items to meet ₹99 minimum.";
    return null;
  };

  const isDisabled = () => {
    if (currentVertical === "food" && getTotal() > 1000) return true;
    if (currentVertical === "instamart" && getTotal() < 99) return true;
    return false;
  };

  const handleConfirm = async () => {
    if (!currentVertical || isDisabled()) return;
    setIsConfirming(true);
    setError(null);
    try {
      await onConfirm(currentVertical);
      setIsSuccess(true);
      await new Promise(r => setTimeout(r, 900));

      if (currentIndex < verticalsToConfirm.length - 1) {
        setCurrentIndex(c => c + 1);
        setIsConfirming(false);
        setIsSuccess(false);
      } else {
        onAllConfirmed();
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to place order.");
      setIsConfirming(false);
    }
  };

  if (!currentVertical || !config) return null;

  const items = getItems();
  const total = getTotal();
  const warning = getWarning();
  const dineoutSlot = currentVertical === "dineout" && cart.dineout_slots?.[0]
    ? (cart.dineout_slots[0] as { restaurant: string; slot: string; date: string })
    : null;

  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center px-4 bottom-sheet-overlay">
      {/* Back button */}
      <button
        onClick={onBack}
        className="absolute top-6 left-6 flex items-center gap-1.5 text-text-secondary hover:text-text-primary text-sm font-medium transition-colors"
      >
        <ChevronLeft className="w-4 h-4" />
        Back to cart
      </button>

      <div className="absolute top-6 right-6">
        <PoweredBySwiggy />
      </div>

      {/* Step dots */}
      <div className="flex gap-2 mb-8">
        {verticalsToConfirm.map((v, i) => {
          const c = VERTICAL_CONFIG[v as keyof typeof VERTICAL_CONFIG];
          return (
            <motion.div
              key={v}
              animate={{ scale: i === currentIndex ? 1.2 : 1, opacity: i < currentIndex ? 0.4 : 1 }}
              className="w-2.5 h-2.5 rounded-full transition-colors"
              style={{ background: i <= currentIndex ? c?.accentColor : "#2E2E2E" }}
            />
          );
        })}
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={currentVertical}
          initial={{ opacity: 0, y: 30, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -30, scale: 0.95 }}
          transition={{ type: "spring", stiffness: 350, damping: 28 }}
          className="w-full max-w-md rounded-3xl overflow-hidden shadow-2xl"
          style={{ background: "#1A1A1A", border: `1px solid ${config.accentBorder}` }}
        >
          {/* Header */}
          <div
            className="px-6 py-5 flex items-center gap-3"
            style={{
              background: `linear-gradient(135deg, ${config.gradientFrom}18, ${config.gradientTo}08)`,
              borderBottom: `1px solid ${config.accentBorder}`,
            }}
          >
            <span className="text-2xl">{config.emoji}</span>
            <div className="flex-1">
              <h2 className="text-text-primary font-black text-lg">{config.title}</h2>
              <p className="text-text-secondary text-xs mt-0.5 font-medium">
                Step {currentIndex + 1} of {verticalsToConfirm.length} · COD payment
              </p>
            </div>
          </div>

          {/* Body */}
          <div className="p-6">
            {/* Items or slot info */}
            {dineoutSlot ? (
              <div className="bg-surface-elevated rounded-2xl p-4 mb-5 border border-border-color space-y-2">
                <div className="font-bold text-text-primary">{dineoutSlot.restaurant}</div>
                <div className="flex gap-2">
                  <span className="text-xs bg-dineout-purple/10 text-dineout-purple px-2.5 py-1 rounded-lg font-semibold">📅 {dineoutSlot.date}</span>
                  <span className="text-xs bg-dineout-purple/10 text-dineout-purple px-2.5 py-1 rounded-lg font-semibold">🕗 {dineoutSlot.slot}</span>
                </div>
                <div className="text-xs text-instamart-green font-semibold">✓ Free reservation — no payment needed</div>
              </div>
            ) : (
              <div className="max-h-52 overflow-y-auto space-y-2.5 mb-5 pr-1">
                {items.map((item, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between bg-surface-elevated px-4 py-3 rounded-xl border border-border-color"
                  >
                    <div>
                      <span className="text-text-secondary text-xs font-medium mr-2">{item.quantity}×</span>
                      <span className="text-text-primary text-sm font-medium">{item.name}</span>
                    </div>
                    <span className="text-text-primary font-bold text-sm">₹{item.price * item.quantity}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Total row */}
            {!dineoutSlot && (
              <div className="flex justify-between items-center px-4 py-3.5 rounded-2xl mb-4" style={{ background: config.accentBg, border: `1px solid ${config.accentBorder}` }}>
                <span className="text-text-secondary font-semibold text-sm">Total (Cash on Delivery)</span>
                <span className="font-black text-xl text-text-primary">₹{total}</span>
              </div>
            )}

            {/* Food cap progress */}
            {currentVertical === "food" && total <= 1000 && (
              <div className="mb-4">
                <div className="flex justify-between text-xs text-text-secondary mb-1.5 font-medium">
                  <span>Session limit usage</span>
                  <span>₹{total} / ₹1000</span>
                </div>
                <div className="h-1.5 bg-surface-elevated rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${(total / 1000) * 100}%` }}
                    transition={{ duration: 0.6, ease: "easeOut" }}
                    className="h-full rounded-full"
                    style={{ background: `linear-gradient(90deg, ${config.gradientFrom}, ${config.gradientTo})` }}
                  />
                </div>
              </div>
            )}

            {/* Warning */}
            {warning && (
              <div className="mb-4 flex items-start gap-2 bg-amber-500/10 border border-amber-500/25 rounded-xl px-3 py-2.5 text-amber-400 text-xs font-medium">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                {warning}
              </div>
            )}

            {/* Error */}
            {error && (
              <div className="mb-4 flex items-start gap-2 bg-red-500/10 border border-red-500/25 rounded-xl px-3 py-2.5 text-red-400 text-sm font-medium">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                {error}
              </div>
            )}

            {/* Confirm button */}
            <motion.button
              onClick={handleConfirm}
              disabled={isConfirming || isDisabled()}
              whileHover={!isConfirming && !isDisabled() ? { scale: 1.02 } : {}}
              whileTap={!isConfirming && !isDisabled() ? { scale: 0.97 } : {}}
              className="btn-ripple w-full py-4 rounded-2xl font-black text-white flex items-center justify-center gap-2.5 text-base disabled:opacity-40 transition-all shadow-lg"
              style={{
                background: isSuccess
                  ? "linear-gradient(135deg, #00B383, #00D49B)"
                  : `linear-gradient(135deg, ${config.gradientFrom}, ${config.gradientTo})`,
                boxShadow: `0 6px 24px ${config.accentColor}40`,
              }}
            >
              {isSuccess ? (
                <>
                  <CheckCircle2 className="w-5 h-5" />
                  Order Placed!
                </>
              ) : isConfirming ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Placing order...
                </>
              ) : (
                <>
                  <Shield className="w-5 h-5" />
                  {currentVertical === "dineout" ? "Confirm Reservation" : "Place Order"}
                </>
              )}
            </motion.button>

            <p className="text-center text-xs text-text-secondary/50 mt-3 font-medium">
              Secure · COD · Powered by Swiggy
            </p>
          </div>
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
