import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Create account — AimFast.Dev',
  description: 'Create your AimFast.Dev account to start tracking tech trends and market opportunities.',
  robots: { index: false, follow: false },
  alternates: {
    canonical: 'https://www.aimfast.dev/register/',
  },
};

export default function RegisterLayout({ children }: { children: React.ReactNode }) {
  return children;
}
