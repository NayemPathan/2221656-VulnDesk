/**
 * frontend/src/context/DemoUserContext.tsx
 * ----------------------------------------
 * React Context that manages the active Demo Persona across the entire SPA.
 *
 * Why this matters for the Mid-Project MVP Viva:
 * - Allows instant 1-click switching between Alice (Researcher), Bob (Researcher),
 *   Mallory (Banned Researcher), Charlie (Security Analyst), and Nadia (Admin)
 *   in the top navigation bar.
 * - Includes a built-in fallback list matching `backend/app/seed.py` so the
 *   dropdown renders immediately even before the first API call resolves.
 */


import React, { createContext, useContext, useEffect, useState } from "react";
import { api, getStoredDemoEmail, setStoredDemoEmail } from "../api/client";
import { DemoUser } from "../types";


const FALLBACK_USERS: DemoUser[] = [
  {
    id: 1,
    name: "Alice Rahman (Researcher)",
    email: "alice@vulndesk.local",
    role: "researcher",
    is_banned: false,
  },
  {
    id: 2,
    name: "Bob Karim (Researcher)",
    email: "bob@vulndesk.local",
    role: "researcher",
    is_banned: false,
  },
  {
    id: 3,
    name: "Mallory Blocked (Banned Researcher)",
    email: "mallory@vulndesk.local",
    role: "researcher",
    is_banned: true,
  },
  {
    id: 4,
    name: "Charlie Hossain (Security Analyst)",
    email: "charlie@vulndesk.local",
    role: "analyst",
    is_banned: false,
  },
  {
    id: 5,
    name: "Nadia Islam (Admin)",
    email: "admin@vulndesk.local",
    role: "admin",
    is_banned: false,
  },
];


interface DemoUserContextValue {
  users: DemoUser[];
  currentUser: DemoUser;
  selectUserByEmail: (email: string) => void;
  loadingUsers: boolean;
}


const DemoUserContext = createContext<DemoUserContextValue | undefined>(
  undefined
);


export const DemoUserProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [users, setUsers] = useState<DemoUser[]>(FALLBACK_USERS);
  const [selectedEmail, setSelectedEmail] = useState<string>(() =>
    getStoredDemoEmail()
  );
  const [loadingUsers, setLoadingUsers] = useState<boolean>(true);


  useEffect(() => {
    let active = true;
    api
      .getDemoUsers()
      .then((fetched) => {
        if (active && fetched.length > 0) {
          setUsers(fetched);
          const exists = fetched.some((u) => u.email === selectedEmail);
          if (!exists) {
            setSelectedEmail(fetched[0].email);
            setStoredDemoEmail(fetched[0].email);
          }
        }
      })
      .catch(() => {
        // Keep FALLBACK_USERS if backend is warming up
      })
      .finally(() => {
        if (active) setLoadingUsers(false);
      });


    return () => {
      active = false;
    };
  }, [selectedEmail]);


  const selectUserByEmail = (email: string) => {
    setStoredDemoEmail(email);
    setSelectedEmail(email);
  };


  const currentUser =
    users.find((u) => u.email === selectedEmail) || users[0];


  return (
    <DemoUserContext.Provider
      value={{
        users,
        currentUser,
        selectUserByEmail,
        loadingUsers,
      }}
    >
      {children}
    </DemoUserContext.Provider>
  );
};


export function useDemoUser(): DemoUserContextValue {
  const ctx = useContext(DemoUserContext);
  if (!ctx) {
    throw new Error("useDemoUser must be used inside a DemoUserProvider");
  }
  return ctx;
}
