import { HostOnboardingForm } from "@/components/host/onboarding/HostOnboardingForm";
import { HostOnboardingRedirectGuard } from "@/components/host/onboarding/HostOnboardingRedirectGuard";

/** First-time become-a-host flow; existing hosts are sent to `/host/roadmap` (302 client guard). */
export default function HostOnboardingPage() {
  return (
    <HostOnboardingRedirectGuard>
      <HostOnboardingForm />
    </HostOnboardingRedirectGuard>
  );
}
