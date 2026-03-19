use anchor_lang::prelude::*;

declare_id!("Rep1111111111111111111111111111111111111111");

/// Three strikes within a window = temporary ban.
const STRIKE_THRESHOLD: u8 = 3;

/// Temporary ban duration: 7 days in seconds.
const TEMP_BAN_DURATION: i64 = 7 * 24 * 60 * 60;

#[program]
pub mod reputation {
    use super::*;

    /// Initialize a reputation account for a contributor.
    /// Seeds: ["reputation", contributor.key()]
    pub fn initialize(ctx: Context<Initialize>) -> Result<()> {
        let rep = &mut ctx.accounts.reputation;
        rep.contributor = ctx.accounts.contributor.key();
        rep.score = 0;
        rep.bounties_completed = 0;
        rep.bounties_failed = 0;
        rep.strikes = 0;
        rep.banned_until = 0;
        rep.bump = ctx.bumps.reputation;
        rep.created_at = Clock::get()?.unix_timestamp;
        rep.last_updated = Clock::get()?.unix_timestamp;

        emit!(ReputationInitialized {
            contributor: ctx.accounts.contributor.key(),
        });

        Ok(())
    }

    /// Increment reputation after a successful bounty completion.
    /// Authority: platform signer only.
    pub fn increment(ctx: Context<UpdateReputation>, points: u64) -> Result<()> {
        let rep = &mut ctx.accounts.reputation;
        let now = Clock::get()?.unix_timestamp;

        // Check if contributor is currently banned
        require!(
            rep.banned_until == 0 || now >= rep.banned_until,
            ReputationError::TemporarilyBanned
        );

        // Clear ban if it has expired
        if rep.banned_until > 0 && now >= rep.banned_until {
            rep.banned_until = 0;
            rep.strikes = 0;
        }

        rep.score = rep.score.checked_add(points).unwrap_or(u64::MAX);
        rep.bounties_completed = rep.bounties_completed.checked_add(1).unwrap();
        rep.last_updated = now;

        emit!(ReputationIncremented {
            contributor: rep.contributor,
            points,
            new_score: rep.score,
            tier: ReputationAccount::tier_from_score(rep.score),
        });

        Ok(())
    }

    /// Decrement reputation on a failed submission.
    /// 3 strikes = temporary ban.
    /// Authority: platform signer only.
    pub fn decrement(ctx: Context<UpdateReputation>, points: u64) -> Result<()> {
        let rep = &mut ctx.accounts.reputation;
        let now = Clock::get()?.unix_timestamp;

        rep.score = rep.score.saturating_sub(points);
        rep.bounties_failed = rep.bounties_failed.checked_add(1).unwrap();
        rep.strikes = rep.strikes.checked_add(1).unwrap_or(u8::MAX);
        rep.last_updated = now;

        // Check if strikes exceed threshold → temp ban
        if rep.strikes >= STRIKE_THRESHOLD {
            rep.banned_until = now
                .checked_add(TEMP_BAN_DURATION)
                .unwrap_or(i64::MAX);

            emit!(ContributorBanned {
                contributor: rep.contributor,
                banned_until: rep.banned_until,
                strikes: rep.strikes,
            });
        }

        emit!(ReputationDecremented {
            contributor: rep.contributor,
            points,
            new_score: rep.score,
            strikes: rep.strikes,
        });

        Ok(())
    }

    /// Reset strikes (admin override, e.g. after appeal).
    /// Authority: platform signer only.
    pub fn reset_strikes(ctx: Context<UpdateReputation>) -> Result<()> {
        let rep = &mut ctx.accounts.reputation;
        rep.strikes = 0;
        rep.banned_until = 0;
        rep.last_updated = Clock::get()?.unix_timestamp;

        emit!(StrikesReset {
            contributor: rep.contributor,
        });

        Ok(())
    }

    /// Query the reputation tier for a contributor. Read-only, no state change.
    /// Returns the tier as a logged event (clients can also deserialize directly).
    pub fn query(ctx: Context<QueryReputation>) -> Result<()> {
        let rep = &ctx.accounts.reputation;

        emit!(ReputationQueried {
            contributor: rep.contributor,
            score: rep.score,
            tier: ReputationAccount::tier_from_score(rep.score),
            bounties_completed: rep.bounties_completed,
            bounties_failed: rep.bounties_failed,
            strikes: rep.strikes,
            banned_until: rep.banned_until,
        });

        Ok(())
    }
}

