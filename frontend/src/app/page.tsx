"use client";

import { useEffect, useState } from "react";
import { KanbanBoard } from "@/components/KanbanBoard";
import { LoginPage } from "@/components/LoginPage";
import { getMe } from "@/lib/auth";

export default function Home() {
  const [user, setUser] = useState<string | null>(null);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    getMe().then((me) => {
      setUser(me?.username ?? null);
      setChecking(false);
    });
  }, []);

  if (checking) return null;

  if (!user) {
    return <LoginPage onLogin={() => setUser("user")} />;
  }

  return <KanbanBoard user={user} onLogout={() => setUser(null)} />;
}
