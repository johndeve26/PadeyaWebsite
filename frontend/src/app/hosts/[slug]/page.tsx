import { redirect } from "next/navigation";

type Props = { params: Promise<{ slug: string }> };

/** Alias → canonical host Legacy page. */
export default async function HostSlugAliasPage({ params }: Props) {
  const { slug } = await params;
  redirect(`/u/${encodeURIComponent(slug)}`);
}
