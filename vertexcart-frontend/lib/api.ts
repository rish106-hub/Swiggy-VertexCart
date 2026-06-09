import { IntentResult, TurnResponse, CartState, OrderReference } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export class APIError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "APIError";
  }
}

async function fetchWithHandle(endpoint: string, options?: RequestInit) {
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });

    if (!response.ok) {
      let message = `API Error: ${response.statusText}`;
      try {
        const errorData = await response.json();
        message = errorData.detail || message;
      } catch {
        // Ignore json parse error if no body
      }
      throw new APIError(response.status, message);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }
    throw new APIError(500, error instanceof Error ? error.message : "Unknown Network Error");
  }
}

export const api = {
  createSession: async (userId: string): Promise<{ session_id: string }> => {
    return fetchWithHandle("/session", {
      method: "POST",
      body: JSON.stringify({ user_id: userId }),
    });
  },

  parseIntent: async (text: string, userId: string): Promise<IntentResult> => {
    return fetchWithHandle("/intent", {
      method: "POST",
      body: JSON.stringify({ text, user_id: userId }),
    });
  },

  sendTurn: async (sessionId: string, text: string): Promise<TurnResponse> => {
    return fetchWithHandle(`/session/${sessionId}/turn`, {
      method: "POST",
      body: JSON.stringify({ text }),
    });
  },

  getCart: async (sessionId: string): Promise<CartState> => {
    return fetchWithHandle(`/session/${sessionId}/cart`, {
      method: "GET",
    });
  },

  confirmOrder: async (sessionId: string, vertical: string): Promise<{ order_id: string; eta: string; status: string }> => {
    return fetchWithHandle(`/session/${sessionId}/confirm`, {
      method: "POST",
      body: JSON.stringify({ vertical }),
    });
  },

  getOrders: async (sessionId: string): Promise<OrderReference[]> => {
    return fetchWithHandle(`/session/${sessionId}/orders`, {
      method: "GET",
    });
  },
};
