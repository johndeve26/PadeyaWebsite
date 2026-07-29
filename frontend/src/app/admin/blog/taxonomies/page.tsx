"use client";

import { Suspense } from "react";

import { BlogTaxonomiesAdminPage } from "@/components/blog/admin/BlogTaxonomiesAdminPage";
import { SkeletonLoader } from "@/components/ui";

export default function AdminBlogTaxonomiesPage() {
  return (
    <Suspense fallback={<SkeletonLoader lines={6} />}>
      <BlogTaxonomiesAdminPage />
    </Suspense>
  );
}
