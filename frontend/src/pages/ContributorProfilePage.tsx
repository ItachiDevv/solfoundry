import { useContributorProfile } from '../hooks/useContributorProfile';
import { ContributorProfile } from '../components/profile';
import { mockContributorProfile } from '../data/mockProfile';

export function ContributorProfilePage() {
  const username = 'contributor42';
  const { profile, loading, error } = useContributorProfile({ username });
  const profileData = profile ?? mockContributorProfile;

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] flex items-center justify-center" data-testid="profile-loading">
        <div className="flex flex-col items-center gap-4">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-[#9945FF] border-t-transparent" />
          <p className="text-gray-400 text-sm">Loading profile...</p>
        </div>
      </div>
    );
  }

  if (error && !profile) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] flex items-center justify-center" data-testid="profile-error">
        <div className="text-center space-y-3">
          <p className="text-red-400 font-medium">Failed to load profile</p>
          <p className="text-gray-500 text-sm">{error}</p>
        </div>
      </div>
    );
  }

  return <ContributorProfile profile={profileData} />;
}
