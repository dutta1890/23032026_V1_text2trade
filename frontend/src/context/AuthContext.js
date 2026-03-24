import { createContext, useContext, useState, useCallback } from "react";
import axios from "axios";

const API = process.env.REACT_APP_BACKEND_URL + "/api/v1";
const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);

  const login = useCallback(async (email, password) => {
    const res = await axios.post(`${API}/auth/login`, { email, password });
    const { access_token } = res.data;
    const payload = JSON.parse(atob(access_token.split(".")[1]));
    const userData = {
      user_id: payload.sub,
      email: payload.email,
      role: payload.role,
      account_mode: payload.account_mode || "real",
    };
    setUser(userData);
    setToken(access_token);
    return userData;
  }, []);

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
  }, [token]);

  const switchMode = useCallback(async (mode) => {
    if (!token) return;
    await axios.post(`${API}/account/switch-mode`, { mode }, {
      headers: { Authorization: `Bearer ${token}` },
    });
    // Update local state — backend reads mode from DB, not JWT
    setUser((prev) => prev ? { ...prev, account_mode: mode } : prev);
  }, [token]);

  const isAuthenticated = !!user && !!token;
  const isAdmin = user?.role === "admin";
  const isDemo = user?.account_mode === "demo";

  return (
    <AuthContext.Provider value={{ user, token, login, logout, switchMode, isAuthenticated, isAdmin, isDemo }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be inside AuthProvider");
  return ctx;
}
