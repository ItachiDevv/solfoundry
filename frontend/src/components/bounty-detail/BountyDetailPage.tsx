import { Sidebar } from '../layout/Sidebar';
import { useState } from 'react';
import { useBountyDetail } from '../../hooks/useBountyDetail';
import { BountyHeader } from './BountyHeader';
import { RequirementsChecklist } from './RequirementsChecklist';
import { SubmissionsList } from './SubmissionsList';
export function BountyDetailPage({ bountyId }: { bountyId: string }) {
  const [collapsed, setCollapsed] = useState(false);
  const { bounty, loading, error } = useBountyDetail(bountyId);
  return (
    <div className="flex min-h-screen bg-surface dark">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(p => !p)} />
      <main className={'flex-1 p-6 ' + (collapsed ? 'ml-16' : 'ml-64')} role="main" data-testid="bounty-detail">
        {loading && <p className="text-gray-500">Loading...</p>}
        {error && <p className="text-red-400" data-testid="error">{error}</p>}
        {bounty && <>
          <BountyHeader bounty={bounty} />
          <div className="mt-6 prose prose-invert max-w-none" data-testid="description"><p className="text-sm text-gray-300 whitespace-pre-wrap">{bounty.description}</p></div>
          <div className="mt-6 grid gap-6 lg:grid-cols-2"><RequirementsChecklist requirements={bounty.requirements} /><SubmissionsList submissions={bounty.submissions} /></div>
          <div className="mt-4 flex flex-wrap gap-1">{bounty.skills.map(s => <span key={s} className="rounded-md bg-surface-200 px-2 py-0.5 text-xs text-gray-400">{s}</span>)}</div>
        </>}
      </main>
    </div>);
}
