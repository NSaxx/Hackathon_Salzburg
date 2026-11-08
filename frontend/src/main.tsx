import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
// Must stay first so the app's styles can override Leaflet's defaults.
import "leaflet/dist/leaflet.css";
import "./index.css";
import App from "./App.tsx";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
