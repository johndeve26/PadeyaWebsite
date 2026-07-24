import { redirect } from "next/navigation";

type Props = { params: Promise<{ id: string }> };

export default async function CmsBlogEditRedirect({ params }: Props) {
  const { id } = await params;
  redirect(`/admin/blog/${id}/edit`);
}
