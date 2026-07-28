import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Sign in — AimFast.Dev',
  description: 'Sign in to your AimFast.Dev account to access your dashboard and tracked trends.',
  robots: { index: false, follow: false },
  alternates: {
    canonical: 'https://www.aimfast.dev/login/',
  },
};

export default function LoginLayout({ children }: { children: React.ReactNode }) {
  return children;
}
