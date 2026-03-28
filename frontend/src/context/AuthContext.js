import { createContext, useContext, useState, useCallback, useEffect } from "react";
import axios from "axios";

const API = process.env.REACT_APP_BACKEND_URL + "/api/v1";
const AuthContext = createContext(null);

const STORAGE_KEYS = { TOKEN: "t2t_token", REFRESH: "t2t_refresh", USER: "t2t_user" };

function parseJwt(token) {
  try {
    return JSON.parse(atob(token.split(".")[1]));
  } catch { return null; }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.USER);
      return stored ? JSON.parse(stored) : null;
    } catch { return null; }
  });
  const [token, setToken] = useState(() => localStorage.getItem(STORAGE_KEYS.TOKEN));
  const [refreshTokenVal, setRefreshToken] = useState(() => localStorage.getItem(STORAGE_KEYS.REFRESH));
  const [restoring, setRestoring] = useState(true);
  const [sessionExpired, setSessionExpired] = useState(false);

  // Validate persisted token on mount
  useEffect(() => {
    const storedToken = localStorage.getItem(STORAGE_KEYS.TOKEN);
    if (!storedToken) { setRestoring(false); return; }
    const payload = parseJwt(storedToken);
    if (!payload || payload.exp * 1000 < Date.now()) {
      // Access token expired — check if we have refresh token
      const rt = localStorage.getItem(STORAGE_KEYS.REFRESH);
      if (rt) {
        // Let useApi handle refresh on first API call
        setRestoring(false);
        return;
      }
      // No refresh token — clear everything
      localStorage.removeItem(STORAGE_KEYS.TOKEN);
      localStorage.removeItem(STORAGE_KEYS.REFRESH);
      localStorage.removeItem(STORAGE_KEYS.USER);
      setToken(null);
      setRefreshToken(null);
      setUser(null);
    }
    setRestoring(false);
  }, []);

  // Listen for storage changes from other tabs
  useEffect(() => {
    const handler = (e) => {
      if (e.key === STORAGE_KEYS.TOKEN && !e.newValue) {
        // Token cleared in another tab — logout here too
        setUser(null);
        setToken(null);
        setRefreshToken(null);
        setSessionExpired(true);
      }
      if (e.key === STORAGE_KEYS.USER && e.newValue) {
        try {
          const newUser = JSON.parse(e.newValue);
          setUser((prev) => {
            if (prev && prev.user_id !== newUser.user_id) {
              // Different user in another tab — force reload
              window.location.reload();
            }
            return newUser;
          });
        } catch { /* ignore */ }
      }
    };
    window.addEventListener("storage", handler);
    return () => window.removeEventListener("storage", handler);
  }, []);

  const persist = useCallback((tkn, refreshTkn, userData) => {
    localStorage.setItem(STORAGE_KEYS.TOKEN, tkn);
    if (refreshTkn) localStorage.setItem(STORAGE_KEYS.REFRESH, refreshTkn);
    localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(userData));
  }, []);

  const clearStorage = useCallback(() => {
    localStorage.removeItem(STORAGE_KEYS.TOKEN);
    localStorage.removeItem(STORAGE_KEYS.REFRESH);
    localStorage.removeItem(STORAGE_KEYS.USER);
  }, []);

  const login = useCallback(async (email, password) => {
    const res = await axios.post(`${API}/auth/login`, { email, password });
    const { access_token, refresh_token } = res.data;
    const payload = parseJwt(access_token);
    const userData = {
      user_id: payload.sub,
      email: payload.email,
      role: payload.role,
      account_mode: payload.account_mode || "real",
    };
    setUser(userData);
    setToken(access_token);
    setRefreshToken(refresh_token);
    setSessionExpired(false);
    persist(access_token, refresh_token, userData);
    return userData;
  }, [persist]);

  const logout = useCallback(async () => {
    if (token) {
      try {
        await axios.post(`${API}/auth/logout`, {}, {
          headers: { Authorization: `Bearer ${token}` },
        });
      } catch { /* ignore */ }
    }
    setUser(null);
    setToken(null);
    setRefreshToken(null);
    setSessionExpired(false);
    clearStorage();
  }, [token, clearStorage]);

  const switchMode = useCallback(async (mode) => {
    if (!token) return;
    await axios.post(`${API}/account/switch-mode`, { mode }, {
      headers: { Authorization: `Bearer ${token}` },
    });
    setUser((prev) => {
      if (!prev) return prev;
      const updated = { ...prev, account_mode: mode };
      localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(updated));
      return updated;
    });
  }, [token]);

  // Called by useApi when token is refreshed
  const onTokenRefreshed = useCallback((newToken) => {
    setToken(newToken);
    localStorage.setItem(STORAGE_KEYS.TOKEN, newToken);
  }, []);

  // Called by useApi when refresh fails
  const onSessionExpired = useCallback(() => {
    setSessionExpired(true);
    setUser(null);
    setToken(null);
    setRefreshToken(null);
    clearStorage();
  }, [clearStorage]);

  const dismissSessionExpired = useCallback(() => {
    setSessionExpired(false);
  }, []);

  const isAuthenticated = !!user && !!(token || refreshTokenVal);
  const isAdmin = user?.role === "admin";
  const isDemo = user?.account_mode === "demo";

  return (
    <AuthContext.Provider value={{
      user, token, refreshToken: refreshTokenVal, login, logout, switchMode,
      isAuthenticated, isAdmin, isDemo, restoring,
      sessionExpired, onTokenRefreshed, onSessionExpired, dismissSessionExpired,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be inside AuthProvider");
  return ctx;
}
