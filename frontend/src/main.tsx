import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router";
import App from "./app/App.tsx";
import { LandingPage } from "./app/landing-page.tsx";
import "./styles/index.css";

createRoot(document.getElementById("root")!).render(
  <BrowserRouter>
    <Routes>
      <Route path="/landing-page" element={<LandingPage />} />
      <Route path="/assistant" element={<App />} />
      <Route path="*" element={<App />} />
    </Routes>
  </BrowserRouter>,
);
