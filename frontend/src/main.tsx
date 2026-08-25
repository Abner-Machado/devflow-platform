import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import { applyStoredTheme } from "./hooks/useTheme";
import "./styles/global.css";

// Applied before the first paint so a dark-theme user never sees a white flash.
applyStoredTheme();

const container = document.getElementById("root");
if (!container) throw new Error("Root element #root is missing from index.html.");

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
