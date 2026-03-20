/** SolFoundry Bounty Detail Types -- frontend-only, no backend claiming logic. */

/** Display-only submission status. */
export type SubmissionStatus = 'pending' | 'in-review' | 'approved' | 'rejected';

/** A single PR submission in the submissions list. */
export interface BountySubmission { id: string; author: string; prUrl: string; status: SubmissionStatus; createdAt: string; }

/** Bounty requirement checklist item. */
export interface BountyRequirement { text: string; completed: boolean; }

/** Full bounty detail object. */
export interface BountyDetail {
  id: string; title: string; description: string;
  tier: 'T1' | 'T2' | 'T3'; skills: string[];
  rewardAmount: number; currency: string; deadline: string;
  status: 'open' | 'in-progress' | 'completed';
  requirements: BountyRequirement[]; submissions: BountySubmission[];
  createdAt: string; projectName: string; creatorName: string;
}
