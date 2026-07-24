import { redirect } from "next/navigation";

type Props = { params: Promise<{ username: string }> };

/** Alias → canonical Fan Passport page. */
export default async function PassportAliasPage({ params }: Props) {
  const { username } = await params;
  redirect(`/f/${encodeURIComponent(username)}`);
}
