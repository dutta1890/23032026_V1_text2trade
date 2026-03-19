import { useState, useEffect } from "react";
import { useApi } from "@/hooks/useApi";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, Users, Search } from "lucide-react";
import { Input } from "@/components/ui/input";

export default function AdminUsers() {
  const api = useApi();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    api.get("/admin/users").then((r) => setUsers(r.data.users || [])).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const filtered = search ? users.filter((u) => u.email?.toLowerCase().includes(search.toLowerCase())) : users;

  if (loading) return <div className="flex items-center justify-center py-32"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>;

  return (
    <div className="space-y-6" data-testid="admin-users-page">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">User Management</h1>
          <p className="text-sm text-muted-foreground mt-1">{users.length} registered users. Strategy content is private.</p>
        </div>
        <div className="relative w-full sm:w-64">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
          <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search email..." className="pl-9 font-mono text-xs h-9" data-testid="user-search" />
        </div>
      </div>

      <Card className="border-border bg-card">
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left" data-testid="users-table">
              <thead>
                <tr className="border-b border-border bg-secondary/30">
                  <th className="py-3 px-4 mono-label text-[10px]">EMAIL</th>
                  <th className="py-3 px-4 mono-label text-[10px]">ROLE</th>
                  <th className="py-3 px-4 mono-label text-[10px]">REGISTERED</th>
                  <th className="py-3 px-4 mono-label text-[10px]">STRATEGIES</th>
                  <th className="py-3 px-4 mono-label text-[10px]">AI CALLS</th>
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr><td colSpan={5} className="py-8 text-center text-xs text-muted-foreground">No users found.</td></tr>
                ) : filtered.map((u, i) => (
                  <tr key={u.user_id || u.email || i} className="border-b border-border/50 hover:bg-secondary/20 transition-colors" data-testid={`user-row-${i}`}>
                    <td className="py-3 px-4 font-mono text-xs text-foreground">{u.email}</td>
                    <td className="py-3 px-4"><span className={`text-[10px] font-mono uppercase px-1.5 py-0.5 ${u.role === "admin" ? "bg-destructive/20 text-destructive" : "bg-primary/20 text-primary"}`}>{u.role || "user"}</span></td>
                    <td className="py-3 px-4 font-mono text-xs text-muted-foreground">{u.created_at ? new Date(u.created_at).toLocaleDateString() : "—"}</td>
                    <td className="py-3 px-4 font-mono text-xs text-foreground tabular-nums">{u.strategy_count ?? "—"}</td>
                    <td className="py-3 px-4 font-mono text-xs text-foreground tabular-nums">{u.ai_calls_today ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <p className="text-[10px] text-muted-foreground font-mono text-center">Privacy: Strategy content is not accessible from this panel.</p>
    </div>
  );
}
