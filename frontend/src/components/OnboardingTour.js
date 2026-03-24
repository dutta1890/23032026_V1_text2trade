import { useState, useEffect } from "react";
import { Joyride, STATUS } from "react-joyride";
import { useAuth } from "@/context/AuthContext";
import { useApi } from "@/hooks/useApi";
import tourConfig from "@/config/tour_config.json";

const joyrideStyles = {
  options: {
    arrowColor: "hsl(240, 6%, 12%)",
    backgroundColor: "hsl(240, 6%, 12%)",
    overlayColor: "rgba(0, 0, 0, 0.75)",
    primaryColor: "hsl(156, 100%, 45%)",
    textColor: "hsl(0, 0%, 90%)",
    zIndex: 10000,
  },
  tooltip: {
    borderRadius: 4,
    border: "1px solid hsl(240, 4%, 20%)",
    padding: "16px",
  },
  tooltipTitle: {
    fontSize: 14,
    fontWeight: 700,
    fontFamily: "'JetBrains Mono', monospace",
  },
  tooltipContent: {
    fontSize: 12,
    lineHeight: 1.6,
    padding: "8px 0 0",
    fontFamily: "'JetBrains Mono', monospace",
  },
  buttonNext: {
    backgroundColor: "hsl(156, 100%, 45%)",
    color: "hsl(240, 6%, 6%)",
    fontSize: 11,
    fontFamily: "'JetBrains Mono', monospace",
    fontWeight: 600,
    borderRadius: 2,
    padding: "6px 16px",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
  },
  buttonBack: {
    color: "hsl(240, 5%, 65%)",
    fontSize: 11,
    fontFamily: "'JetBrains Mono', monospace",
  },
  buttonSkip: {
    color: "hsl(240, 5%, 45%)",
    fontSize: 10,
    fontFamily: "'JetBrains Mono', monospace",
  },
};

export default function OnboardingTour({ run, onComplete }) {
  const api = useApi();

  const handleCallback = (data) => {
    const { status } = data;
    if ([STATUS.FINISHED, STATUS.SKIPPED].includes(status)) {
      api.post("/account/complete-onboarding").catch(() => {});
      if (onComplete) onComplete();
    }
  };

  return (
    <Joyride
      steps={tourConfig.steps.map((s) => ({
        target: s.target,
        title: s.title,
        content: s.content,
        placement: s.placement || "bottom",
        disableBeacon: s.disableBeacon || false,
      }))}
      run={run}
      continuous
      showSkipButton
      showProgress
      scrollToFirstStep
      disableOverlayClose
      callback={handleCallback}
      locale={{ back: "Back", close: "Close", last: "Done", next: "Next", skip: "Skip Tour" }}
      styles={joyrideStyles}
    />
  );
}
