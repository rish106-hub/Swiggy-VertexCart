/**
 * Mock engine — word-level matching, no substring false-positives.
 * Each word in the user's input is looked up in explicit maps.
 * "coke" only matches "coke", never "cookie" or "cook".
 */

import { Entity, IntentResult, CartState, CartItem, OrderReference } from "./types";

// ── Item lookup maps ───────────────────────────────────────────────────────────
// Keys are lowercase single words or short phrases.
// A word in the user's input matches a key if the word equals the key exactly
// OR the user input contains the full key phrase.

interface FoodEntry { items: CartItem[]; restaurant: string }
interface IMEntry   { items: CartItem[] }

const FOOD_MAP: Record<string, FoodEntry> = {
  biryani:      { restaurant: "Behrouz Biryani",       items: [{ name: "Chicken Dum Biryani", price: 349, quantity: 1 }, { name: "Raita", price: 49, quantity: 1 }] },
  pizza:        { restaurant: "La Pino'z Pizza",       items: [{ name: "Margherita Pizza (Medium)", price: 299, quantity: 1 }, { name: "Garlic Bread", price: 99, quantity: 1 }] },
  burger:       { restaurant: "Burger Singh",          items: [{ name: "Classic Smash Burger", price: 229, quantity: 1 }, { name: "Loaded Fries", price: 149, quantity: 1 }] },
  sushi:        { restaurant: "Sushi Samba",           items: [{ name: "Sushi Platter (8 pcs)", price: 499, quantity: 1 }, { name: "Miso Soup", price: 129, quantity: 1 }] },
  tiramisu:     { restaurant: "The Dessert Factory",   items: [{ name: "Classic Tiramisu", price: 249, quantity: 1 }] },
  momos:        { restaurant: "Momos Republic",        items: [{ name: "Steamed Chicken Momos (8 pcs)", price: 179, quantity: 1 }, { name: "Schezwan Dip", price: 29, quantity: 1 }] },
  dosa:         { restaurant: "Saravana Bhavan",       items: [{ name: "Masala Dosa", price: 129, quantity: 1 }, { name: "Filter Coffee", price: 69, quantity: 1 }] },
  idli:         { restaurant: "Saravana Bhavan",       items: [{ name: "Idli Sambar (4 pcs)", price: 99, quantity: 1 }, { name: "Coconut Chutney", price: 29, quantity: 1 }] },
  chicken:      { restaurant: "Zaffran",               items: [{ name: "Butter Chicken (Half)", price: 379, quantity: 1 }, { name: "Garlic Naan (2 pcs)", price: 89, quantity: 1 }] },
  paneer:       { restaurant: "Barbeque Nation",       items: [{ name: "Paneer Tikka Masala", price: 319, quantity: 1 }, { name: "Butter Naan (2 pcs)", price: 79, quantity: 1 }] },
  kebab:        { restaurant: "Barbeque Nation",       items: [{ name: "Seekh Kebab (6 pcs)", price: 299, quantity: 1 }, { name: "Mint Chutney", price: 25, quantity: 1 }] },
  shawarma:     { restaurant: "Shawarma Station",      items: [{ name: "Chicken Shawarma Roll", price: 179, quantity: 1 }] },
  noodles:      { restaurant: "Wok to Walk",           items: [{ name: "Hakka Noodles (Chicken)", price: 249, quantity: 1 }] },
  pasta:        { restaurant: "Smoky Joe's Diner",     items: [{ name: "Penne Arrabbiata", price: 329, quantity: 1 }, { name: "Garlic Bread", price: 89, quantity: 1 }] },
  sandwich:     { restaurant: "Subway",                items: [{ name: "Chicken Teriyaki Sub (6\")", price: 199, quantity: 1 }] },
  coffee:       { restaurant: "Blue Tokai Coffee",     items: [{ name: "Cold Brew Coffee (16 oz)", price: 199, quantity: 1 }, { name: "Hazelnut Croissant", price: 99, quantity: 1 }] },
  chai:         { restaurant: "Chaayos",               items: [{ name: "Masala Chai (2 cups)", price: 79, quantity: 1 }, { name: "Butter Toast", price: 59, quantity: 1 }] },
  tea:          { restaurant: "Chaayos",               items: [{ name: "Masala Chai (2 cups)", price: 79, quantity: 1 }] },
  cake:         { restaurant: "Theobroma",             items: [{ name: "Belgian Chocolate Cake Slice", price: 189, quantity: 1 }] },
  dessert:      { restaurant: "The Dessert Factory",   items: [{ name: "Dark Chocolate Lava Cake", price: 199, quantity: 1 }, { name: "Vanilla Gelato", price: 149, quantity: 1 }] },
  icecream:     { restaurant: "Baskin Robbins",        items: [{ name: "Brownie Sundae (2 scoops)", price: 229, quantity: 1 }] },
  "ice cream":  { restaurant: "Baskin Robbins",        items: [{ name: "Brownie Sundae (2 scoops)", price: 229, quantity: 1 }] },
  pav:          { restaurant: "Jumbo King",            items: [{ name: "Vada Pav (2 pcs)", price: 60, quantity: 1 }] },
  "pav bhaji":  { restaurant: "Sardar Pav Bhaji",      items: [{ name: "Pav Bhaji (2 pieces pav)", price: 149, quantity: 1 }] },
  chole:        { restaurant: "Roshan di Kulfi",       items: [{ name: "Chole Bhature (2 pieces)", price: 169, quantity: 1 }] },
  dal:          { restaurant: "Haldiram's",            items: [{ name: "Dal Makhani (300g)", price: 199, quantity: 1 }, { name: "Butter Roti (4 pcs)", price: 79, quantity: 1 }] },
  rice:         { restaurant: "Haldiram's",            items: [{ name: "Steamed Rice (300g)", price: 79, quantity: 1 }, { name: "Dal Tadka (250g)", price: 149, quantity: 1 }] },
  steak:        { restaurant: "Hard Rock Cafe",        items: [{ name: "BBQ Beef Steak (200g)", price: 699, quantity: 1 }, { name: "Mashed Potato", price: 149, quantity: 1 }] },
  nachos:       { restaurant: "Chili's",               items: [{ name: "Classic Nachos with Cheese", price: 299, quantity: 1 }] },
  wings:        { restaurant: "WingsNMore",            items: [{ name: "Buffalo Wings (8 pcs)", price: 349, quantity: 1 }, { name: "BBQ Dip", price: 39, quantity: 1 }] },
  wrap:         { restaurant: "Subway",                items: [{ name: "Chicken & Avocado Wrap", price: 219, quantity: 1 }] },
  tacos:        { restaurant: "Taco Bell",             items: [{ name: "Crunchy Chicken Tacos (3 pcs)", price: 249, quantity: 1 }] },
  lunch:        { restaurant: "Behrouz Biryani",       items: [{ name: "Chicken Dum Biryani", price: 349, quantity: 1 }] },
  dinner:       { restaurant: "Zaffran",               items: [{ name: "Butter Chicken (Half)", price: 379, quantity: 1 }, { name: "Garlic Naan (2 pcs)", price: 89, quantity: 1 }] },
  breakfast:    { restaurant: "Chaayos",               items: [{ name: "Masala Chai (2 cups)", price: 79, quantity: 1 }, { name: "Aloo Paratha (2 pcs)", price: 119, quantity: 1 }] },
};

