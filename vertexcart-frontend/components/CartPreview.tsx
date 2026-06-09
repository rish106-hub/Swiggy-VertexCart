"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { Send, Clock, MapPin, CheckCircle } from "lucide-react";
import { CartState, IntentResult, TurnResponse } from "../lib/types";
import { PoweredBySwiggy } from "./PoweredBySwiggy";

interface CartPreviewProps {
  cart: CartState;
  intent: IntentResult;
  agentResponse: TurnResponse;
  onCorrect: (text: string) => void;
  onConfirmStart: () => void;
}

export function CartPreview({ cart, intent, agentResponse, onCorrect, onConfirmStart }: CartPreviewProps) {
  const [correctionText, setCorrectionText] = useState("");

  const handleCorrection = (e: React.FormEvent) => {
    e.preventDefault();
    if (correctionText.trim()) {
      onCorrect(correctionText.trim());
      setCorrectionText("");
    }
  };

  const hasInstamart = cart?.instamart?.items?.length > 0;
  const hasFood = cart?.food?.items?.length > 0;

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
          {hasInstamart && (
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex-1"
            >
              <div className="flex items-center gap-2 mb-4 border-b border-instamart-green/30 pb-2">
                <div className="w-3 h-3 rounded-full bg-instamart-green"></div>
                <h2 className="font-semibold text-white">Instamart</h2>
                {cart.instamart.eta && (
                  <span className="ml-auto text-xs text-instamart-green flex items-center gap-1 bg-instamart-green/10 px-2 py-1 rounded-full">
                    <Clock className="w-3 h-3" /> {cart.instamart.eta}
                  </span>
                )}
              </div>
              <div className="space-y-3">
                {cart.instamart.items.map((item, i) => (
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
                  <span className="text-white">₹{cart.instamart.total}</span>
                </div>
              </div>
            </motion.div>
          )}

          {/* Food Column */}
          {hasFood && (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex-1"
            >
              <div className="flex items-center gap-2 mb-4 border-b border-swiggy-orange/30 pb-2">
                <div className="w-3 h-3 rounded-full bg-swiggy-orange"></div>
                <h2 className="font-semibold text-white">Food Delivery</h2>
                {cart.food.eta && (
                  <span className="ml-auto text-xs text-swiggy-orange flex items-center gap-1 bg-swiggy-orange/10 px-2 py-1 rounded-full">
                    <Clock className="w-3 h-3" /> {cart.food.eta}
                  </span>
                )}
              </div>
              {cart.food.restaurantName && (
                <div className="mb-3 text-sm text-text-secondary flex items-center gap-1">
                   <MapPin className="w-3 h-3" /> From: {cart.food.restaurantName}
                </div>
              )}
              <div className="space-y-3">
                {cart.food.items.map((item, i) => (
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
                  <span className="text-white">₹{cart.food.total}</span>
                </div>
              </div>
            </motion.div>
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
        <div className="bg-surface border border-surface-elevated rounded-xl p-5 sticky top-8">
          <h3 className="text-white font-medium mb-4">Intent Breakdown</h3>
          <div className="space-y-4 mb-6">
             {intent.entities.map((ent, i) => (
               <div key={i} className="flex justify-between items-center text-sm border-b border-surface-elevated pb-2">
                 <span className="text-text-secondary">&quot;{ent.text}&quot;</span>
                 <span className={`px-2 py-0.5 rounded text-xs
                    ${ent.vertical === 'instamart' ? 'bg-instamart-green/20 text-instamart-green' : 
                      ent.vertical === 'food' ? 'bg-swiggy-orange/20 text-swiggy-orange' : 
                      'bg-dineout-purple/20 text-dineout-purple'}`}
                 >
                    {ent.vertical}
                 </span>
               </div>
             ))}
          </div>

          <form onSubmit={handleCorrection} className="mt-8">
             <label className="text-xs text-text-secondary mb-2 block uppercase tracking-wider">Need to change something?</label>
             <div className="relative">
               <input 
                 type="text"
                 value={correctionText}
                 onChange={(e) => setCorrectionText(e.target.value)}
                 placeholder="e.g. drop the dessert..."
                 className="w-full bg-background border border-surface-elevated rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-swiggy-orange pr-10"
               />
               <button 
                 type="submit"
                 disabled={!correctionText.trim()}
                 className="absolute right-2 top-1/2 -translate-y-1/2 text-text-secondary hover:text-white disabled:opacity-50"
               >
                  <Send className="w-4 h-4" />
               </button>
             </div>
          </form>
        </div>
      </div>
    </div>
  );
}
