import { ApiError } from "@/lib/api";

export function registerErrorMessage(err: ApiError): string {
  const detail = err.detail.trim();
  const lower = detail.toLowerCase();

  if (err.status === 409) {
    if (lower.includes("email")) {
      return "That email is already registered. Log in or use a different email.";
    }
    if (lower.includes("username")) {
      return "That username is already taken. Choose another one.";
    }
  }

  if (err.status === 422 && detail) {
    return detail;
  }

  if (detail && err.status >= 400 && err.status < 500) {
    return detail;
  }

  return "We could not create your account. Check your details and try again.";
}
