/**
 * Client-side mock intelligence engine.
 * Parses any free-text input → realistic intent + cart data.
 * Powers full demo flow without a running backend.
 */

import { Entity, IntentResult, CartState, CartItem, OrderReference } from "./types";

// ── Keyword banks ──────────────────────────────────────────────────────────────

const FOOD_KEYWORDS = [
  'pizza', 'burger', 'biryani', 'sushi', 'noodles', 'sandwich', 'wrap', 'roll',
  'cake', 'dessert', 'tiramisu', 'ice cream', 'gelato', 'brownie', 'pastry',
  'coffee', 'chai', 'tea', 'latte', 'cappuccino', 'cold brew',
  'breakfast', 'order', 'delivery', 'deliver', 'delivered', 'food', 'eat', 'hungry',
  'dal', 'roti', 'paneer', 'chicken', 'mutton', 'fish', 'kebab', 'paratha', 'dosa',
  'idli', 'momos', 'spring rolls', 'tacos', 'pasta', 'risotto', 'steak',
  'wings', 'nachos', 'fries', 'shawarma', 'pav bhaji', 'chole bhature',
  'rajma', 'khichdi', 'pulao', 'fried rice', 'hakka', 'manchurian',
];

const INSTAMART_KEYWORDS = [
  'groceries', 'grocery', 'ingredients', 'cook', 'cooking', 'make', 'prepare', 'bake',
  'vegetables', 'veggies', 'fruits', 'milk', 'bread', 'eggs', 'onion', 'tomato',
  'potato', 'garlic', 'ginger', 'cheese', 'butter', 'oil', 'sugar', 'flour', 'salt',
  'snacks', 'chips', 'biscuits', 'namkeen', 'crackers',
  'drinks', 'water', 'juice', 'soda', 'cola', 'coke', 'pepsi', 'sprite', 'diet coke',
  'cold drink', 'soft drink', 'energy drink', 'red bull',
  'usual', 'reorder', 'stock up', 'pantry', 'supplies', 'household',
  'detergent', 'soap', 'shampoo', 'toothpaste',
  'wine', 'beer', 'spirits', 'whiskey',
  'parmesan', 'mozzarella', 'ricotta', 'cream', 'yogurt', 'curd',
  'basil', 'oregano', 'thyme', 'spices', 'masala',
];

const DINEOUT_KEYWORDS = [
  'book', 'reserve', 'reservation', 'table', 'seat', 'dine', 'dining', 'dineout',
  'dinner out', 'lunch out', 'brunch out', 'go out', 'eat out',
  'friday', 'saturday', 'sunday', 'weekend', 'tonight', 'tomorrow',
  'date', 'anniversary', 'birthday', 'celebration', 'special occasion',
  'italian restaurant', 'sushi bar', 'steakhouse', 'rooftop', 'fine dining',
];

// ── Item catalogs ──────────────────────────────────────────────────────────────

const FOOD_ITEMS: Record<string, CartItem[]> = {
  pizza: [{ name: 'Margherita Pizza (Medium)', price: 299, quantity: 1 }],
  burger: [{ name: 'Classic Smash Burger', price: 229, quantity: 1 }],
  biryani: [{ name: 'Chicken Dum Biryani', price: 349, quantity: 1 }],
  sushi: [{ name: 'Sushi Platter (8 pcs)', price: 499, quantity: 1 }, { name: 'Miso Soup', price: 129, quantity: 1 }],
  tiramisu: [{ name: 'Tiramisu', price: 249, quantity: 1 }],
  dessert: [{ name: 'Dark Chocolate Lava Cake', price: 199, quantity: 1 }, { name: 'Vanilla Bean Gelato', price: 149, quantity: 1 }],
  cake: [{ name: 'Belgian Chocolate Cake Slice', price: 189, quantity: 1 }],
  pasta: [{ name: 'Penne Arrabbiata', price: 329, quantity: 1 }],
  coffee: [{ name: 'Cold Brew Coffee (16 oz)', price: 199, quantity: 1 }, { name: 'Hazelnut Croissant', price: 99, quantity: 1 }],
  chai: [{ name: 'Masala Chai (2 cups)', price: 79, quantity: 1 }, { name: 'Butter Toast', price: 59, quantity: 1 }],
  momos: [{ name: 'Steamed Chicken Momos (8 pcs)', price: 179, quantity: 1 }, { name: 'Schezwan Sauce', price: 29, quantity: 1 }],
  dosa: [{ name: 'Masala Dosa', price: 129, quantity: 1 }, { name: 'Filter Coffee', price: 69, quantity: 1 }],
  chicken: [{ name: 'Butter Chicken (Half)', price: 379, quantity: 1 }, { name: 'Garlic Naan (2 pcs)', price: 89, quantity: 1 }],
  paneer: [{ name: 'Paneer Tikka Masala', price: 319, quantity: 1 }, { name: 'Butter Naan (2 pcs)', price: 79, quantity: 1 }],
  default_food: [{ name: 'Chef\'s Special of the Day', price: 349, quantity: 1 }, { name: 'Garlic Bread', price: 99, quantity: 1 }],
};

