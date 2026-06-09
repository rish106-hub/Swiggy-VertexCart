// Matches backend model: app/models/intent.py
export interface Entity {
  text: string;
  type: "ingredient" | "ready_to_eat" | "reservation";
  vertical: "instamart" | "food" | "dineout";
  confidence: number;
}

export interface IntentResult {
  entities: Entity[];
  occasion: string;
  urgency: string;
  dineout_signal: boolean;
  requires_clarification: boolean;
  raw_input: string;
}

// Matches backend model: app/models/session.py
export interface TurnResponse {
  agent_response: string;
  verticals_active: string[];
  cart_summary: Record<string, unknown>;
  requires_confirmation: boolean;
}

// Cart Item Models (Extrapolated from PRD and common MCP structures)
export interface CartItem {
  id?: string;
  itemId?: string;
  spinId?: string;
  name: string;
  price: number;
  quantity: number;
  image_url?: string;
}

export interface CartState {
  food: {
    items: CartItem[];
    total: number;
    restaurantId?: string;
    restaurantName?: string;
    eta?: string;
  };
  instamart: {
    items: CartItem[];
    total: number;
    eta?: string;
  };
  dineout: {
    slots?: Record<string, unknown>[];
    restaurantName?: string;
    reservationTime?: string;
  }
}

// Matches backend model: app/models/order.py
export interface OrderReference {
  id: string;
  vertical: "food" | "instamart" | "dineout";
  swiggy_order_id: string;
  status: string;
  eta?: string;
}
