import { permanentRedirect } from "next/navigation";

/** Host email prefs use the same account-level notification settings. */
export default function HostNotificationSettingsRedirect() {
  permanentRedirect("/dashboard/settings/notifications");
}
