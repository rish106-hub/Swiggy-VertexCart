"use client";

import React, { useEffect, useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Clock, RotateCcw, CheckCircle } from "lucide-react";
import { api } from "../lib/api";
import { OrderReference } from "../lib/types";
import { PoweredBySwiggy } from "./PoweredBySwiggy";

interface OrderStatusProps {
  sessionId: string;
  onNewOrder: () => void;
}

const STATUS_STAGES = {
  instamart: ["Packing", "Picked up", "On the way", "Delivered"],
  food: ["Accepted", "Preparing", "On the way", "Delivered"],
  dineout: ["Confirmed", "Reminder sent", "Enjoy your dinner!"],
};

const VERTICAL_CONFIG = {
  instamart: { color: "#00B383", bg: "rgba(0,179,131,0.08)", border: "rgba(0,179,131,0.2)", label: "Instamart", emoji: "🛒" },
  food: { color: "#FF5200", bg: "rgba(255,82,0,0.08)", border: "rgba(255,82,0,0.2)", label: "Swiggy Food", emoji: "🍔" },
  dineout: { color: "#8B5CF6", bg: "rgba(139,92,246,0.08)", border: "rgba(139,92,246,0.2)", label: "Dineout", emoji: "🍽️" },
};

// Confetti particle
const CONFETTI_COLORS = ["#FF5200", "#00B383", "#8B5CF6", "#FFD700", "#FF4B91"];

function ConfettiPiece({ delay, color }: { delay: number; color: string }) {
  const left = `${Math.random() * 100}%`;
  return (
    <motion.div
      className="fixed top-0 w-2.5 h-2.5 rounded-sm pointer-events-none z-50"
      style={{ left, background: color }}
      initial={{ y: -20, opacity: 1, rotate: 0 }}
      animate={{ y: "110vh", opacity: [1, 1, 0], rotate: Math.random() * 720 - 360 }}
      transition={{ duration: 2.5 + Math.random(), delay, ease: "easeIn" }}
    />
  );
}

