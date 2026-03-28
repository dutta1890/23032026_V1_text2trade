import { useState, useCallback, useMemo, useRef } from "react";
import { useAuth } from "@/context/AuthContext";
import axios from "axios";

const API = process.env.REACT_APP_BACKEND_URL + "/api/v1";

/**
 * API hook with silent token refresh on 401.
 * - If access token expires, attempts refresh via /auth/refresh
 * - If refresh succeeds, retries original request transparently
 * - If refresh fails, triggers session expired state
 */
export function useApi() {
  const { token, refreshToken, onTokenRefreshed, onSessionExpired } = useAuth();
  const isRefreshing = useRef(false);
  const pendingQueue = useRef([]);

  const headers = useMemo(
    () => (token ? { Authorization: `Bearer ${token}` } : {}),
    [token]
  );

  const processQueue = useCallback((newToken) => {
    pendingQueue.current.forEach(({ resolve }) => resolve(newToken));
    pendingQueue.current = [];
  }, []);

  const failQueue = useCallback(() => {
    pendingQueue.current.forEach(({ reject }) => reject(new Error("Session expired")));
    pendingQueue.current = [];
  }, []);

  const attemptRefresh = useCallback(async () => {
    if (isRefreshing.current) {
      return new Promise((resolve, reject) => {
        pendingQueue.current.push({ resolve, reject });
      });
    }
    isRefreshing.current = true;
    try {
      const res = await axios.post(`${API}/auth/refresh`, {
        refresh_token: refreshToken,
      });
      const newToken = res.data.access_token;
      onTokenRefreshed(newToken);
      processQueue(newToken);
      isRefreshing.current = false;
      return newToken;
    } catch {
      failQueue();
      isRefreshing.current = false;
      onSessionExpired();
      throw new Error("Session expired");
    }
  }, [refreshToken, onTokenRefreshed, onSessionExpired, processQueue, failQueue]);

  const request = useCallback(
    async (method, url, data, extraHeaders = {}) => {
      const fullUrl = `${API}${url}`;
      const config = { method, url: fullUrl, headers: { ...headers, ...extraHeaders } };
      if (data !== undefined) config.data = data;

      try {
        return await axios(config);
      } catch (err) {
        // On 401, attempt silent refresh
        if (err.response?.status === 401 && refreshToken) {
          try {
            const newToken = await attemptRefresh();
            config.headers = { ...config.headers, Authorization: `Bearer ${newToken}` };
            return await axios(config);
          } catch {
            throw err;
          }
        }
        throw err;
      }
    },
    [headers, refreshToken, attemptRefresh]
  );

  const get = useCallback((url, extra) => request("GET", url, undefined, extra), [request]);
  const post = useCallback((url, data, extra) => request("POST", url, data, extra), [request]);
  const put = useCallback((url, data, extra) => request("PUT", url, data, extra), [request]);
  const del = useCallback((url, extra) => request("DELETE", url, undefined, extra), [request]);

  return { get, post, put, del };
}
