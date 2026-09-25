"use client";
import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { useRouter, usePathname } from "next/navigation";
import { api } from "./api";

type AuthState = { email: string | null; isAdmin: boolean; ready: boolean };
type AuthCtx = AuthState & { login: (e: string, p: string) => Promise<void>; logout: () => void };

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ email: null, isAdmin: false, ready: false });
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    const email = window.localStorage.getItem("ft_email");
    const isAdmin = window.localStorage.getItem("ft_admin") === "1";
    const token = window.localStorage.getItem("ft_token");
    setState({ email: token ? email : null, isAdmin: token ? isAdmin : false, ready: true });
  }, []);

  useEffect(() => {
    if (state.ready && !state.email && pathname !== "/login") {
      router.replace("/login");
    }
  }, [state.ready, state.email, pathname, router]);

  const login = async (email: string, password: string) => {
    const res = await api.login(email, password);
    window.localStorage.setItem("ft_token", res.access_token);
    window.localStorage.setItem("ft_email", res.email);
    window.localStorage.setItem("ft_admin", res.is_admin ? "1" : "0");
    setState({ email: res.email, isAdmin: res.is_admin, ready: true });
    router.replace("/");
  };

  const logout = () => {
    window.localStorage.removeItem("ft_token");
    window.localStorage.removeItem("ft_email");
    window.localStorage.removeItem("ft_admin");
    setState({ email: null, isAdmin: false, ready: true });
    router.replace("/login");
  };

  return <Ctx.Provider value={{ ...state, login, logout }}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
