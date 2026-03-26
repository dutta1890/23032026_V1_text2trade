import { createContext, useContext, useState, useCallback, useEffect } from "react";
import axios from "axios";

const API = process.env.REACT_APP_BACKEND_URL + "/api/v1";
const AuthContext = createContext(null);

const STORAGE_KEYS = { TOKEN: "t2t_token", USER: "t2t_user" };

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
  const [restoring, setRestoring] = useState(true);

  // Validate persisted token on mount
  useEffect(() => {
    const storedToken = localStorage.getItem(STORAGE_KEYS.TOKEN);
    if (!storedToken) { setRestoring(false); return; }
    const payload = parseJwt(storedToken);
    if (!payload || payload.exp * 1000 < Date.now()) {
      // Token expired — clear
      localStorage.removeItem(STORAGE_KEYS.TOKEN);
      localStorage.removeItem(STORAGE_KEYS.USER);
      setToken(null);
      setUser(null);
      setRestoring(false);
      return;
    }
    // Token still valid — restore
    setRestoring(false);
  }, []);

  const persist = useCallback((tkn, userData) => {
    localStorage.setItem(STORAGE_KEYS.TOKEN, tkn);
    localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(userData));
  }, []);

  const clearStorage = useCallback(() => {
    localStorage.removeItem(STORAGE_KEYS.TOKEN);
    localStorage.removeItem(STORAGE_KEYS.USER);
  }, []);

  const login = useCallback(async (email, password) => {
    const res = await axios.post(`${API}/auth/login`, { email, password });
    const { access_token } = res.data;
    const payload = parseJwt(access_token);
    const userData = {
      user_id: payload.sub,
      email: payload.email,
      role: payload.role,
      account_mode: payload.account_mode || "real",
    };
    setUser(userData);
    setToken(access_token);
    persist(access_token, userData);
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

  const isAuthenticated = !!user && !!token;
  const isAdmin = user?.role === "admin";
  const isDemo = user?.account_mode === "demo";

  return (
    <AuthContext.Provider value={{ user, token, login, logout, switchMode, isAuthenticated, isAdmin, isDemo, restoring }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be inside AuthProvider");
  return ctx;
}
