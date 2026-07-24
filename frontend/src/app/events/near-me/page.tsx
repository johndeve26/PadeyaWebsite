import { redirect } from "next/navigation";

export const revalidate = 90;

/** Deep link into marketplace nearby mode. */
export default function NearMePage() {
  redirect("/events?near=1");
}
