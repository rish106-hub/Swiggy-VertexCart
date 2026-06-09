import React, { useState } from "react";
import { Send } from "lucide-react";
import { IntentResult } from "../lib/types";

interface AgentReasoningProps {
  intent: IntentResult;
  onCorrect: (text: string) => void;
}

export function AgentReasoning({ intent, onCorrect }: AgentReasoningProps) {
  const [correctionText, setCorrectionText] = useState("");

  const handleCorrection = (e: React.FormEvent) => {
    e.preventDefault();
    if (correctionText.trim()) {
      onCorrect(correctionText.trim());
      setCorrectionText("");
    }
  };

  return (
    <div className="bg-white border border-border-color rounded-2xl p-6 sticky top-8 shadow-sm">
      <h3 className="text-text-primary font-bold mb-5 flex items-center gap-2">
        <span className="text-swiggy-orange">⚡️</span> Intent Breakdown
      </h3>
      <div className="space-y-4 mb-8">
        {intent.entities.map((ent, i) => (
          <div key={i} className="flex justify-between items-center text-sm border-b border-border-color pb-3">
            <span className="text-text-secondary font-medium">&quot;{ent.text}&quot;</span>
            <span className={`px-2.5 py-1 rounded-md text-xs font-bold
              ${ent.vertical === 'instamart' ? 'bg-instamart-green/10 text-instamart-green' : 
                ent.vertical === 'food' ? 'bg-swiggy-orange/10 text-swiggy-orange' : 
                'bg-dineout-purple/10 text-dineout-purple'}`}
            >
              {ent.vertical}
            </span>
          </div>
        ))}
      </div>

      <form onSubmit={handleCorrection} className="mt-8">
        <label className="text-xs text-text-secondary mb-3 block font-semibold uppercase tracking-wider">
          Need to change something?
        </label>
        <div className="relative group">
          <input 
            type="text"
            value={correctionText}
            onChange={(e) => setCorrectionText(e.target.value)}
            placeholder="e.g. drop the dessert..."
            className="w-full bg-surface-elevated border border-border-color rounded-xl px-4 py-3 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-swiggy-orange/50 focus:border-swiggy-orange pr-12 transition-all"
          />
          <button 
            type="submit"
            disabled={!correctionText.trim()}
            className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 flex items-center justify-center rounded-lg text-white bg-swiggy-orange hover:bg-orange-600 disabled:opacity-50 disabled:bg-surface-elevated disabled:text-text-secondary transition-all"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </form>
    </div>
  );
}
