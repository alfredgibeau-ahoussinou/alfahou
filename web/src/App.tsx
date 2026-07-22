import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AppShell } from "./AppShell";
import { IntroPage } from "./pages/IntroPage";
import { ManifestPage } from "./pages/ManifestPage";
import { StudioPage } from "./pages/StudioPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<IntroPage />} />
          <Route path="manifeste" element={<ManifestPage />} />
          <Route path="atelier" element={<StudioPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
