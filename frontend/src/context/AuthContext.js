import { createContext, useContext, useState, useCallback } from "react";
import axios from "axios";

const API = process.env.REACT_APP_BACKEND_URL + "/api/v1";
const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);

  const login = useCallback((userData, accessToken) => {
    setUser(userData);
    setToken(accessToken);
  }, []);

  const logout = useCallback(async () => {
    if (token) {
      try {
        await axios.post(`${API}/auth/logout`, {}, {
          headers: { Authorization: `Bearer ${token}` },
        });
      } catch { /* ignore - token might be expired */ }
    }
    setUser(null);
    setToken(null);
  }, [token]);

  const isAuthenticated = !!user && !!token;
  const isAdmin = user?.role === "admin";

  return (
    <AuthContext.Provider value={{ user, token, login, logout, isAuthenticated, isAdmin }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be inside AuthProvider");
  return ctx;
}
