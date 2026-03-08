import { BrowserRouter, Routes, Route } from "react-router-dom";
import HomePage from "./pages/HomePage";
import AnalysisPage from "./pages/AnalysisPage";
import Chatbot from "./Chatbot";
import PaperPage from "./pages/PaperPage";
import AboutPage from "./pages/AboutPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/analysis" element={<AnalysisPage />} />
        <Route path="/paper" element={<PaperPage />} />
        <Route path="/about" element={<AboutPage />} />
      </Routes>
      <Chatbot />
    </BrowserRouter>
  );
}
