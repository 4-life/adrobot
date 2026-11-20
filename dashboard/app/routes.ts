import { type RouteConfig, index, route } from "@react-router/dev/routes";

export default [
  index("routes/home.tsx"),
  // Resource routes (data only, loaded by fetchers).
  route("offers-search", "routes/offers-search.ts"),
  route("new-campaign-data", "routes/new-campaign-data.ts"),
] satisfies RouteConfig;
