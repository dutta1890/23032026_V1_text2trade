import { createContext, useContext, useState, useCallback, useMemo } from "react";
import axios from "axios";

const AuthContext = createContext(null);
const API = process.env.REACT_APP_BACKEND_URL + "/api/v1";

function decodeJwt(token) {
  try {
    const payload = token.split(".")[1];
    return JSON.parse(atob(payload));
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [accessToken, setAccessToken] = useState(null);
  const [user, setUser] = useState(null);

  const login = useCallback(async (email, password) => {
    const res = await axios.post(`${API}/auth/login`, { email, password });
    const token = res.data.access_token;
    const decoded = decodeJwt(token);
    setAccessToken(token);
    setUser({ email: decoded?.sub || email, role: decoded?.role || "user", userId: decoded?.user_id });
    return decoded;
  }, []);

  const register = useCallback(async (email, password) => {
    await axios.post(`${API}/auth/register`, { email, password });
  }, []);

  const logout = useCallback(() => {
    setAccessToken(null);
    setUser(null);
  }, []);

  const value = useMemo(() => ({
    user,
    token: accessToken,
    isAuthenticated: !!accessToken,
    isAdmin: user?.role === "admin",
    login,
    register,
    logout,
  }), [user, accessToken, login, register, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be inside AuthProvider");
  return ctx;
}
