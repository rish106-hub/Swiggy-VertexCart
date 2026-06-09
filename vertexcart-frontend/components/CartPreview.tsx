"use client";

import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle, ShoppingCart } from "lucide-react";
import { CartState, IntentResult, TurnResponse } from "../lib/types";
import { PoweredBySwiggy } from "./PoweredBySwiggy";
import { CartColumn } from "./CartColumn";
import { AgentReasoning } from "./AgentReasoning";

interface CartPreviewProps {
  cart: CartState;
  intent: IntentResult;
  agentResponse: TurnResponse;
  onLiveCorrection: (text: string) => void;
  onCorrectionSubmit: (text: string) => void;
  onConfirmStart: () => void;
}

const VERTICAL_STYLES = {
  food: {
    accentColor: "#FF5200",
    accentBg: "rgba(255,82,0,0.06)",
    accentBorder: "rgba(255,82,0,0.2)",
    animateX: 20,
  },
  instamart: {
    accentColor: "#00B383",
    accentBg: "rgba(0,179,131,0.06)",
    accentBorder: "rgba(0,179,131,0.2)",
    animateX: -20,
  },
  dineout: {
    accentColor: "#8B5CF6",
    accentBg: "rgba(139,92,246,0.06)",
    accentBorder: "rgba(139,92,246,0.2)",
    animateX: 0,
  },
};

function DineoutSlot({ slot }: { slot: { restaurant: string; slot: string; date: string; cuisine?: string; rating?: string } }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex-1 rounded-2xl overflow-hidden"
      style={{ background: "rgba(139,92,246,0.06)", border: "1px solid rgba(139,92,246,0.2)" }}
    >
      <div className="px-5 pt-4 pb-3 flex items-center gap-2.5" style={{ borderBottom: "1px solid rgba(139,92,246,0.2)" }}>
        <span className="text-xl">🍽️</span>
        <div>
          <h2 className="font-bold text-text-primary text-sm">Dineout Reservation</h2>
          <span className="text-xs text-dineout-purple font-semibold">Free · No prepayment</span>
        </div>
      </div>
      <div className="p-5">
        <div className="bg-background/60 rounded-xl p-4 border border-border-color/50 space-y-2.5">
          <div className="text-text-primary font-bold">{slot.restaurant}</div>
          {slot.cuisine && <div className="text-text-secondary text-sm">{slot.cuisine}</div>}
          <div className="flex items-center gap-3 pt-1">
            <div className="flex items-center gap-1.5 text-dineout-purple text-sm font-semibold bg-dineout-purple/10 px-3 py-1.5 rounded-lg">
              📅 {slot.date}
            </div>
            <div className="flex items-center gap-1.5 text-dineout-purple text-sm font-semibold bg-dineout-purple/10 px-3 py-1.5 rounded-lg">
              🕗 {slot.slot}
            </div>
          </div>
          {slot.rating && (
            <div className="text-xs text-text-secondary font-medium">⭐ {slot.rating} rating</div>
          )}
        </div>
        <div className="mt-3 px-4 py-3 rounded-xl flex justify-between items-center" style={{ background: "rgba(139,92,246,0.12)", border: "1px solid rgba(139,92,246,0.2)" }}>
          <span className="text-text-secondary text-sm font-semibold">Booking fee</span>
          <span className="font-black text-base text-instamart-green">FREE</span>
        </div>
      </div>
    </motion.div>
  );
}

export function CartPreview({ cart, intent, agentResponse, onLiveCorrection, onCorrectionSubmit, onConfirmStart }: CartPreviewProps) {
  const hasInstamart = (cart?.instamart?.items?.length || 0) > 0;
  const hasFood = (cart?.food?.items?.length || 0) > 0;
  const hasDineout = (cart?.dineout_slots?.length || 0) > 0;
  const hasAny = hasInstamart || hasFood || hasDineout;

  const totalGOV =
    (cart?.instamart?.subtotal || 0) + (cart?.food?.subtotal || 0);

  return (
    <div className="min-h-screen pb-32 px-4 md:px-6 max-w-7xl mx-auto pt-6">
      {/* Top bar */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <ShoppingCart className="w-4 h-4 text-text-secondary" />
          <span className="text-text-secondary text-sm font-semibold">Your Cart</span>
          {totalGOV > 0 && (
            <span className="text-xs bg-surface-elevated border border-border-color px-2.5 py-1 rounded-full text-text-secondary font-medium">
              ₹{totalGOV} total
            </span>
          )}
        </div>
        <PoweredBySwiggy />
      </div>

      <div className="flex flex-col xl:flex-row gap-6">
        {/* Main cart area */}
        <div className="flex-1 min-w-0">
          {/* Agent message */}
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-5 p-4 bg-surface rounded-2xl border border-border-color flex items-start gap-3"
          >
            <div className="w-8 h-8 rounded-xl bg-swiggy-orange/15 flex items-center justify-center shrink-0">
              <span className="text-sm">🤖</span>
            </div>
            <p className="text-text-primary text-sm leading-relaxed pt-0.5">{agentResponse.agent_response}</p>
          </motion.div>

          {/* Cart columns */}
          <AnimatePresence mode="popLayout">
            {hasAny ? (
              <div className="flex flex-col lg:flex-row gap-4">
                {hasInstamart && cart.instamart && (
                  <CartColumn
                    vertical="instamart"
                    title="Instamart"
                    items={cart.instamart.items}
                    total={cart.instamart.subtotal}
                    eta={cart.instamart.status}
                    {...VERTICAL_STYLES.instamart}
                  />
                )}
                {hasFood && cart.food && (
                  <CartColumn
                    vertical="food"
                    title="Swiggy Food"
                    items={cart.food.items}
                    total={cart.food.subtotal}
                    eta={cart.food.status}
                    restaurantName={cart.food.restaurantName}
                    {...VERTICAL_STYLES.food}
                  />
                )}
                {hasDineout && cart.dineout_slots && cart.dineout_slots.length > 0 && (
                  <DineoutSlot slot={cart.dineout_slots[0] as { restaurant: string; slot: string; date: string; cuisine?: string; rating?: string }} />
                )}
              </div>
            ) : (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-center py-16 text-text-secondary"
              >
                <div className="text-4xl mb-3">🛒</div>
                <p className="font-medium">Cart is empty — try a different correction</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Right sidebar */}
        <div className="w-full xl:w-72 shrink-0">
          <AgentReasoning
            intent={intent}
            onLiveCorrection={onLiveCorrection}
            onCorrectionSubmit={onCorrectionSubmit}
          />
        </div>
      </div>

      {/* Sticky bottom CTA */}
      <div className="fixed bottom-0 left-0 right-0 z-30 bg-background/80 backdrop-blur-md border-t border-border-color">
        <div className="max-w-7xl mx-auto px-4 md:px-6 py-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-text-secondary text-sm">
            <span className="w-2 h-2 rounded-full bg-instamart-green live-dot" />
            <span className="font-medium">Live cart · COD only</span>
          </div>
          <AnimatePresence>
            {hasAny && (
              <motion.button
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.96 }}
                onClick={onConfirmStart}
                className="btn-ripple px-7 py-3.5 bg-swiggy-orange text-white font-bold rounded-2xl flex items-center gap-2 shadow-lg text-sm"
                style={{ boxShadow: "0 4px 20px rgba(255,82,0,0.4)" }}
              >
                Review & Confirm
                <CheckCircle className="w-4 h-4" />
              </motion.button>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
