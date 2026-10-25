import { useNavigate } from 'react-router-dom';
import { FileQuestion } from 'lucide-react';
import { EmptyState } from '../components/EmptyState';

export default function NotFoundPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-[60vh] flex items-center justify-center p-6">
      <EmptyState
        icon={FileQuestion}
        title="404 - Statutory Route Not Found"
        description="The requested AICTE scrutiny or verification workspace docket does not exist or has been moved."
        actionText="Return to Overview"
        onAction={() => navigate('/officer/overview')}
        secondaryActionText="Go to Login"
        onSecondaryAction={() => navigate('/login')}
      />
    </div>
  );
}
