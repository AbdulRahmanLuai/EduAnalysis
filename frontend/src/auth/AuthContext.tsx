import { createContext, useContext, useState, ReactNode } from "react";
import client from "../api/client";

interface AuthState {
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [token, setToken] = useState<string | null>(
    localStorage.getItem("access_token")
  );

  const isAuthenticated = !!token;

  const storeToken = (access_token: string) => {
    localStorage.setItem("access_token", access_token);
    setToken(access_token);
  };

  const login = async (email: string, password: string) => {
    const res = await client.post("/auth/login", { email, password });
    storeToken(res.data.access_token);
  };

  const register = async (email: string, password: string) => {
    const res = await client.post("/auth/signup", { email, password });
    storeToken(res.data.access_token);
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    setToken(null);
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
};
