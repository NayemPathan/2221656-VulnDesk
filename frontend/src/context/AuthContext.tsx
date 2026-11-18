import React, { createContext, useContext, useEffect, useState } from "react";
import { api, setAccessToken } from "../api/client";
import { AuthUser, LoginPayload, RegisterPayload } from "../types";


interface AuthContextValue {
  currentUser: AuthUser | null;
  initializing: boolean;
  login: (payload: LoginPayload) => Promise<AuthUser>;
  register: (payload: RegisterPayload) => Promise<AuthUser>;
  logout: () => Promise<void>;
  refreshProfile: () => Promise<void>;
}


const AuthContext = createContext<AuthContextValue | undefined>(undefined);


export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [initializing, setInitializing] = useState<boolean>(true);


  useEffect(() => {
    let active = true;
    api
      .refresh()
      .then((res) => {
        if (active && res) {
          setCurrentUser(res.user);
        }
      })
      .finally(() => {
        if (active) setInitializing(false);
      });
    return () => {
      active = false;
    };
  }, []);


  const login = async (payload: LoginPayload): Promise<AuthUser> => {
    const res = await api.login(payload);
    setCurrentUser(res.user);
    return res.user;
  };


  const register = async (payload: RegisterPayload): Promise<AuthUser> => {
    return api.register(payload);
  };


  const logout = async (): Promise<void> => {
    await api.logout();
    setAccessToken(null);
    setCurrentUser(null);
  };


  const refreshProfile = async (): Promise<void> => {
    const me = await api.getMe();
    setCurrentUser(me);
  };


  return (
    <AuthContext.Provider
      value={{
        currentUser,
        initializing,
        login,
        register,
        logout,
        refreshProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};


export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside an AuthProvider");
  }
  return ctx;
}
