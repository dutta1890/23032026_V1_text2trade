import { useState, useEffect, useCallback } from "react";
import { Info } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import axios from "axios";

const API = process.env.REACT_APP_BACKEND_URL + "/api/v1";

let _cache = null;
let _fetching = false;
let _listeners = [];

function fetchKnowledge() {
  if (_cache) return Promise.resolve(_cache);
  if (_fetching) {
    return new Promise((resolve) => _listeners.push(resolve));
  }
  _fetching = true;
  return axios
    .get(`${API}/knowledge`)
    .then((res) => {
      const map = {};
      (res.data.entries || []).forEach((e) => {
        map[e.term_id] = e;
      });
      _cache = map;
      _fetching = false;
      _listeners.forEach((fn) => fn(map));
      _listeners = [];
      return map;
    })
    .catch(() => {
      _fetching = false;
      _listeners.forEach((fn) => fn({}));
      _listeners = [];
      return {};
    });
}

export function useKnowledge() {
  const [kb, setKb] = useState(_cache || null);
  useEffect(() => {
    if (_cache) {
      setKb(_cache);
      return;
    }
    fetchKnowledge().then(setKb);
  }, []);
  return kb;
}

export function InfoTooltip({ termId, className = "" }) {
  const kb = useKnowledge();
  const entry = kb?.[termId];
  if (!entry) return null;

  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            className={`inline-flex items-center justify-center w-4 h-4 text-muted-foreground hover:text-primary transition-colors focus:outline-none ${className}`}
            data-testid={`info-tooltip-${termId}`}
          >
            <Info className="w-3.5 h-3.5" />
          </button>
        </TooltipTrigger>
        <TooltipContent
          side="top"
          className="max-w-xs bg-card border border-border text-foreground p-3 shadow-lg"
        >
          <p className="font-mono text-[11px] font-bold text-primary mb-1">
            {entry.term}
          </p>
          <p className="text-[11px] leading-relaxed text-muted-foreground">
            {entry.short_description}
          </p>
          {entry.example && (
            <p className="text-[10px] leading-relaxed text-muted-foreground/70 mt-1.5 pt-1.5 border-t border-border/50 italic">
              {entry.example}
            </p>
          )}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