const INSTAMART_MAP: Record<string, IMEntry> = {
  milk:         { items: [{ name: "Amul Full Cream Milk (1L)", price: 68, quantity: 2 }] },
  bread:        { items: [{ name: "Britannia Brown Bread", price: 55, quantity: 1 }] },
  eggs:         { items: [{ name: "Farm Fresh Eggs (6 pcs)", price: 72, quantity: 1 }] },
  egg:          { items: [{ name: "Farm Fresh Eggs (6 pcs)", price: 72, quantity: 1 }] },
  butter:       { items: [{ name: "Amul Butter (100g)", price: 62, quantity: 1 }] },
  cheese:       { items: [{ name: "Amul Processed Cheese (200g)", price: 120, quantity: 1 }] },
  tomato:       { items: [{ name: "Fresh Tomatoes (500g)", price: 35, quantity: 1 }] },
  tomatoes:     { items: [{ name: "Fresh Tomatoes (500g)", price: 35, quantity: 1 }] },
  onion:        { items: [{ name: "Onions (1 kg)", price: 42, quantity: 1 }] },
  onions:       { items: [{ name: "Onions (1 kg)", price: 42, quantity: 1 }] },
  potato:       { items: [{ name: "Potatoes (1 kg)", price: 38, quantity: 1 }] },
  potatoes:     { items: [{ name: "Potatoes (1 kg)", price: 38, quantity: 1 }] },
  garlic:       { items: [{ name: "Fresh Garlic (200g)", price: 35, quantity: 1 }] },
  ginger:       { items: [{ name: "Fresh Ginger (100g)", price: 25, quantity: 1 }] },
  flour:        { items: [{ name: "Aashirvaad Atta (1 kg)", price: 58, quantity: 1 }] },
  sugar:        { items: [{ name: "Tata Sugar (1 kg)", price: 52, quantity: 1 }] },
  salt:         { items: [{ name: "Tata Salt (1 kg)", price: 28, quantity: 1 }] },
  oil:          { items: [{ name: "Fortune Refined Oil (1L)", price: 128, quantity: 1 }] },
  rice:         { items: [{ name: "India Gate Basmati Rice (1 kg)", price: 145, quantity: 1 }] },
  dal:          { items: [{ name: "Toor Dal (500g)", price: 72, quantity: 1 }] },
  pasta:        { items: [{ name: "Barilla Penne (500g)", price: 145, quantity: 1 }, { name: "Napoletana Sauce (400g)", price: 89, quantity: 1 }, { name: "Parmesan (100g)", price: 175, quantity: 1 }] },
  parmesan:     { items: [{ name: "Grana Padano Parmesan (100g)", price: 175, quantity: 1 }] },
  "olive oil":  { items: [{ name: "Extra Virgin Olive Oil (250ml)", price: 220, quantity: 1 }] },
  wine:         { items: [{ name: "Sula Sauvignon Blanc (750ml)", price: 850, quantity: 1 }, { name: "Gourmet Cheese Board Kit", price: 350, quantity: 1 }] },
  beer:         { items: [{ name: "Bira 91 White (6-pack)", price: 680, quantity: 1 }] },
  whiskey:      { items: [{ name: "Royal Stag Deluxe (375ml)", price: 550, quantity: 1 }] },
  coke:         { items: [{ name: "Coca-Cola (300ml)", price: 40, quantity: 2 }, { name: "Diet Coke (300ml)", price: 40, quantity: 1 }] },
  "diet coke":  { items: [{ name: "Diet Coke (300ml)", price: 40, quantity: 2 }] },
  cola:         { items: [{ name: "Coca-Cola (300ml)", price: 40, quantity: 2 }] },
  pepsi:        { items: [{ name: "Pepsi (300ml)", price: 40, quantity: 2 }] },
  sprite:       { items: [{ name: "Sprite (750ml)", price: 40, quantity: 1 }] },
  soda:         { items: [{ name: "Evervess Soda (500ml)", price: 30, quantity: 2 }] },
  juice:        { items: [{ name: "Tropicana Orange (1L)", price: 120, quantity: 1 }] },
  water:        { items: [{ name: "Bisleri Water (1L)", price: 20, quantity: 4 }] },
  chips:        { items: [{ name: "Lay's Classic (60g)", price: 20, quantity: 2 }, { name: "Kurkure Masala (90g)", price: 20, quantity: 1 }] },
  snacks:       { items: [{ name: "Lay's Classic (60g)", price: 20, quantity: 2 }, { name: "Bingo Mad Angles (90g)", price: 20, quantity: 1 }, { name: "Parle-G (250g)", price: 20, quantity: 1 }] },
  chocolate:    { items: [{ name: "Cadbury Dairy Milk (160g)", price: 90, quantity: 1 }, { name: "KitKat (41.5g)", price: 30, quantity: 2 }] },
  biscuits:     { items: [{ name: "Parle-G Biscuits (250g)", price: 20, quantity: 2 }, { name: "Oreo Original (150g)", price: 40, quantity: 1 }] },
  groceries:    { items: [{ name: "Full Cream Milk (1L)", price: 68, quantity: 2 }, { name: "Brown Bread", price: 55, quantity: 1 }, { name: "Farm Fresh Eggs (6 pcs)", price: 72, quantity: 1 }, { name: "Onions (1 kg)", price: 42, quantity: 1 }, { name: "Tomatoes (500g)", price: 35, quantity: 1 }] },
  grocery:      { items: [{ name: "Full Cream Milk (1L)", price: 68, quantity: 2 }, { name: "Brown Bread", price: 55, quantity: 1 }, { name: "Farm Fresh Eggs (6 pcs)", price: 72, quantity: 1 }, { name: "Onions (1 kg)", price: 42, quantity: 1 }, { name: "Tomatoes (500g)", price: 35, quantity: 1 }] },
  vegetables:   { items: [{ name: "Mixed Vegetables Pack (500g)", price: 65, quantity: 1 }, { name: "Tomatoes (500g)", price: 35, quantity: 1 }, { name: "Onions (1 kg)", price: 42, quantity: 1 }] },
  veggies:      { items: [{ name: "Mixed Vegetables Pack (500g)", price: 65, quantity: 1 }] },
  fruits:       { items: [{ name: "Apple (1 kg)", price: 150, quantity: 1 }, { name: "Banana (dozen)", price: 60, quantity: 1 }] },
  cream:        { items: [{ name: "Amul Fresh Cream (200ml)", price: 65, quantity: 1 }] },
  yogurt:       { items: [{ name: "Epigamia Greek Yogurt (400g)", price: 130, quantity: 1 }] },
  curd:         { items: [{ name: "Mother Dairy Curd (400g)", price: 52, quantity: 1 }] },
  masala:       { items: [{ name: "MDH Garam Masala (100g)", price: 72, quantity: 1 }, { name: "Everest Chicken Masala (50g)", price: 48, quantity: 1 }] },
  spices:       { items: [{ name: "MDH Garam Masala (100g)", price: 72, quantity: 1 }, { name: "Everest Coriander Powder (50g)", price: 38, quantity: 1 }] },
  ingredients:  { items: [{ name: "Mixed Vegetables Pack (500g)", price: 65, quantity: 1 }, { name: "Onions (1 kg)", price: 42, quantity: 1 }, { name: "Tomatoes (500g)", price: 35, quantity: 1 }, { name: "Garlic (200g)", price: 35, quantity: 1 }] },
};

