/**
 * Safely extract a human-readable error message from an Axios error.
 * Handles both string `detail` and Pydantic validation array `detail`.
 */
export function extractApiError(err, fallback = "Something went wrong") {
  const detail = err?.response?.data?.detail;
  if (!detail) return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((e) => {
        const msg = e.msg || "";
        return msg.replace(/^Value error, /i, "");
      })
      .join(". ");
  }
  return fallback;
}
