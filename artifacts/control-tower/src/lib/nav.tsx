// Minimal Next.js navigation shims backed by wouter.
import React from "react";
import { useLocation, useParams as useWouterParams, useSearch, Link as WLink } from "wouter";

export function useRouter() {
  const [, navigate] = useLocation();
  return React.useMemo(
    () => ({
      push: (to: string) => navigate(to),
      replace: (to: string) => navigate(to, { replace: true }),
      back: () => window.history.back(),
    }),
    [navigate],
  );
}

export function usePathname(): string {
  const [path] = useLocation();
  return path;
}

export function useSearchParams(): URLSearchParams {
  const search = useSearch();
  return React.useMemo(() => new URLSearchParams(search), [search]);
}

export function useParams<T extends Record<string, string | undefined> = Record<string, string | undefined>>(): T {
  // @ts-ignore
  return useWouterParams() as T;
}

export function Link({
  href,
  children,
  ...rest
}: React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) {
  return (
    <WLink href={href} {...rest}>
      {children}
    </WLink>
  );
}

export default Link;
