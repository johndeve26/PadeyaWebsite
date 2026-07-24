import { permanentRedirect } from "next/navigation";

type PageProps = {
  params: Promise<{ username: string }>;
};

/** Alias — prefer marketplace host shop or classic `/u/[username]/merch`. */
export default async function UserShopRedirectPage({ params }: PageProps) {
  const { username } = await params;
  const clean = decodeURIComponent(username).replace(/^@/, "");
  permanentRedirect(`/merch/hosts/${clean}`);
}
