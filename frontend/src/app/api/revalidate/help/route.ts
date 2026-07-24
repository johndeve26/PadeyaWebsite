import { revalidatePath, revalidateTag } from "next/cache";
import { NextResponse } from "next/server";

/** Called after help/KB publish from admin tooling (same-origin). */
export async function POST() {
  revalidateTag("help", "max");
  revalidatePath("/help");
  revalidatePath("/");
  revalidatePath("/sitemap.xml");
  return NextResponse.json({ revalidated: true, now: Date.now() });
}
