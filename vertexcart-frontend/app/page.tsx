"use client";

import React, { useState, useCallback } from "react";
import { api } from "../lib/api";
import { parseIntentMock, buildMockCart, buildAgentResponse, applyCorrection } from "../lib/mock-engine";
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

  const [query, setQuery] = useState("");
  const [intent, setIntent] = useState<IntentResult | undefined>();
  const [agentResponse, setAgentResponse] = useState<TurnResponse | undefined>();
  const [cart, setCart] = useState<CartState | undefined>();

  const [userId] = useState(() => `user_${Math.random().toString(36).substr(2, 9)}`);

  const handleIntentSubmit = async (text: string) => {
    setQuery(text);
    setStep("parsing");

    // Optimistic: parse intent client-side immediately so lanes appear fast
    const optimisticIntent = parseIntentMock(text);
    setIntent(optimisticIntent);

    let sid: string | null = null;
    try {
      // Always create a fresh session for each new top-level query
      // This prevents stale mock state from a previous flow
      const sessionRes = await api.createSession(userId);
      sid = sessionRes.session_id;
      setSessionId(sid);

      // These two run in parallel — intent from server can override optimistic
      const [serverIntent, turnRes] = await Promise.all([
        api.parseIntent(text, userId).catch(() => optimisticIntent),
        api.sendTurn(sid!, text),
      ]);

      setIntent(serverIntent);
      setAgentResponse(turnRes);

      if (turnRes.requires_clarification) {
        setStep("input");
        return;
      }

      const liveCart = await api.getCart(sid!);
      setCart(liveCart);
      setStep("preview");
    } catch {
      // Full client-side fallback
      const clientCart = buildMockCart(text);
      if (sid) api.updateMockCart(sid, clientCart);
      setCart(clientCart);
      setAgentResponse({
        agent_response: buildAgentResponse(text, clientCart),
        verticals_active: optimisticIntent.entities.map(e => e.vertical),
        cart_summary: {},
        requires_confirmation: true,
        requires_clarification: false,
      });
      setStep("preview");
    }
  };

  // Real-time correction: update cart immediately from correction text
  // Called on every keystroke from sidebar — no network call needed
  const handleLiveCorrection = useCallback((correctionText: string) => {
    if (!cart || !correctionText.trim()) return;
    const updated = applyCorrection(query, correctionText, cart);
    setCart(updated);
    if (sessionId) api.updateMockCart(sessionId, updated);
    // Re-derive intent from correction text only (not appended to original)
    const newIntent = parseIntentMock(correctionText);
    setIntent(prev => prev ? { ...prev, entities: newIntent.entities.length ? newIntent.entities : prev.entities } : newIntent);
  }, [cart, query, sessionId]);

  // Final correction submit: triggers a full server turn
  const handleCorrectionSubmit = async (text: string) => {
    if (!sessionId) return;
    setStep("parsing");

    const combined = `${query} — correction: ${text}`;
    const newIntent = parseIntentMock(combined);
    setIntent(newIntent);

    try {
      const turnRes = await api.sendTurn(sessionId, text);
      setAgentResponse(turnRes);
      const liveCart = await api.getCart(sessionId);
      setCart(liveCart);
    } catch {
      // Client-side correction fallback — already applied via handleLiveCorrection
      setAgentResponse(prev => prev
        ? { ...prev, agent_response: `Updated: ${text}` }
        : undefined
      );
    }
    setStep("preview");
  };

  const handleConfirmOrder = async (vertical: string) => {
    if (!sessionId) return;
    await api.confirmOrder(sessionId, vertical);
  };

  const handleReset = () => {
    setStep("input");
    setQuery("");
    setIntent(undefined);
    setAgentResponse(undefined);
    setCart(undefined);
    setSessionId(null);
  };

  return (
    <main className="min-h-screen bg-background">
      {step === "input" && (
        <IntentInput onSubmit={handleIntentSubmit} />
      )}

      {step === "parsing" && (
        <ParsingState query={query} intent={intent} />
      )}

      {step === "preview" && cart && intent && agentResponse && (
        <CartPreview
          cart={cart}
          intent={intent}
          agentResponse={agentResponse}
          onLiveCorrection={handleLiveCorrection}
          onCorrectionSubmit={handleCorrectionSubmit}
          onConfirmStart={() => setStep("confirming")}
        />
      )}

      {step === "confirming" && cart && (
        <ConfirmOrder
          cart={cart}
          onConfirm={handleConfirmOrder}
          onAllConfirmed={() => setStep("status")}
          onBack={() => setStep("preview")}
        />
      )}

      {step === "status" && sessionId && (
        <OrderStatus sessionId={sessionId} onNewOrder={handleReset} />
      )}
    </main>
  );
}

