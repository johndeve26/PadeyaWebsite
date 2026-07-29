"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function AdminBlogCategoriesRedirectPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/admin/blog/taxonomies?tab=categories");
  }, [router]);
  return null;
}
