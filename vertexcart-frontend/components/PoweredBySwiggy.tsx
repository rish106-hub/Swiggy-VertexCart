import React from "react";

export function PoweredBySwiggy() {
  return (
    <div className="flex items-center gap-1.5 text-xs text-text-secondary select-none bg-surface border border-border-color px-3 py-1.5 rounded-full">
      <div className="w-3.5 h-3.5 rounded-sm bg-swiggy-orange flex items-center justify-center">
        <span className="text-white font-black leading-none" style={{ fontSize: "8px" }}>S</span>
      </div>
      <span className="font-medium">Powered by</span>
      <span className="font-black text-swiggy-orange tracking-tight">SWIGGY</span>
    </div>
  );
}
