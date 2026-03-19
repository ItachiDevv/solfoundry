import { Link } from "react-router-dom";
import { Home, ArrowLeft } from "lucide-react";

export function NotFoundPage() {
  return (
    <div className="animate-fade-in flex flex-col items-center justify-center py-20 text-center">
      <div className="text-8xl font-bold gradient-text-purple mb-4">404</div>
      <h1 className="text-2xl font-bold mb-2">Page Not Found</h1>
      <p className="text-foundry-text-muted max-w-md mb-8">
        The page you&apos;re looking for doesn&apos;t exist or has been moved.
        Maybe it got lost in the blockchain.
      </p>
      <div className="flex gap-3">
        <Link to="/" className="btn-primary inline-flex items-center gap-2">
          <Home size={16} />
          Go Home
        </Link>
        <button
          onClick={() => window.history.back()}
          className="btn-secondary inline-flex items-center gap-2"
        >
          <ArrowLeft size={16} />
          Go Back
        </button>
      </div>
    </div>
  );
}
