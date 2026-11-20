import React, { createContext, useContext, useEffect, useState } from "react";


type Theme = "light" | "dark";
interface ThemeContextValue {
  theme: Theme;
  toggleTheme: () => void;
}


const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);
const THEME_KEY = "vulndesk_theme";


export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [theme, setTheme] = useState<Theme>(() => {
    const saved = localStorage.getItem(THEME_KEY);
    if (saved === "dark" || saved === "light") return saved;
    return window.matchMedia?.("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  });


  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);


  const toggleTheme = () => {
    setTheme((prev) => (prev === "light" ? "dark" : "light"));
  };


  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};


export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used inside ThemeProvider");
  return ctx;
}
