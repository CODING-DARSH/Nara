// NARA — App Router
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import "./styles/globals.css";

import { AppProvider }     from "./context/AppContext";
import BottomNav           from "./components/BottomNav";
import Login               from "./pages/Login";
import Register            from "./pages/Register";
import Onboarding          from "./pages/Onboarding";
import Home                from "./pages/Home";
import Recommendations     from "./pages/Recommendations";
import RestaurantDetail    from "./pages/RestaurantDetail";
import LogMeal             from "./pages/LogMeal";
import FoodGraph           from "./pages/FoodGraph";
import Chat                from "./pages/Chat";
import Profile             from "./pages/Profile";

function RequireAuth({ children }) {
  const token = localStorage.getItem("nara_token");
  if (!token) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login"    element={<Login />} />
          <Route path="/register" element={<Register />} />

          <Route path="/onboarding" element={<RequireAuth><Onboarding /></RequireAuth>} />
          <Route path="/"           element={<RequireAuth><Home /></RequireAuth>} />
          <Route path="/recommendations" element={<RequireAuth><Recommendations /></RequireAuth>} />

          {/* Restaurant detail — tap a restaurant card → ranked real menu */}
          <Route path="/restaurant/:restaurantId" element={<RequireAuth><RestaurantDetail /></RequireAuth>} />

          <Route path="/log"     element={<RequireAuth><LogMeal /></RequireAuth>} />
          <Route path="/graph"   element={<RequireAuth><FoodGraph /></RequireAuth>} />
          <Route path="/chat"    element={<RequireAuth><Chat /></RequireAuth>} />
          <Route path="/profile" element={<RequireAuth><Profile /></RequireAuth>} />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>

        <BottomNav />
      </BrowserRouter>
    </AppProvider>
  );
}