// Words that signal "buy/cook at home" → Instamart even for food words
const COOK_SIGNALS = new Set(["cook", "cooking", "make", "bake", "baking", "prepare", "preparing", "making", "ingredients", "recipe"]);

// Words that signal a restaurant reservation
const DINEOUT_SIGNALS = new Set(["book", "reserve", "reservation", "table", "dine", "dining"]);
const DINEOUT_PHRASES = ["book a table", "reserve a table", "dinner out", "lunch out", "dine out", "eat out", "going out"];

const DINEOUT_RESTAURANTS = [
  { restaurant: "Fatty Bao – Asian Gastrobar",    slot: "7:30 PM", date: "Friday",   cuisine: "Pan-Asian",    rating: "4.6" },
  { restaurant: "Pebble Street Kitchen",           slot: "8:00 PM", date: "Friday",   cuisine: "Continental",  rating: "4.4" },
  { restaurant: "SodaBottleOpenerWala",            slot: "7:00 PM", date: "Saturday", cuisine: "Parsi Café",   rating: "4.5" },
  { restaurant: "The Bombay Canteen",              slot: "8:30 PM", date: "Saturday", cuisine: "Modern Indian", rating: "4.7" },
];

// ── Tokenizer ──────────────────────────────────────────────────────────────────

function tokenize(text: string): string[] {
  return text.toLowerCase()
    .replace(/[^a-z0-9\s]/g, " ")
    .split(/\s+/)
    .filter(t => t.length > 0);
}