const FOOD_RESTAURANTS: Record<string, string> = {
  pizza: 'La Pino\'z Pizza',
  burger: 'Burger Singh',
  biryani: 'Behrouz Biryani',
  sushi: 'Sushi Samba',
  tiramisu: 'The Dessert Factory',
  dessert: 'The Dessert Factory',
  cake: 'Theobroma',
  pasta: 'Smoky Joe\'s Diner',
  coffee: 'Blue Tokai Coffee',
  chai: 'Chaayos',
  momos: 'Momos Republic',
  dosa: 'Saravana Bhavan',
  chicken: 'Zaffran',
  paneer: 'Barbeque Nation',
  default_food: 'Swiggy Pop Kitchen',
};

const INSTAMART_ITEMS: Record<string, CartItem[]> = {
  pasta: [
    { name: 'Barilla Penne Rigate (500g)', price: 145, quantity: 1 },
    { name: 'Napoletana Tomato Sauce (400g)', price: 89, quantity: 1 },
    { name: 'Parmesan Cheese Block (100g)', price: 175, quantity: 1 },
    { name: 'Extra Virgin Olive Oil (250ml)', price: 220, quantity: 1 },
    { name: 'Fresh Garlic (200g)', price: 35, quantity: 1 },
  ],
  grocery: [
    { name: 'Full Cream Milk (1L)', price: 68, quantity: 2 },
    { name: 'Brown Bread Loaf', price: 55, quantity: 1 },
    { name: 'Farm Fresh Eggs (6 pcs)', price: 72, quantity: 1 },
    { name: 'Onions (1 kg)', price: 42, quantity: 1 },
    { name: 'Tomatoes (500g)', price: 35, quantity: 1 },
    { name: 'Fortune Refined Oil (1L)', price: 128, quantity: 1 },
  ],
  baking: [
    { name: 'All Purpose Flour (1 kg)', price: 58, quantity: 1 },
    { name: 'Castor Sugar (500g)', price: 48, quantity: 1 },
    { name: 'Amul Butter (100g)', price: 62, quantity: 2 },
    { name: 'Baking Powder (100g)', price: 45, quantity: 1 },
    { name: 'Vanilla Extract (30ml)', price: 95, quantity: 1 },
  ],
  snacks: [
    { name: 'Lay\'s Classic (60g)', price: 20, quantity: 2 },
    { name: 'Kurkure Masala (90g)', price: 20, quantity: 2 },
    { name: 'Parle-G Biscuits (250g)', price: 20, quantity: 1 },
    { name: 'Sprite (750ml)', price: 40, quantity: 2 },
  ],
  wine: [
    { name: 'Sula Sauvignon Blanc (750ml)', price: 850, quantity: 1 },
    { name: 'Fratelli Sangiovese (750ml)', price: 750, quantity: 1 },
    { name: 'Gourmet Cheese Board Kit', price: 350, quantity: 1 },
  ],
  cocktails: [
    { name: 'Bira 91 White (6-pack)', price: 680, quantity: 1 },
    { name: 'Bacardi Cocktail Mixers Pack', price: 320, quantity: 1 },
    { name: 'Sliced Lime & Mint Bundle', price: 45, quantity: 1 },
  ],
  beverages: [
    { name: 'Diet Coke (300ml)', price: 40, quantity: 2 },
    { name: 'Sprite (750ml)', price: 40, quantity: 1 },
    { name: 'Minute Maid Orange (250ml)', price: 30, quantity: 1 },
  ],
  coke: [
    { name: 'Diet Coke (300ml)', price: 40, quantity: 2 },
    { name: 'Coca-Cola Classic (750ml)', price: 45, quantity: 1 },
  ],
  default_im: [
    { name: 'Full Cream Milk (1L)', price: 68, quantity: 1 },
    { name: 'Brown Bread Loaf', price: 55, quantity: 1 },
    { name: 'Farm Fresh Eggs (6 pcs)', price: 72, quantity: 1 },
    { name: 'Mixed Vegetables Pack (500g)', price: 65, quantity: 1 },
  ],
};

