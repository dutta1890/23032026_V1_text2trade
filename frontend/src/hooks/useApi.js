import { useCallback, useMemo } from "react";
import axios from "axios";
import { useAuth } from "../context/AuthContext";

const BASE = process.env.REACT_APP_BACKEND_URL + "/api/v1";

export function useApi() {
  const { token } = useAuth();

  const headers = useMemo(
    () => (token ? { Authorization: `Bearer ${token}` } : {}),
    [token]
  );

  const get = useCallback((path) => axios.get(`${BASE}${path}`, { headers }), [headers]);
  const post = useCallback((path, data) => axios.post(`${BASE}${path}`, data, { headers }), [headers]);
  const put = useCallback((path, data) => axios.put(`${BASE}${path}`, data, { headers }), [headers]);
  const del = useCallback((path, config) => axios.delete(`${BASE}${path}`, { headers, ...config }), [headers]);

  return { get, post, put, del };
}
