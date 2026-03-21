/** Route entry point for /profile/:username — fetches contributor data from API. */
import { useParams } from 'react-router-dom';
import { useContributor } from '../hooks/useContributor';
import ContributorProfile from '../components/ContributorProfile';
import { TableSkeleton } from '../components/LoadingSkeleton';

export default function ContributorProfilePage() {
  const { username } = useParams<{ username: string }>();
  const { contributor, loading, error } = useContributor(username ?? '');

  if (loading) return <div className="p-6"><TableSkeleton rows={3} /></div>;
  if (error && !contributor) return <div className="p-8 text-center text-red-400" role="alert">Error: {error}</div>;

  return (
    <ContributorProfile
      username={contributor?.username ?? username ?? ''}
      avatarUrl={contributor?.avatarUrl}
      walletAddress={contributor?.walletAddress}
      totalEarned={contributor?.totalEarned}
      bountiesCompleted={contributor?.bountiesCompleted}
      reputationScore={contributor?.reputationScore}
    />
  );
}
