// NARA — Bottom Navigation
import { useLocation, useNavigate } from "react-router-dom";

const TABS = [
  {
    path: "/",
    label: "Home",
    icon: (active) => (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
        <path
          d="M3 9.5L12 3L21 9.5V20C21 20.55 20.55 21 20 21H15V15H9V21H4C3.45 21 3 20.55 3 20V9.5Z"
          fill={active ? "#ffffff" : "none"}
          stroke={active ? "#ffffff" : "#6b6b6b"}
          strokeWidth="1.8"
          strokeLinejoin="round"
        />
      </svg>
    ),
  },
  {
    path: "/recommendations",
    label: "Discover",
    icon: (active) => (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
        <circle
          cx="12" cy="12" r="9"
          stroke={active ? "#ffffff" : "#6b6b6b"}
          strokeWidth="1.8"
        />
        <path
          d="M14.5 9.5L10 10L9.5 14.5L14 14L14.5 9.5Z"
          fill={active ? "#ffffff" : "none"}
          stroke={active ? "#ffffff" : "#6b6b6b"}
          strokeWidth="1.8"
          strokeLinejoin="round"
        />
      </svg>
    ),
  },
  {
    path: "/log",
    label: "Log",
    icon: (active) => (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
        <circle
          cx="12" cy="12" r="9"
          fill={active ? "#ffffff" : "none"}
          stroke={active ? "#ffffff" : "#6b6b6b"}
          strokeWidth="1.8"
        />
        <path
          d="M12 8V16M8 12H16"
          stroke={active ? "#000000" : "#6b6b6b"}
          strokeWidth="2"
          strokeLinecap="round"
        />
      </svg>
    ),
  },
  {
    path: "/graph",
    label: "Graph",
    icon: (active) => (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
        <path
          d="M3 17L8 12L12 15L17 9L21 12"
          stroke={active ? "#ffffff" : "#6b6b6b"}
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path
          d="M3 21H21"
          stroke={active ? "#ffffff" : "#6b6b6b"}
          strokeWidth="1.8"
          strokeLinecap="round"
        />
      </svg>
    ),
  },
  {
    path: "/chat",
    label: "Chat",
    icon: (active) => (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
        <path
          d="M20 2H4C2.9 2 2 2.9 2 4V22L6 18H20C21.1 18 22 17.1 22 16V4C22 2.9 21.1 2 20 2Z"
          fill={active ? "#ffffff" : "none"}
          stroke={active ? "#ffffff" : "#6b6b6b"}
          strokeWidth="1.8"
          strokeLinejoin="round"
        />
      </svg>
    ),
  },
];

export default function BottomNav() {
  const location = useLocation();
  const navigate = useNavigate();

  const noNav = ["/login", "/register", "/onboarding"];
  if (noNav.some((p) => location.pathname.startsWith(p))) return null;

  return (
    <nav
      style={{
        position:       "fixed",
        bottom:         0,
        left:           0,
        right:          0,
        height:         "var(--nav-height)",
        background:     "rgba(0,0,0,0.85)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        borderTop:      "1px solid var(--border)",
        display:        "flex",
        alignItems:     "center",
        justifyContent: "space-around",
        paddingBottom:  "env(safe-area-inset-bottom, 0px)",
        zIndex:         100,
      }}
    >
      {TABS.map((tab) => {
        const active = location.pathname === tab.path;
        return (
          <button
            key={tab.path}
            onClick={() => navigate(tab.path)}
            style={{
              display:        "flex",
              flexDirection:  "column",
              alignItems:     "center",
              gap:            "4px",
              padding:        "8px 16px",
              background:     "none",
              border:         "none",
              cursor:         "pointer",
              transition:     "opacity 0.2s",
              opacity:        active ? 1 : 0.6,
            }}
          >
            {tab.icon(active)}
            <span
              style={{
                fontSize:   "10px",
                fontWeight: active ? 600 : 400,
                color:      active ? "var(--text-primary)" : "var(--text-secondary)",
                letterSpacing: "0.02em",
              }}
            >
              {tab.label}
            </span>
          </button>
        );
      })}
    </nav>
  );
}