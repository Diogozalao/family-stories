import { useEffect, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { useLogin } from "../lib/hooks";
import { useAuthStore } from "../store/auth";
import { extractErrorMessage } from "../lib/api";

import LandingFooter from "../components/landing/LandingFooter";
import LandingHeader from "../components/landing/LandingHeader";
import LandingHero   from "../components/landing/LandingHero";
import PipelineDemo  from "../components/landing/PipelineDemo";
import {
  LandingPlatforms, LandingStats, LandingTrustBar,
} from "../components/landing/LandingPlatforms";
import {
  CTASection, FeaturesSection, HowItWorksSection, PrivacySection,
} from "../components/landing/LandingSections";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/**
 * Public landing + sign-in page.
 *
 * Layout follows a Cloudflare-style flow: hero (with embedded login),
 * trust bar, platform tiles, big numbers, deep-dive sections, final CTA,
 * footer. The actual sign-in form lives inside :file:`LandingHero` so
 * the visitor never has to scroll to authenticate.
 */
export default function LoginPage() {
  const { t } = useTranslation();
  const token = useAuthStore((s) => s.token);
  const navigate = useNavigate();
  const location = useLocation() as { hash?: string; state?: { from?: { pathname?: string } } };
  const login = useLogin();

  const [email,    setEmail]    = useState("");
  const [password, setPassword] = useState("");
  const [showPw,   setShowPw]   = useState(false);

  // Reset the form when the page becomes visible again — guards against
  // browsers re-populating the password field after a back-navigation.
  useEffect(() => {
    const reset = () => {
      if (document.visibilityState === "visible") {
        setEmail("");
        setPassword("");
      }
    };
    document.addEventListener("visibilitychange", reset);
    window.addEventListener("pageshow", reset);
    return () => {
      document.removeEventListener("visibilitychange", reset);
      window.removeEventListener("pageshow", reset);
    };
  }, []);

  // Smooth-scroll to the section named in the URL hash (#platforms / #how /
  // #privacy / #demo). The nav links point at /login#section, so arriving
  // from /about — or clicking again on /login — both land on the section.
  // Offset by the fixed header height so the title isn't tucked under it.
  useEffect(() => {
    const id = location.hash?.replace("#", "");
    if (!id) return;
    const tmr = window.setTimeout(() => {
      const el = document.getElementById(id);
      if (el) {
        const y = el.getBoundingClientRect().top + window.scrollY - 72;
        window.scrollTo({ top: y, behavior: "smooth" });
      }
    }, 60);
    return () => window.clearTimeout(tmr);
  }, [location.hash]);

  if (token) return <Navigate to="/" replace />;

  const emailInvalid = email.length > 0 && !EMAIL_RE.test(email);
  const canSubmit    = EMAIL_RE.test(email) && password.length > 0;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    login.mutate(
      { username: email, password },
      {
        onSuccess: () => {
          toast.success(t("common.success"));
          navigate(location.state?.from?.pathname ?? "/", { replace: true });
        },
        onError: (err) => toast.error(extractErrorMessage(err, t("auth.invalid"))),
      },
    );
  };

  return (
    <div className="min-h-screen bg-stone-50 dark:bg-stone-950">
      <LandingHeader />

      <LandingHero
        email={email}             setEmail={setEmail}
        password={password}       setPassword={setPassword}
        showPw={showPw}           setShowPw={setShowPw}
        emailInvalid={emailInvalid}
        canSubmit={canSubmit}
        pending={login.isPending}
        onSubmit={handleSubmit}
      />

      <PipelineDemo />
      <LandingTrustBar />
      <LandingPlatforms />
      <LandingStats />

      <FeaturesSection />
      <HowItWorksSection />
      <PrivacySection />
      <CTASection />

      <LandingFooter />
    </div>
  );
}