// Match multi-word phrases first, then single words
function extractMatches(text: string): {
  foodKeys: string[];
  imKeys: string[];
  hasDineout: boolean;
  hasCookSignal: boolean;
} {
  const lower = text.toLowerCase();
  const tokens = tokenize(text);

  const foodKeys: string[] = [];
  const imKeys: string[] = [];

  // Check multi-word phrases first (longest match wins)
  const allMapKeys = [
    ...Object.keys(FOOD_MAP).filter(k => k.includes(" ")),
    ...Object.keys(INSTAMART_MAP).filter(k => k.includes(" ")),
  ];
  const matchedPhrases = new Set<string>();

  for (const phrase of allMapKeys) {
    if (lower.includes(phrase)) {
      if (FOOD_MAP[phrase])      { foodKeys.push(phrase); matchedPhrases.add(phrase); }
      if (INSTAMART_MAP[phrase]) { imKeys.push(phrase);   matchedPhrases.add(phrase); }
    }
  }

  // Single-word matches — skip tokens already covered by a matched phrase
  for (const token of tokens) {
    // Skip if this token is part of a matched phrase
    const inPhrase = Array.from(matchedPhrases).some(p => p.includes(token));
    if (inPhrase) continue;

    if (FOOD_MAP[token] && !foodKeys.includes(token))           foodKeys.push(token);
    if (INSTAMART_MAP[token] && !imKeys.includes(token))        imKeys.push(token);
  }

  const hasCookSignal = tokens.some(t => COOK_SIGNALS.has(t));
  const hasDineout =
    tokens.some(t => DINEOUT_SIGNALS.has(t)) ||
    DINEOUT_PHRASES.some(p => lower.includes(p));

  return { foodKeys, imKeys, hasDineout, hasCookSignal };
}

