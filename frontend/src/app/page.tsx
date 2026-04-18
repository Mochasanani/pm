"use client";

import { useEffect, useState } from "react";
import { KanbanBoard } from "@/components/KanbanBoard";
import { LoginPage } from "@/components/LoginPage";
import { getMe, type User } from "@/lib/api";

export default function Home() {
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    getMe().then((me) => {
      setUser(me);
      setChecking(false);
    });
  }, []);

  if (checking) return null;

  if (!user) {
    return (
      <LoginPage
        onAuthenticated={() => {
          // LoginPage already received the user from the API; refetch to
          // populate the full record here.
          getMe().then((me) => setUser(me));
        }}
      />
    );
  }

  return (
    <KanbanBoard
      user={user}
      onUserUpdated={(u) => setUser(u)}
      onLogout={() => setUser(null)}
    />
  );
}
