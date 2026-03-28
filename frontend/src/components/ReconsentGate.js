import { useAuth } from "@/context/AuthContext";
import ReconsentModal from "@/components/ReconsentModal";

/**
 * Renders the re-consent modal when a logged-in user hasn't accepted latest legal docs.
 * Placed at the app root, inside AuthProvider and BrowserRouter.
 */
export default function ReconsentGate() {
  const { isAuthenticated, restoring } = useAuth();
  if (restoring || !isAuthenticated) return null;
  return <ReconsentModal />;
}
