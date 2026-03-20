import { BountyDetailPage } from '../components/bounty-detail';
/** Route: /bounties/:id - renders BountyDetailPage with id from URL hash */
export default function BountyDetailRoute() {
  const id = window.location.hash.replace('#/bounties/', '') || 'bounty-101';
  return <BountyDetailPage bountyId={id} />;
}
