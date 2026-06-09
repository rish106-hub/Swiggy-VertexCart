"use client";

import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Clock, CheckCircle } from "lucide-react";
import { api } from "../lib/api";
import { OrderReference } from "../lib/types";
import { PoweredBySwiggy } from "./PoweredBySwiggy";

interface OrderStatusProps {
  sessionId: string;
}

export function OrderStatus({ sessionId }: OrderStatusProps) {
  const [orders, setOrders] = useState<OrderReference[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;

    const fetchOrders = async () => {
      try {
        const data = await api.getOrders(sessionId);
        if (mounted) {
          setOrders(data);
          setLoading(false);
        }
      } catch (error) {
        console.error("Failed to fetch orders:", error);
      }
    };

    fetchOrders();

    // Poll every 10 seconds per PRD
    const interval = setInterval(fetchOrders, 10000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [sessionId]);

  const getStatusColor = (vertical: string) => {
    switch (vertical) {
      case "instamart": return "bg-instamart-green";
      case "food": return "bg-swiggy-orange";
      case "dineout": return "bg-dineout-purple";
      default: return "bg-surface-elevated";
    }
  };

  return (
    <div className="min-h-screen pt-20 px-4 md:px-8 max-w-4xl mx-auto flex flex-col relative">
      <div className="absolute top-6 right-6">
        <PoweredBySwiggy />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center mb-12"
      >
        <div className="w-16 h-16 bg-white/10 rounded-full flex items-center justify-center mx-auto mb-6">
          <CheckCircle className="w-8 h-8 text-white" />
        </div>
        <h1 className="text-3xl md:text-4xl font-semibold text-white mb-3">
          Orders Placed
        </h1>
        <p className="text-text-secondary text-base">
          Your requests are being processed by Swiggy.
        </p>
      </motion.div>

      {loading ? (
        <div className="text-center text-text-secondary">Loading your orders...</div>
      ) : (
        <div className="space-y-4">
          {orders.map((order, i) => (
            <motion.div
              key={`${order.order_id}-${order.vertical}`}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              className="bg-surface border border-surface-elevated rounded-2xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-4 relative overflow-hidden"
            >
              {/* Vertical Color Strip */}
              <div className={`absolute left-0 top-0 bottom-0 w-2 ${getStatusColor(order.vertical)}`} />
              
              <div className="pl-4">
                <h3 className="text-white font-semibold capitalize text-lg mb-1">{order.vertical} Order</h3>
                <p className="text-text-secondary text-sm">ID: {order.order_id}</p>
              </div>

              <div className="pl-4 md:pl-0 flex items-center gap-4">
                 <div className="text-right">
                    <div className="text-white font-medium capitalize">{order.status}</div>
                    {order.eta && (
                      <div className="text-text-secondary text-sm flex items-center gap-1 justify-end mt-1">
                        <Clock className="w-3 h-3" /> {order.eta}
                      </div>
                    )}
                 </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
