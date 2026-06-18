import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useUserStore } from '../store/useUserStore';

type ProtectedRouteProps = {
  children: ReactNode;
};

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const isAuthenticated = useUserStore((state) => state.isAuthenticated);
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return <>{children}</>;
}
