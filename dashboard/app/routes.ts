import { type RouteConfig, index, route } from "@react-router/dev/routes";

export default [
  index("routes/home.tsx"), // the campaigns table
  route("campaigns/:id", "routes/campaign.tsx"), // one campaign, opened by id
  // Resource routes (data only, used by fetchers).
  route("campaign-action", "routes/campaign-action.ts"),
  route("offers-search", "routes/offers-search.ts"),
  route("new-campaign-data", "routes/new-campaign-data.ts"),
] satisfies RouteConfig;
