import { lazy } from "react";
import { type RouteObject } from "react-router-dom";
import { Layout } from "./components/Layout";
import { ProtectedRoute } from "./components/ProtectedRoute";

// Lazy-load pages for code splitting
const HomePage = lazy(() =>
  import("./pages/HomePage").then((m) => ({ default: m.HomePage })),
);
const BountiesPage = lazy(() =>
  import("./pages/BountiesPage").then((m) => ({ default: m.BountiesPage })),
);
const BountyDetailPage = lazy(() =>
  import("./pages/BountyDetailPage").then((m) => ({
    default: m.BountyDetailPage,
  })),
);
const CreateBountyPage = lazy(() =>
  import("./pages/CreateBountyPage").then((m) => ({
    default: m.CreateBountyPage,
  })),
);
const LeaderboardPage = lazy(() =>
  import("./pages/LeaderboardPage").then((m) => ({
    default: m.LeaderboardPage,
  })),
);
const TokenomicsPage = lazy(() =>
  import("./pages/TokenomicsPage").then((m) => ({
    default: m.TokenomicsPage,
  })),
);
const AgentsPage = lazy(() =>
  import("./pages/AgentsPage").then((m) => ({ default: m.AgentsPage })),
);
const DashboardPage = lazy(() =>
  import("./pages/DashboardPage").then((m) => ({ default: m.DashboardPage })),
);
const ProfilePage = lazy(() =>
  import("./pages/ProfilePage").then((m) => ({ default: m.ProfilePage })),
);
const NotFoundPage = lazy(() =>
  import("./pages/NotFoundPage").then((m) => ({ default: m.NotFoundPage })),
);

export const routes: RouteObject[] = [
  {
    element: <Layout />,
    children: [
      // Public routes
      { index: true, element: <HomePage /> },
      { path: "bounties", element: <BountiesPage /> },
      { path: "bounties/:id", element: <BountyDetailPage /> },
      { path: "leaderboard", element: <LeaderboardPage /> },
      { path: "tokenomics", element: <TokenomicsPage /> },
      { path: "agents", element: <AgentsPage /> },

      // Protected routes
      {
        path: "bounties/create",
        element: (
          <ProtectedRoute>
            <CreateBountyPage />
          </ProtectedRoute>
        ),
      },
      {
        path: "dashboard",
        element: (
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        ),
      },
      {
        path: "profile",
        element: (
          <ProtectedRoute>
            <ProfilePage />
          </ProtectedRoute>
        ),
      },

      // 404
      { path: "*", element: <NotFoundPage /> },
    ],
  },
];
