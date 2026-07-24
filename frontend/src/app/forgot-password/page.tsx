import type { Metadata } from "next";

import { ForgotPasswordForm } from "@/components/auth/ForgotPasswordForm";
import { privateAreaMetadata } from "@/lib/seo/noindex";

export const metadata: Metadata = privateAreaMetadata("Forgot password");

export default function ForgotPasswordPage() {
  return <ForgotPasswordForm />;
}
