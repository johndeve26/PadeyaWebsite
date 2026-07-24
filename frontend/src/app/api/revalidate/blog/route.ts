import { revalidatePath, revalidateTag } from "next/cache";
import { NextResponse } from "next/server";

/** Bust public blog ISR after admin publish / unpublish / seed. */
export async function POST() {
  // Next 16 requires a cacheLife profile as the second argument.
  revalidateTag("blog", "max");
  revalidatePath("/blog");
  revalidatePath("/");
  revalidatePath("/sitemap.xml");
  return NextResponse.json({ revalidated: true, now: Date.now() });
}