// ── Cart builder ───────────────────────────────────────────────────────────────

function sum(items: CartItem[]): number {
  return items.reduce((a, i) => a + i.price * i.quantity, 0);
}

function pickDineoutSlot(text: string) {
  const lower = text.toLowerCase();
  if (lower.includes("saturday") || lower.includes("sunday") || lower.includes("weekend")) return DINEOUT_RESTAURANTS[2];
  if (lower.includes("italian"))   return { ...DINEOUT_RESTAURANTS[1], cuisine: "Italian" };
  if (lower.includes("asian") || lower.includes("thai"))  return DINEOUT_RESTAURANTS[0];
  return DINEOUT_RESTAURANTS[Math.floor(Math.random() * DINEOUT_RESTAURANTS.length)];
}

export function buildMockCart(text: string): CartState {
  const { foodKeys, imKeys, hasDineout, hasCookSignal } = extractMatches(text);
  const state: CartState = {};

  // If cook signal present, food words → Instamart ingredients instead of delivery
  const effectiveFoodKeys = hasCookSignal ? [] : foodKeys;
  const effectiveIMKeys   = hasCookSignal
    ? [...imKeys, ...foodKeys.filter(k => INSTAMART_MAP[k])]
    : imKeys;

  // Build Instamart cart — deduplicate items
  if (effectiveIMKeys.length > 0) {
    const seen = new Set<string>();
    const allItems: CartItem[] = [];
    for (const key of effectiveIMKeys) {
      const entry = INSTAMART_MAP[key];
      if (!entry) continue;
      for (const item of entry.items) {
        if (!seen.has(item.name)) {
          seen.add(item.name);
          allItems.push({ ...item });
        }
      }
    }
    if (allItems.length > 0) {
      state.instamart = { items: allItems, subtotal: sum(allItems), status: `${10 + Math.floor(Math.random() * 8)} min` };
    }
  }

  // Build Food cart — use first matched food item (one restaurant per cart)
  if (effectiveFoodKeys.length > 0) {
    const key = effectiveFoodKeys[0];
    const entry = FOOD_MAP[key];
    if (entry) {
      const items = JSON.parse(JSON.stringify(entry.items)) as CartItem[];
      state.food = {
        items,
        subtotal: sum(items),
        restaurantName: entry.restaurant,
        status: `${25 + Math.floor(Math.random() * 18)} min`,
      };
    }
  }

  // Dineout
  if (hasDineout) {
    state.dineout_slots = [pickDineoutSlot(text)];
  }

  // Absolute fallback — if nothing matched, try to infer from raw nouns
  if (!state.food && !state.instamart && !state.dineout_slots) {
    const tokens = tokenize(text);
    // Find the first token that could be a food item (length > 3, no stopwords)
    const stopwords = new Set(["want", "need", "like", "have", "some", "with", "from", "order", "please", "just", "also", "and", "the", "for", "can", "get", "give"]);
    const noun = tokens.find(t => t.length > 3 && !stopwords.has(t));
    state.food = {
      items: [{ name: noun ? `${noun.charAt(0).toUpperCase()}${noun.slice(1)} Special` : "Chef's Daily Special", price: 299, quantity: 1 }],
      subtotal: 299,
      restaurantName: "Swiggy Pop Kitchen",
      status: "30 min",
    };
  }

  return state;
}