const DINEOUT_SLOTS = [
  {
    restaurant: 'Fatty Bao – Asian Gastrobar',
    slot: '7:30 PM',
    date: 'Friday',
    cuisine: 'Pan-Asian',
    rating: '4.6',
  },
  {
    restaurant: 'Pebble Street Kitchen',
    slot: '8:00 PM',
    date: 'Friday',
    cuisine: 'Continental',
    rating: '4.4',
  },
  {
    restaurant: 'SodaBottleOpenerWala',
    slot: '7:00 PM',
    date: 'Saturday',
    cuisine: 'Parsi Café',
    rating: '4.5',
  },
];

// ── NLP-lite parser ────────────────────────────────────────────────────────────

function tokenize(text: string): string[] {
  return text.toLowerCase().split(/[\s,+&]+/).filter(Boolean);
}

function contains(text: string, keywords: string[]): boolean {
  const lower = text.toLowerCase();
  return keywords.some(k => lower.includes(k));
}

function detectIntentType(text: string): {
  hasFood: boolean;
  hasInstamart: boolean;
  hasDineout: boolean;
} {
  return {
    hasFood: contains(text, FOOD_KEYWORDS),
    hasInstamart: contains(text, INSTAMART_KEYWORDS),
    hasDineout: contains(text, DINEOUT_KEYWORDS),
  };
}

function pickFoodItems(text: string): { items: CartItem[]; restaurant: string; key: string } {
  const lower = text.toLowerCase();
  for (const [key, items] of Object.entries(FOOD_ITEMS)) {
    if (key !== 'default_food' && lower.includes(key)) {
      return { items: JSON.parse(JSON.stringify(items)), restaurant: FOOD_RESTAURANTS[key] || FOOD_RESTAURANTS.default_food, key };
    }
  }
  // Try partial matches
  const tokens = tokenize(text);
  for (const token of tokens) {
    for (const [key, items] of Object.entries(FOOD_ITEMS)) {
      if (key !== 'default_food' && key.includes(token) && token.length > 3) {
        return { items: JSON.parse(JSON.stringify(items)), restaurant: FOOD_RESTAURANTS[key] || FOOD_RESTAURANTS.default_food, key };
      }
    }
  }
  return {
    items: JSON.parse(JSON.stringify(FOOD_ITEMS.default_food)),
    restaurant: FOOD_RESTAURANTS.default_food,
    key: 'default_food',
  };
}

function pickInstamartItems(text: string): CartItem[] {
  const lower = text.toLowerCase();
  if (lower.includes('coke') || lower.includes('diet coke') || lower.includes('pepsi') || lower.includes('sprite') || lower.includes('cola')) {
    return JSON.parse(JSON.stringify(INSTAMART_ITEMS.coke));
  }
  if (lower.includes('soda') || lower.includes('cold drink') || lower.includes('soft drink') || lower.includes('beverage')) {
    return JSON.parse(JSON.stringify(INSTAMART_ITEMS.beverages));
  }
  if (lower.includes('pasta') || lower.includes('spaghetti') || lower.includes('penne')) {
    return JSON.parse(JSON.stringify(INSTAMART_ITEMS.pasta));
  }
  if (lower.includes('bak') || lower.includes('cookie') || lower.includes('muffin')) {
    return JSON.parse(JSON.stringify(INSTAMART_ITEMS.baking));
  }
  if (lower.includes('snack') || lower.includes('chips') || lower.includes('namkeen')) {
    return JSON.parse(JSON.stringify(INSTAMART_ITEMS.snacks));
  }
  if (lower.includes('wine') || lower.includes('prosecco') || lower.includes('champagne')) {
    return JSON.parse(JSON.stringify(INSTAMART_ITEMS.wine));
  }
  if (lower.includes('beer') || lower.includes('cocktail') || lower.includes('mixer')) {
    return JSON.parse(JSON.stringify(INSTAMART_ITEMS.cocktails));
  }
  if (lower.includes('usual') || lower.includes('reorder') || lower.includes('groceries') || lower.includes('grocery')) {
    return JSON.parse(JSON.stringify(INSTAMART_ITEMS.grocery));
  }
  return JSON.parse(JSON.stringify(INSTAMART_ITEMS.default_im));
}

