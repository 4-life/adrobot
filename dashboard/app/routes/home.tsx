import { ApiStatus } from "@/components/site/ApiStatus/ApiStatus";
import { Header } from "@/components/site/Header/Header";
import { getHealth } from "@/lib/api.server";

import type { Route } from "./+types/home";

export async function loader() {
  return { health: await getHealth() };
}

export default function Home({ loaderData }: Route.ComponentProps) {
  return (
    <>
      <Header />
      <main className="mx-auto max-w-6xl p-4">
        <ApiStatus healthy={loaderData.health.healthy} />
      </main>
    </>
  );
}
