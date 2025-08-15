import HistoryViewer from '@/components/HistoryViewer';
import { AuthProvider } from '@/components/AuthContext';

export default function HistoryPage() {
  return (
    <AuthProvider>
      <HistoryViewer />
    </AuthProvider>
  );
}