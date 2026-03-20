export type ClaimStatus = 'unclaimed' | 'claimed' | 'in-review' | 'approved' | 'rejected';
export interface BountySubmission { id: string; author: string; prUrl: string; status: ClaimStatus; createdAt: string; }
export interface BountyDetail { id: string; title: string; description: string; tier: 'T1'|'T2'|'T3'; skills: string[]; rewardAmount: number; currency: string; deadline: string; status: 'open'|'in-progress'|'completed'; requirements: { text: string; completed: boolean }[]; submissions: BountySubmission[]; createdAt: string; projectName: string; creatorName: string; }
