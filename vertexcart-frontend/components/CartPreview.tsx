"use client";

import React from "react";
import { motion } from "framer-motion";
import { CheckCircle } from "lucide-react";
import { CartState, IntentResult, TurnResponse } from "../lib/types";
import { PoweredBySwiggy } from "./PoweredBySwiggy";
import { CartColumn } from "./CartColumn";
import { AgentReasoning } from "./AgentReasoning";

interface CartPreviewProps {
  cart: CartState;
  intent: IntentResult;
  agentResponse: TurnResponse;
  onCorrect: (text: string) => void;
  onConfirmStart: () => void;
}

export function CartPreview({ cart, intent, agentResponse, onCorrect, onConfirmStart }: CartPreviewProps) {
  const hasInstamart = (cart?.instamart?.items?.length || 0) > 0;
  const hasFood = (cart?.food?.items?.length || 0) > 0;

  return (
    <div className="min-h-screen pb-24 px-4 md:px-8 max-w-7xl mx-auto flex flex-col md:flex-row gap-8 pt-8 relative">
      <div className="absolute top-4 right-4 z-10">
        <PoweredBySwiggy />
      </div>

      {/* Main Cart Area */}
      <div className="flex-1">
        <motion.div
           initial={{ opacity: 0, y: -10 }}
           animate={{ opacity: 1, y: 0 }}
           className="mb-8 p-4 bg-surface rounded-xl border border-surface-elevated flex items-start gap-4"
        >
          <div className="w-8 h-8 rounded-full bg-surface-elevated flex items-center justify-center shrink-0">🤖</div>
          <p className="text-white pt-1">{agentResponse.agent_response}</p>
        </motion.div>

        <div className="flex flex-col lg:flex-row gap-6">
          {/* Instamart Column */}
          {hasInstamart && cart.instamart && (
            <CartColumn
              vertical="instamart"
              title="Instamart"
              items={cart.instamart.items}
              total={cart.instamart.subtotal}
              eta={cart.instamart.status}
              colorClass="bg-instamart-green"
              borderColorClass="border-instamart-green/30"
              accentBgClass="bg-instamart-green/10"
              animateX={-20}
            />
          )}

          {/* Food Column */}
          {hasFood && cart.food && (
            <CartColumn
              vertical="food"
              title="Food Delivery"
              items={cart.food.items}
              total={cart.food.subtotal}
              eta={cart.food.status}
              restaurantName={cart.food.restaurantName}
              colorClass="bg-swiggy-orange"
              borderColorClass="border-swiggy-orange/30"
              accentBgClass="bg-swiggy-orange/10"
              animateX={20}
            />
          )}
        </div>
        
        {/* Bottom CTA Area */}
        <div className="fixed bottom-0 left-0 right-0 bg-background border-t border-surface-elevated p-4 flex justify-center z-20">
           <div className="max-w-7xl w-full flex flex-col md:flex-row items-center justify-between px-4 md:px-8 gap-4">
              <div className="text-text-secondary text-sm">
                 Live cart data from Swiggy
              </div>
              {agentResponse.requires_confirmation && (
                <button
                  onClick={onConfirmStart}
                  className="px-8 py-3 bg-white text-black font-semibold rounded-full hover:bg-gray-200 transition-colors flex items-center gap-2"
                >
                   Review & Confirm Orders <CheckCircle className="w-4 h-4" />
                </button>
              )}
           </div>
        </div>
      </div>

      {/* Right Sidebar: Agent Reasoning */}
      <div className="w-full md:w-80 shrink-0">
        <AgentReasoning intent={intent} onCorrect={onCorrect} />
      </div>
    </div>
  );
}