// ── Intent parser ──────────────────────────────────────────────────────────────

export function parseIntentMock(text: string): IntentResult {
  const { foodKeys, imKeys, hasDineout, hasCookSignal } = extractMatches(text);
  const entities: Entity[] = [];

  const effectiveFoodKeys = hasCookSignal ? [] : foodKeys;
  const effectiveIMKeys   = hasCookSignal ? [...imKeys, ...foodKeys] : imKeys;

  if (effectiveIMKeys.length > 0) {
    entities.push({
      text: effectiveIMKeys[0],
      type: "ingredient",
      vertical: "instamart",
      confidence: 0.93,
    });
  }

  if (effectiveFoodKeys.length > 0) {
    entities.push({
      text: effectiveFoodKeys[0],
      type: "ready_to_eat",
      vertical: "food",
      confidence: 0.91,
    });
  }

  if (hasDineout) {
    entities.push({
      text: "table reservation",
      type: "reservation",
      vertical: "dineout",
      confidence: 0.95,
    });
  }

  if (entities.length === 0) {
    const tokens = tokenize(text).filter(t => t.length > 3);
    entities.push({
      text: tokens[0] || text.slice(0, 20),
      type: "ready_to_eat",
      vertical: "food",
      confidence: 0.65,
    });
  }

  const verticals = entities.map(e => e.vertical);
  return {
    entities,
    occasion: hasDineout ? "evening_out" : verticals.includes("instamart") && verticals.includes("food") ? "cook_and_order" : verticals.includes("instamart") ? "grocery_run" : "food_delivery",
    urgency: "immediate",
    dineout_signal: hasDineout,
    requires_clarification: false,
    raw_input: text,
  };
}

// ── Agent response ─────────────────────────────────────────────────────────────

