import { BountyDetailPage } from '../components/bounty-detail';

/**
 * SolFoundry Bounty Detail Route
 *
 * Page-level entry point wired into the app router (/bounties/:id).
 * Extracts bounty ID from URL hash and passes to BountyDetailPage.
 * In production, use useParams() from react-router-dom instead.
 *
 * @returns The routed bounty detail page
 */
export default function BountyDetailRoute() {
  const id = window.location.hash.replace('#/bounties/', '') || 'bounty-101';
  return <BountyDetailPage bountyId={id} />;
}