export function OrderStatus({ sessionId, onNewOrder }: OrderStatusProps) {
  const [orders, setOrders] = useState<OrderReference[]>([]);
  const [loading, setLoading] = useState(true);
  const [showConfetti, setShowConfetti] = useState(false);
  const hasFiredConfetti = useRef(false);

  useEffect(() => {
    let mounted = true;
    const fetchOrders = async () => {
      try {
        const data = await api.getOrders(sessionId);
        if (mounted) {
          setOrders(data);
          setLoading(false);
          if (!hasFiredConfetti.current && data.length > 0) {
            hasFiredConfetti.current = true;
            setShowConfetti(true);
            setTimeout(() => setShowConfetti(false), 3000);
          }
        }
      } catch {
        if (mounted) setLoading(false);
      }
    };

    fetchOrders();
    const interval = setInterval(fetchOrders, 10000);
    return () => { mounted = false; clearInterval(interval); };
  }, [sessionId]);

  const confettiPieces = Array.from({ length: 30 }, (_, i) => ({
    id: i,
    delay: i * 0.05,
    color: CONFETTI_COLORS[i % CONFETTI_COLORS.length],
  }));

  return (
    <div className="min-h-screen pt-16 px-4 pb-12 max-w-2xl mx-auto relative">
      {/* Confetti burst */}
      <AnimatePresence>
        {showConfetti && confettiPieces.map(p => (
          <ConfettiPiece key={p.id} delay={p.delay} color={p.color} />
        ))}
      </AnimatePresence>

      <div className="absolute top-6 right-6">
        <PoweredBySwiggy />
      </div>

      {/* Success header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: "spring", stiffness: 300, damping: 22 }}
        className="text-center mb-12"
      >
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 400, damping: 16, delay: 0.1 }}
          className="w-20 h-20 mx-auto mb-5 rounded-2xl flex items-center justify-center"
          style={{ background: "rgba(255,82,0,0.12)", border: "1px solid rgba(255,82,0,0.25)", boxShadow: "0 0 30px rgba(255,82,0,0.2)" }}
        >
          <CheckCircle className="w-10 h-10 text-swiggy-orange" />
        </motion.div>
        <motion.h1
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="text-4xl font-black text-text-primary mb-2"
        >
          You&apos;re all set! 🎉
        </motion.h1>
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="text-text-secondary font-medium"
        >
          {orders.length} {orders.length === 1 ? "order" : "orders"} confirmed · Sit back and relax
        </motion.p>
      </motion.div>

      {/* Order cards */}
      {loading ? (
        <div className="space-y-4">
          {[1, 2].map(i => (
            <div key={i} className="skeleton h-28 rounded-2xl" />
          ))}
        </div>
      ) : (
        <div className="space-y-4">
          {orders.map((order, i) => {
            const cfg = VERTICAL_CONFIG[order.vertical] || VERTICAL_CONFIG.food;
            const stages = STATUS_STAGES[order.vertical] || STATUS_STAGES.food;
            const stageIdx = stages.findIndex(s => s.toLowerCase() === order.status.toLowerCase());
            const currentStage = stageIdx >= 0 ? stageIdx : 0;

            return (
              <motion.div
                key={order.order_id}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ type: "spring", stiffness: 300, damping: 24, delay: i * 0.12 }}
                className="rounded-2xl overflow-hidden"
                style={{ background: cfg.bg, border: `1px solid ${cfg.border}` }}
              >
                {/* Card header */}
                <div className="px-5 py-4 flex items-center justify-between" style={{ borderBottom: `1px solid ${cfg.border}` }}>
                  <div className="flex items-center gap-3">
                    <span className="text-xl">{cfg.emoji}</span>
                    <div>
                      <div className="font-bold text-text-primary">{cfg.label}</div>
                      <div className="text-xs text-text-secondary font-mono mt-0.5">{order.order_id}</div>
                    </div>
                  </div>
                  <div
                    className="text-xs font-bold px-3 py-1.5 rounded-xl"
                    style={{ color: cfg.color, background: `${cfg.color}18` }}
                  >
                    {order.status}
                  </div>
                </div>

                {/* Progress stages */}
                <div className="px-5 py-4">
                  <div className="flex items-center gap-1 mb-4">
                    {stages.map((stage, idx) => (
                      <React.Fragment key={stage}>
                        <div className="flex flex-col items-center gap-1.5 flex-1 min-w-0">
                          <motion.div
                            animate={{ scale: idx === currentStage ? 1.15 : 1 }}
                            className="w-3 h-3 rounded-full border-2"
                            style={{
                              background: idx <= currentStage ? cfg.color : "transparent",
                              borderColor: idx <= currentStage ? cfg.color : "#3E3E3E",
                              boxShadow: idx === currentStage ? `0 0 8px ${cfg.color}` : "none",
                            }}
                          />
                          <span
                            className="text-center leading-tight"
                            style={{
                              fontSize: "9px",
                              color: idx <= currentStage ? cfg.color : "#555",
                              fontWeight: idx === currentStage ? 700 : 500,
                              maxWidth: "50px",
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                              whiteSpace: "nowrap",
                            }}
                          >
                            {stage}
                          </span>
                        </div>
                        {idx < stages.length - 1 && (
                          <div
                            className="h-0.5 flex-1 rounded-full mb-4"
                            style={{ background: idx < currentStage ? cfg.color : "#2E2E2E" }}
                          />
                        )}
                      </React.Fragment>
                    ))}
                  </div>

                  {order.eta && (
                    <div className="flex items-center gap-2 text-text-secondary text-sm font-medium">
                      <Clock className="w-3.5 h-3.5" style={{ color: cfg.color }} />
                      <span>ETA: <span className="text-text-primary font-bold">{order.eta}</span></span>
                    </div>
                  )}
                </div>
              </motion.div>
            );
          })}
        </div>
      )}

      {/* New order CTA */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.6 }}
        className="text-center mt-12"
      >
        <button
          onClick={onNewOrder}
          className="btn-ripple inline-flex items-center gap-2 px-6 py-3 bg-surface border border-border-color rounded-2xl text-text-secondary hover:text-text-primary text-sm font-semibold transition-all hover:border-swiggy-orange/40"
        >
          <RotateCcw className="w-4 h-4" />
          Start a new order
        </button>
      </motion.div>
    </div>
  );
}