// ---------------------------------------------------------------------------
// Accounts
// ---------------------------------------------------------------------------

#[derive(Accounts)]
pub struct Initialize<'info> {
    #[account(mut)]
    pub payer: Signer<'info>,

    /// The contributor whose reputation is being initialized.
    /// CHECK: Any valid public key; the PDA is keyed to this address.
    pub contributor: UncheckedAccount<'info>,

    #[account(
        init,
        payer = payer,
        space = 8 + ReputationAccount::INIT_SPACE,
        seeds = [b"reputation", contributor.key().as_ref()],
        bump,
    )]
    pub reputation: Account<'info, ReputationAccount>,

    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct UpdateReputation<'info> {
    /// Platform authority that controls reputation updates.
    pub authority: Signer<'info>,

    /// CHECK: The contributor whose reputation is updated. Validated via PDA seeds.
    pub contributor: UncheckedAccount<'info>,

    #[account(
        mut,
        seeds = [b"reputation", contributor.key().as_ref()],
        bump = reputation.bump,
        constraint = reputation.contributor == contributor.key() @ ReputationError::ContributorMismatch,
    )]
    pub reputation: Account<'info, ReputationAccount>,
}

#[derive(Accounts)]
pub struct QueryReputation<'info> {
    /// CHECK: The contributor whose reputation we query.
    pub contributor: UncheckedAccount<'info>,

    #[account(
        seeds = [b"reputation", contributor.key().as_ref()],
        bump = reputation.bump,
        constraint = reputation.contributor == contributor.key() @ ReputationError::ContributorMismatch,
    )]
    pub reputation: Account<'info, ReputationAccount>,
}

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

#[account]
#[derive(InitSpace)]
pub struct ReputationAccount {
    /// The contributor wallet this reputation belongs to.
    pub contributor: Pubkey,
    /// Cumulative reputation score.
    pub score: u64,
    /// Total bounties completed successfully.
    pub bounties_completed: u64,
    /// Total bounties failed.
    pub bounties_failed: u64,
    /// Current strike count (resets after ban expires or admin reset).
    pub strikes: u8,
    /// Unix timestamp until which the contributor is banned. 0 = not banned.
    pub banned_until: i64,
    /// PDA bump seed.
    pub bump: u8,
    /// Unix timestamp of account creation.
    pub created_at: i64,
    /// Unix timestamp of last update.
    pub last_updated: i64,
}

impl ReputationAccount {
    /// Convert a numeric score to a tier.
    /// Novice: 0-10, Builder: 11-50, Expert: 51-100, Legend: 101+
    pub fn tier_from_score(score: u64) -> ReputationTier {
        match score {
            0..=10 => ReputationTier::Novice,
            11..=50 => ReputationTier::Builder,
            51..=100 => ReputationTier::Expert,
            _ => ReputationTier::Legend,
        }
    }
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq, InitSpace)]
pub enum ReputationTier {
    Novice,
    Builder,
    Expert,
    Legend,
}

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

#[error_code]
pub enum ReputationError {
    #[msg("Contributor is temporarily banned")]
    TemporarilyBanned,
    #[msg("Contributor key does not match the reputation PDA")]
    ContributorMismatch,
}

// ---------------------------------------------------------------------------
// Events
// ---------------------------------------------------------------------------

#[event]
pub struct ReputationInitialized {
    pub contributor: Pubkey,
}

#[event]
pub struct ReputationIncremented {
    pub contributor: Pubkey,
    pub points: u64,
    pub new_score: u64,
    pub tier: ReputationTier,
}

#[event]
pub struct ReputationDecremented {
    pub contributor: Pubkey,
    pub points: u64,
    pub new_score: u64,
    pub strikes: u8,
}

#[event]
pub struct ContributorBanned {
    pub contributor: Pubkey,
    pub banned_until: i64,
    pub strikes: u8,
}

#[event]
pub struct StrikesReset {
    pub contributor: Pubkey,
}

#[event]
pub struct ReputationQueried {
    pub contributor: Pubkey,
    pub score: u64,
    pub tier: ReputationTier,
    pub bounties_completed: u64,
    pub bounties_failed: u64,
    pub strikes: u8,
    pub banned_until: i64,
}
