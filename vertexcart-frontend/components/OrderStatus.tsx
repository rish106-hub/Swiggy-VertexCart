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
    <div className="min-h-screen pt-24 px-4 md:px-8 max-w-4xl mx-auto flex flex-col relative bg-background">
      <div className="absolute top-6 right-6">
        <PoweredBySwiggy />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center mb-16"
      >
        <div className="w-20 h-20 bg-swiggy-orange/10 rounded-full flex items-center justify-center mx-auto mb-6 shadow-sm border border-swiggy-orange/20">
          <CheckCircle className="w-10 h-10 text-swiggy-orange" />
        </div>
        <h1 className="text-4xl md:text-5xl font-extrabold text-text-primary mb-4 tracking-tight">
          Orders Placed
        </h1>
        <p className="text-text-secondary text-lg font-medium">
          Your requests are being processed by Swiggy.
        </p>
      </motion.div>

      {loading ? (
        <div className="text-center text-text-secondary font-medium animate-pulse">Loading your orders...</div>
      ) : (
        <div className="space-y-6">
          {orders.map((order, i) => (
            <motion.div
              key={`${order.order_id}-${order.vertical}`}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              className="bg-white border border-border-color rounded-3xl p-6 md:p-8 flex flex-col md:flex-row md:items-center justify-between gap-6 relative overflow-hidden shadow-sm hover:shadow-md transition-shadow"
            >
              {/* Vertical Color Strip */}
              <div className={`absolute left-0 top-0 bottom-0 w-2.5 ${getStatusColor(order.vertical)}`} />
              
              <div className="pl-6">
                <h3 className="text-text-primary font-extrabold capitalize text-xl mb-1.5">{order.vertical} Order</h3>
                <p className="text-text-secondary text-sm font-medium bg-surface-elevated inline-block px-3 py-1 rounded-md border border-border-color/50">ID: {order.order_id}</p>
              </div>

              <div className="pl-6 md:pl-0 flex items-center gap-4">
                 <div className="text-left md:text-right">
                    <div className={`font-bold capitalize text-lg ${order.status.toLowerCase() === 'delivered' ? 'text-green-600' : 'text-swiggy-orange'}`}>{order.status}</div>
                    {order.eta && (
                      <div className="text-text-secondary text-sm font-medium flex items-center gap-1.5 justify-start md:justify-end mt-2 bg-surface-elevated px-3 py-1.5 rounded-lg border border-border-color/50">
                        <Clock className="w-4 h-4 text-text-primary" /> ETA: {order.eta}
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