function pickDineoutSlot(text: string) {
  const lower = text.toLowerCase();
  if (lower.includes('saturday') || lower.includes('sunday') || lower.includes('weekend')) {
    return DINEOUT_SLOTS[2];
  }
  if (lower.includes('italian')) {
    return { ...DINEOUT_SLOTS[1], cuisine: 'Italian', restaurant: 'Trattoria' };
  }
  if (lower.includes('asian') || lower.includes('sushi') || lower.includes('thai')) {
    return DINEOUT_SLOTS[0];
  }
  return DINEOUT_SLOTS[Math.floor(Math.random() * DINEOUT_SLOTS.length)];
}

function sum(items: CartItem[]): number {
  return items.reduce((acc, i) => acc + i.price * i.quantity, 0);
}

// ── Public API ─────────────────────────────────────────────────────────────────

export function parseIntentMock(text: string): IntentResult {
  const { hasFood, hasInstamart, hasDineout } = detectIntentType(text);
  const entities: Entity[] = [];

  if (hasInstamart) {
    // Extract the ingredient/grocery-related phrase
    const phrases = text.match(/cook\s+\w+|\w+\s+ingredients?|usual\s+groceries?|\w+\s+supplies?/i);
    entities.push({
      text: phrases?.[0] || 'groceries',
      type: 'ingredient',
      vertical: 'instamart',
      confidence: 0.91,
    });
  }

  if (hasFood) {
    // Find the most specific food noun
    const lower = text.toLowerCase();
    let foodPhrase = 'food delivery';
    for (const key of Object.keys(FOOD_ITEMS)) {
      if (key !== 'default_food' && lower.includes(key)) {
        foodPhrase = key;
        break;
      }
    }
    entities.push({
      text: foodPhrase,
      type: 'ready_to_eat',
      vertical: 'food',
      confidence: 0.87,
    });
  }

  if (hasDineout) {
    const phrases = text.match(/book\s+a?\s*table|reserve\s+a?\s*table|dinner\s+out|lunch\s+out|dine\s+out/i);
    entities.push({
      text: phrases?.[0] || 'table reservation',
      type: 'reservation',
      vertical: 'dineout',
      confidence: 0.93,
    });
  }

  // Fallback: if nothing detected, treat as food order
  if (entities.length === 0) {
    entities.push({
      text: text.trim().slice(0, 30),
      type: 'ready_to_eat',
      vertical: 'food',
      confidence: 0.72,
    });
  }

  return {
    entities,
    occasion: hasDineout ? 'evening_out' : hasInstamart && hasFood ? 'cook_and_order' : hasFood ? 'food_delivery' : 'grocery_run',
    urgency: 'immediate',
    dineout_signal: hasDineout,
    requires_clarification: false,
    raw_input: text,
  };
}

export function buildMockCart(text: string): CartState {
  const { hasFood, hasInstamart, hasDineout } = detectIntentType(text);
  const state: CartState = {};

  if (hasInstamart) {
    const items = pickInstamartItems(text);
    state.instamart = {
      items,
      subtotal: sum(items),
      status: `${10 + Math.floor(Math.random() * 10)} min`,
    };
  }

  if (hasFood && !hasDineout) {
    const { items, restaurant } = pickFoodItems(text);
    state.food = {
      items,
      subtotal: sum(items),
      restaurantName: restaurant,
      status: `${25 + Math.floor(Math.random() * 20)} min`,
    };
  }

  if (hasDineout) {
    const slot = pickDineoutSlot(text);
    state.dineout_slots = [slot];
  }

  // Fallback if nothing matched
  if (!state.instamart && !state.food && !state.dineout_slots) {
    const { items, restaurant } = pickFoodItems(text);
    state.food = {
      items,
      subtotal: sum(items),
      restaurantName: restaurant,
      status: `${25 + Math.floor(Math.random() * 20)} min`,
    };
  }

  return state;
}

export function buildAgentResponse(text: string, cart: CartState): string {
  const parts: string[] = [];

  if (cart.instamart && (cart.instamart.items?.length || 0) > 0) {
    const count = cart.instamart.items.length;
    const total = cart.instamart.subtotal;
    parts.push(`Found ${count} items on Instamart (₹${total}, ~${cart.instamart.status})`);
  }

  if (cart.food && (cart.food.items?.length || 0) > 0) {
    const total = cart.food.subtotal;
    const restaurant = cart.food.restaurantName;
    parts.push(`${cart.food.items[0]?.name} from ${restaurant} on Swiggy Food (₹${total}, ~${cart.food.status})`);
  }

  if (cart.dineout_slots && cart.dineout_slots.length > 0) {
    const slot = cart.dineout_slots[0] as { restaurant: string; slot: string; date: string };
    parts.push(`Free table at ${slot.restaurant} for ${slot.date} at ${slot.slot}`);
  }

  if (parts.length === 0) {
    return `Got it — let me put that together for you.`;
  }

  if (parts.length === 1) {
    return `Got it! ${parts[0]}. Want me to go ahead?`;
  }

  const last = parts.pop()!;
  return `Here's your plan: ${parts.join(', ')}, and ${last}. Ready to confirm?`;
}

