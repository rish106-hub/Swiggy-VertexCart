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
    <div className="bg-surface border border-surface-elevated rounded-xl p-5 sticky top-8">
      <h3 className="text-white font-medium mb-4">Intent Breakdown</h3>
      <div className="space-y-4 mb-6">
        {intent.entities.map((ent, i) => (
          <div key={i} className="flex justify-between items-center text-sm border-b border-surface-elevated pb-2">
            <span className="text-text-secondary">&quot;{ent.text}&quot;</span>
            <span className={`px-2 py-0.5 rounded text-xs
              ${ent.vertical === 'instamart' ? 'bg-instamart-green/20 text-instamart-green' : 
                ent.vertical === 'food' ? 'bg-swiggy-orange/20 text-swiggy-orange' : 
                'bg-dineout-purple/20 text-dineout-purple'}`}
            >
              {ent.vertical}
            </span>
          </div>
        ))}
      </div>

      <form onSubmit={handleCorrection} className="mt-8">
        <label className="text-xs text-text-secondary mb-2 block uppercase tracking-wider">
          Need to change something?
        </label>
        <div className="relative">
          <input 
            type="text"
            value={correctionText}
            onChange={(e) => setCorrectionText(e.target.value)}
            placeholder="e.g. drop the dessert..."
            className="w-full bg-background border border-surface-elevated rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-swiggy-orange pr-10"
          />
          <button 
            type="submit"
            disabled={!correctionText.trim()}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-text-secondary hover:text-white disabled:opacity-50"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </form>
    </div>
  );
}
