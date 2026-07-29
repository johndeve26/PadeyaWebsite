"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function AdminBlogTagsRedirectPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/admin/blog/taxonomies?tab=tags");
  }, [router]);
  return null;
}
