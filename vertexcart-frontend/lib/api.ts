import { IntentResult, TurnResponse, CartState, OrderReference } from "./types";
import {
  parseIntentMock,
  buildMockCart,
  buildAgentResponse,
  generateMockOrders,
} from "./mock-engine";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

// Keyed by session ID — prevents stale state across React hot reloads
const _mockStore: Map<string, { cart: CartState; orders: OrderReference[] }> = new Map();
let _mockSessionId: string | null = null;

function getStore(sid: string) {
  if (!_mockStore.has(sid)) _mockStore.set(sid, { cart: {}, orders: [] });
  return _mockStore.get(sid)!;
}

export class APIError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "APIError";
  }
}

async function fetchWithHandle(endpoint: string, options?: RequestInit) {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      signal: controller.signal,
      headers: { "Content-Type": "application/json", ...options?.headers },
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      let message = `API Error: ${response.statusText}`;
      try {
        const errorData = await response.json();
        message = errorData.detail || message;
      } catch { /* ignore */ }
      throw new APIError(response.status, message);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof APIError) throw error;
    throw new APIError(503, "backend_unavailable");
  }
}

const mockDelay = (ms: number) => new Promise(r => setTimeout(r, ms));

export const api = {
  createSession: async (userId: string): Promise<{ session_id: string }> => {
    try {
      return await fetchWithHandle("/session", {
        method: "POST",
        body: JSON.stringify({ user_id: userId }),
      });
    } catch {
      // Fresh session ID → fresh store entry, no stale state
      _mockSessionId = `mock_${Math.random().toString(36).substr(2, 9)}`;
      _mockStore.delete(_mockSessionId); // ensure clean slate
      return { session_id: _mockSessionId };
    }
  },

  parseIntent: async (text: string, userId: string): Promise<IntentResult> => {
    try {
      return await fetchWithHandle("/intent", {
        method: "POST",
        body: JSON.stringify({ text, user_id: userId }),
      });
    } catch {
      await mockDelay(600);
      return parseIntentMock(text);
    }
  },

  sendTurn: async (sessionId: string, text: string): Promise<TurnResponse> => {
    try {
      return await fetchWithHandle(`/session/${sessionId}/turn`, {
        method: "POST",
        body: JSON.stringify({ text }),
      });
    } catch {
      await mockDelay(800);
      const intent = parseIntentMock(text);
      const cart = buildMockCart(text);
      // Always write to the session-specific store
      getStore(sessionId).cart = cart;
      const agentResp = buildAgentResponse(text, cart);
      return {
        agent_response: agentResp,
        verticals_active: intent.entities.map(e => e.vertical),
        cart_summary: {},
        requires_confirmation: true,
        requires_clarification: false,
      };
    }
  },

  getCart: async (sessionId: string): Promise<CartState> => {
    try {
      return await fetchWithHandle(`/session/${sessionId}/cart`);
    } catch {
      await mockDelay(200);
      return getStore(sessionId).cart;
    }
  },

  confirmOrder: async (
    sessionId: string,
    vertical: string
  ): Promise<{ order_id: string; eta: string; status: string }> => {
    try {
      return await fetchWithHandle(`/session/${sessionId}/confirm`, {
        method: "POST",
        body: JSON.stringify({ vertical }),
      });
    } catch {
      await mockDelay(1200);
      const store = getStore(sessionId);
      const cartSection =
        vertical === "food" ? store.cart.food
        : vertical === "instamart" ? store.cart.instamart
        : null;

      const orderId = `${vertical.toUpperCase().slice(0, 2)}-${Math.random()
        .toString(36).substr(2, 8).toUpperCase()}`;

      const eta =
        vertical === "dineout"
          ? (store.cart.dineout_slots?.[0] as { slot?: string; date?: string } | undefined)?.slot || "7:30 PM"
          : (cartSection as { status?: string } | undefined)?.status || "30 min";

      const order: OrderReference = {
        order_id: orderId,
        vertical: vertical as "food" | "instamart" | "dineout",
        placed_at: new Date().toISOString(),
        status: vertical === "dineout" ? "Confirmed" : "Accepted",
        eta,
      };

      store.orders.push(order);
      return { order_id: orderId, eta, status: order.status };
    }
  },

  getOrders: async (sessionId: string): Promise<OrderReference[]> => {
    try {
      return await fetchWithHandle(`/session/${sessionId}/orders`);
    } catch {
      await mockDelay(200);
      const store = getStore(sessionId);
      if (store.orders.length > 0) return store.orders;
      return generateMockOrders(store.cart);
    }
  },

  // Used by page.tsx for real-time correction sync
  updateMockCart: (sessionId: string, cart: CartState) => {
    getStore(sessionId).cart = cart;
  },
};
