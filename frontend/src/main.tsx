import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router";
import App from "./app/App.tsx";
import { LandingPage } from "./app/landing-page.tsx";
import "./styles/index.css";

createRoot(document.getElementById("root")!).render(
  <BrowserRouter>
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/agent" element={<App />} />
      <Route path="/landing-page" element={<Navigate to="/" replace />} />
      <Route path="/assistant" element={<Navigate to="/agent" replace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  </BrowserRouter>,
);
