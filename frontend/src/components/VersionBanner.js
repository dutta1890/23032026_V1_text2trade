import { useState, useEffect } from "react";
import { X, RefreshCw } from "lucide-react";
import axios from "axios";

const API = process.env.REACT_APP_BACKEND_URL + "/api/v1";
const FRONTEND_VERSION = process.env.REACT_APP_VERSION || "0.2.0";

function compareVersions(a, b) {
  const pa = a.split(".").map(Number);
  const pb = b.split(".").map(Number);
  for (let i = 0; i < 3; i++) {
    if ((pa[i] || 0) < (pb[i] || 0)) return -1;
    if ((pa[i] || 0) > (pb[i] || 0)) return 1;
  }
  return 0;
}

export default function VersionBanner() {
  const [outdated, setOutdated] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    axios.get(`${API}/app/version`)
      .then((res) => {
        const min = res.data.min_supported_version;
        if (min && compareVersions(FRONTEND_VERSION, min) < 0) {
          setOutdated(true);
        }
      })
      .catch(() => {});
  }, []);

  if (!outdated || dismissed) return null;

  return (
    <div className="fixed top-0 left-0 right-0 z-[50] bg-amber-500/90 text-black px-4 py-2 flex items-center justify-center gap-3 text-xs font-mono" data-testid="version-banner">
      <RefreshCw className="w-3.5 h-3.5" />
      <span>A newer version is available. Please refresh your browser for the latest version.</span>
      <button onClick={() => window.location.reload()} className="underline font-bold">Refresh</button>
      <button onClick={() => setDismissed(true)} className="ml-2"><X className="w-3.5 h-3.5" /></button>
    </div>
  );
}
