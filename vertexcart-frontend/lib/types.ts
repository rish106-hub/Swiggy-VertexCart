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
  requires_clarification: boolean;
  clarification_prompt?: string;
}

// Cart Item Models (Extrapolated from Swiggy tool response structure)
export interface CartItem {
  itemId?: string;
  spinId?: string;
  name: string;
  price: number;
  quantity: number;
}

export interface FoodCart {
  items: CartItem[];
  subtotal: number;
  restaurantId?: string;
  restaurantName?: string;
  status?: string;
  error?: string;
}

export interface IMCart {
  items: CartItem[];
  subtotal: number;
  status?: string;
  error?: string;
}

export interface CartState {
  food?: FoodCart;
  instamart?: IMCart;
  dineout_restaurants?: unknown[];
  dineout_slots?: unknown[];
}

// Matches backend model: app/models/order.py
export interface OrderReference {
  order_id: string;
  vertical: "food" | "instamart" | "dineout";
  placed_at: string;
  status: string;
  eta?: string;
  tracking?: unknown;
}
