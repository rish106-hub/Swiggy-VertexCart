"use client";

import React, { useState } from "react";
import { api } from "../lib/api";
import { IntentResult, TurnResponse, CartState } from "../lib/types";
import { IntentInput } from "../components/IntentInput";
import { ParsingState } from "../components/ParsingState";
import { CartPreview } from "../components/CartPreview";
import { ConfirmOrder } from "../components/ConfirmOrder";
import { OrderStatus } from "../components/OrderStatus";

type AppStep = "input" | "parsing" | "preview" | "confirming" | "status";

export default function Home() {
  const [step, setStep] = useState<AppStep>("input");
  const [sessionId, setSessionId] = useState<string | null>(null);
  
  // State for Intent flow
  const [query, setQuery] = useState("");
  const [intent, setIntent] = useState<IntentResult | undefined>();
  const [agentResponse, setAgentResponse] = useState<TurnResponse | undefined>();
  const [cart, setCart] = useState<CartState | undefined>();
  
  // UI flags
  const [isTakingLong, setIsTakingLong] = useState(false);

  // Generate a random user ID for the session (in a real app, this comes from auth)
  const [userId] = useState(() => `user_${Math.random().toString(36).substr(2, 9)}`);

  const handleIntentSubmit = async (text: string) => {
    setQuery(text);
    setStep("parsing");
    
    // Start a timer to show skeleton loaders if it takes too long
    const timeoutId = setTimeout(() => setIsTakingLong(true), 1500);

    try {
      // 1. Create Session
      let currentSessionId = sessionId;
      if (!currentSessionId) {
         const sessionRes = await api.createSession(userId);
         currentSessionId = sessionRes.session_id;
         setSessionId(currentSessionId);
      }

      // 2. Parse Intent (optimistic update for UI lanes)
      const parsedIntent = await api.parseIntent(text, userId);
      setIntent(parsedIntent);
      
      // 3. Process Turn (this hits the MCP tools)
      const turnRes = await api.sendTurn(currentSessionId, text);
      setAgentResponse(turnRes);

      // 4. Fetch live cart state
      const liveCart = await api.getCart(currentSessionId);
      setCart(liveCart);

      clearTimeout(timeoutId);
      setStep("preview");

    } catch (error) {
      console.error("Flow failed:", error);
      // Fallback for demo purposes if backend fails
      alert("Backend error. Check console. Ensure Phase 1 is running.");
      setStep("input");
    }
  };

  const handleCorrection = async (text: string) => {
    if (!sessionId) return;
    setStep("parsing");
    setQuery(text);
    setIntent(undefined); // Reset to show loaders
    
    try {
      const parsedIntent = await api.parseIntent(text, userId);
      setIntent(parsedIntent);
      
      const turnRes = await api.sendTurn(sessionId, text);
      setAgentResponse(turnRes);

      const liveCart = await api.getCart(sessionId);
      setCart(liveCart);
      
      setStep("preview");
    } catch (error) {
      console.error("Correction failed:", error);
      setStep("preview"); // Go back to preview on fail
    }
  };

  const handleConfirmOrder = async (vertical: string) => {
    if (!sessionId) return;
    await api.confirmOrder(sessionId, vertical);
  };

  return (
    <main className="min-h-screen bg-background">
      {step === "input" && (
        <IntentInput onSubmit={handleIntentSubmit} />
      )}

      {step === "parsing" && (
        <ParsingState 
           query={query} 
           intent={intent} 
           isTakingLong={isTakingLong} 
        />
      )}

      {step === "preview" && cart && intent && agentResponse && (
        <CartPreview
          cart={cart}
          intent={intent}
          agentResponse={agentResponse}
          onCorrect={handleCorrection}
          onConfirmStart={() => setStep("confirming")}
        />
      )}

      {step === "confirming" && cart && (
        <ConfirmOrder
          cart={cart}
          onConfirm={handleConfirmOrder}
          onAllConfirmed={() => setStep("status")}
        />
      )}

      {step === "status" && sessionId && (
        <OrderStatus sessionId={sessionId} />
      )}
    </main>
  );
}