export function buildAgentResponse(text: string, cart: CartState): string {
  const parts: string[] = [];

  if (cart.instamart?.items?.length) {
    parts.push(`${cart.instamart.items.length} items from Instamart (₹${cart.instamart.subtotal}, ~${cart.instamart.status})`);
  }

  if (cart.food?.items?.length) {
    parts.push(`${cart.food.items[0].name} from ${cart.food.restaurantName} (₹${cart.food.subtotal}, ~${cart.food.status})`);
  }

  if (cart.dineout_slots?.length) {
    const slot = cart.dineout_slots[0] as { restaurant: string; slot: string; date: string };
    parts.push(`free table at ${slot.restaurant} — ${slot.date}, ${slot.slot}`);
  }

  if (!parts.length) return "Got it — let me put that together for you.";
  if (parts.length === 1) return `Found: ${parts[0]}. Confirm to proceed?`;
  return `Your plan: ${parts.join(" + ")}. Ready to confirm?`;
}

// ── Correction ────────────────────────────────────────────────────────────────

const REMOVAL_SIGNALS = ["remove", "drop", "skip", "don't", "no more", "without", "cancel", "delete", "not"];

export function applyCorrection(
  _originalText: string,
  correction: string,
  currentCart: CartState
): CartState {
  const lower = correction.toLowerCase();

  // Removal — patch existing cart
  if (REMOVAL_SIGNALS.some(w => lower.includes(w))) {
    const updated: CartState = JSON.parse(JSON.stringify(currentCart));

    // Remove whole verticals
    if (lower.includes("instamart") || lower.includes("groceries") || lower.includes("grocery")) delete updated.instamart;
    if (lower.includes("food") || lower.includes("delivery")) delete updated.food;
    if (lower.includes("dineout") || lower.includes("table") || lower.includes("reservation")) delete updated.dineout_slots;

    // Remove specific items by matching token
    const tokens = tokenize(correction).filter(t => t.length > 3 && !REMOVAL_SIGNALS.includes(t));
    if (tokens.length > 0 && updated.food?.items) {
      updated.food.items = updated.food.items.filter(item =>
        !tokens.some(t => item.name.toLowerCase().includes(t))
      );
      updated.food.subtotal = sum(updated.food.items);
      if (updated.food.items.length === 0) delete updated.food;
    }
    if (tokens.length > 0 && updated.instamart?.items) {
      updated.instamart.items = updated.instamart.items.filter(item =>
        !tokens.some(t => item.name.toLowerCase().includes(t))
      );
      updated.instamart.subtotal = sum(updated.instamart.items);
      if (updated.instamart.items.length === 0) delete updated.instamart;
    }

    return updated;
  }

  // New items mentioned → build fresh cart from correction, merge into current
  const correctionCart = buildMockCart(correction);
  const merged: CartState = { ...currentCart };
  if (correctionCart.food)          merged.food = correctionCart.food;
  if (correctionCart.instamart)     merged.instamart = correctionCart.instamart;
  if (correctionCart.dineout_slots) merged.dineout_slots = correctionCart.dineout_slots;
  return merged;
}

// ── Order generation ──────────────────────────────────────────────────────────

export function generateMockOrders(cart: CartState): OrderReference[] {
  const orders: OrderReference[] = [];
  const now = new Date().toISOString();

  if (cart.instamart?.items?.length) {
    orders.push({ order_id: `IM-${Math.random().toString(36).substr(2, 8).toUpperCase()}`, vertical: "instamart", placed_at: now, status: "Packing", eta: cart.instamart.status || "15 min" });
  }
  if (cart.food?.items?.length) {
    orders.push({ order_id: `FD-${Math.random().toString(36).substr(2, 8).toUpperCase()}`, vertical: "food", placed_at: now, status: "Accepted", eta: cart.food.status || "35 min" });
  }
  if (cart.dineout_slots?.length) {
    const slot = cart.dineout_slots[0] as { restaurant: string; slot: string; date: string };
    orders.push({ order_id: `DO-${Math.random().toString(36).substr(2, 8).toUpperCase()}`, vertical: "dineout", placed_at: now, status: "Confirmed", eta: `${slot.date}, ${slot.slot}` });
  }
  return orders;
}