const REMOVAL_WORDS = ['remove', 'drop', 'skip', "don't", 'no ', 'without', 'cancel', 'delete'];
const FRESH_ORDER_SIGNALS = ['i want', 'i need', 'order me', 'get me', 'give me', 'just ', 'only ', 'instead'];

export function applyCorrection(originalText: string, correction: string, currentCart: CartState): CartState {
  const lower = correction.toLowerCase();

  // Removal commands — patch the existing cart
  if (REMOVAL_WORDS.some(w => lower.includes(w))) {
    const updated = JSON.parse(JSON.stringify(currentCart)) as CartState;

    if (lower.includes('instamart') || lower.includes('groceries') || lower.includes('ingredient') || lower.includes('coke') || lower.includes('drink')) {
      delete updated.instamart;
    }
    if (lower.includes('food') || lower.includes('delivery')) {
      delete updated.food;
    }
    if (lower.includes('dineout') || lower.includes('table') || lower.includes('reservation')) {
      delete updated.dineout_slots;
    }

    // Remove specific items by name tokens
    const tokens = tokenize(correction).filter(t => t.length > 3 && !REMOVAL_WORDS.includes(t));
    if (tokens.length > 0) {
      if (updated.food?.items) {
        updated.food.items = updated.food.items.filter(item =>
          !tokens.some(t => item.name.toLowerCase().includes(t))
        );
        updated.food.subtotal = sum(updated.food.items);
        if (updated.food.items.length === 0) delete updated.food;
      }
      if (updated.instamart?.items) {
        updated.instamart.items = updated.instamart.items.filter(item =>
          !tokens.some(t => item.name.toLowerCase().includes(t))
        );
        updated.instamart.subtotal = sum(updated.instamart.items);
        if (updated.instamart.items.length === 0) delete updated.instamart;
      }
    }

    return updated;
  }

  // Correction looks like a fresh order intent — replace, don't append
  if (FRESH_ORDER_SIGNALS.some(s => lower.includes(s))) {
    return buildMockCart(correction);
  }

  // Contains food/item keywords that differ from original → fresh parse of correction alone
  const { hasFood, hasInstamart, hasDineout } = detectIntentType(correction);
  if (hasFood || hasInstamart || hasDineout) {
    // Build cart for correction text independently, then merge with original cart
    const correctionCart = buildMockCart(correction);
    const merged: CartState = { ...currentCart };
    if (correctionCart.food) merged.food = correctionCart.food;
    if (correctionCart.instamart) merged.instamart = correctionCart.instamart;
    if (correctionCart.dineout_slots) merged.dineout_slots = correctionCart.dineout_slots;
    return merged;
  }

  return currentCart;
}

export function generateMockOrders(cart: CartState): OrderReference[] {
  const orders: OrderReference[] = [];
  const now = new Date().toISOString();

  if (cart.instamart && (cart.instamart.items?.length || 0) > 0) {
    orders.push({
      order_id: `IM-${Math.random().toString(36).substr(2, 8).toUpperCase()}`,
      vertical: 'instamart',
      placed_at: now,
      status: 'Packing',
      eta: cart.instamart.status || '15 min',
    });
  }

  if (cart.food && (cart.food.items?.length || 0) > 0) {
    orders.push({
      order_id: `FD-${Math.random().toString(36).substr(2, 8).toUpperCase()}`,
      vertical: 'food',
      placed_at: now,
      status: 'Accepted',
      eta: cart.food.status || '35 min',
    });
  }

  if (cart.dineout_slots && cart.dineout_slots.length > 0) {
    const slot = cart.dineout_slots[0] as { restaurant: string; slot: string; date: string };
    orders.push({
      order_id: `DO-${Math.random().toString(36).substr(2, 8).toUpperCase()}`,
      vertical: 'dineout',
      placed_at: now,
      status: 'Confirmed',
      eta: `${slot.date}, ${slot.slot}`,
    });
  }

  return orders;
}
