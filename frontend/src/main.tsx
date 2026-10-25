/**
 * frontend/src/main.tsx
 * ---------------------
 * Vite React 18 entrypoint that mounts `<App />` into `#root`.
 */


import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";


ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

