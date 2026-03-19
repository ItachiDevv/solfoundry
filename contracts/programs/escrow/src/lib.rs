use anchor_lang::prelude::*;
use anchor_spl::associated_token::AssociatedToken;
use anchor_spl::token::{self, CloseAccount, Mint, Token, TokenAccount, Transfer};

declare_id!("Esc1111111111111111111111111111111111111111");

/// Platform fee: 5% of payout is routed to the treasury.
const PLATFORM_FEE_BPS: u64 = 500; // basis points
const BPS_DENOMINATOR: u64 = 10_000;

#[program]
pub mod escrow {
    use super::*;

    /// Create a new escrow for a bounty and deposit $FNDRY tokens.
    ///
    /// Seeds: ["escrow", bounty_id.to_le_bytes()]
    pub fn initialize(ctx: Context<Initialize>, bounty_id: u64, amount: u64) -> Result<()> {
        require!(amount > 0, EscrowError::ZeroAmount);

        let escrow = &mut ctx.accounts.escrow;
        escrow.bounty_id = bounty_id;
        escrow.funder = ctx.accounts.funder.key();
        escrow.token_mint = ctx.accounts.token_mint.key();
        escrow.amount = amount;
        escrow.status = EscrowStatus::Funded;
        escrow.bump = ctx.bumps.escrow;
        escrow.created_at = Clock::get()?.unix_timestamp;

        // Transfer tokens from funder to escrow vault
        token::transfer(
            CpiContext::new(
                ctx.accounts.token_program.to_account_info(),
                Transfer {
                    from: ctx.accounts.funder_token_account.to_account_info(),
                    to: ctx.accounts.escrow_vault.to_account_info(),
                    authority: ctx.accounts.funder.to_account_info(),
                },
            ),
            amount,
        )?;

        emit!(EscrowCreated {
            bounty_id,
            funder: ctx.accounts.funder.key(),
            amount,
            token_mint: ctx.accounts.token_mint.key(),
        });

        Ok(())
    }

    /// Release escrow funds to the bounty winner.
    /// Authority: platform signer only.
    /// Splits payout: 95% to winner, 5% to treasury.
    pub fn release(ctx: Context<Release>, bounty_id: u64) -> Result<()> {
        let escrow = &ctx.accounts.escrow;
        require!(
            escrow.status == EscrowStatus::Funded,
            EscrowError::InvalidStatus
        );

        let amount = escrow.amount;
        let fee = amount
            .checked_mul(PLATFORM_FEE_BPS)
            .unwrap()
            .checked_div(BPS_DENOMINATOR)
            .unwrap();
        let payout = amount.checked_sub(fee).unwrap();

        let bounty_id_bytes = bounty_id.to_le_bytes();
        let seeds: &[&[u8]] = &[b"escrow", bounty_id_bytes.as_ref(), &[escrow.bump]];
        let signer_seeds = &[seeds];

        // Transfer payout to winner
        token::transfer(
            CpiContext::new_with_signer(
                ctx.accounts.token_program.to_account_info(),
                Transfer {
                    from: ctx.accounts.escrow_vault.to_account_info(),
                    to: ctx.accounts.winner_token_account.to_account_info(),
                    authority: ctx.accounts.escrow.to_account_info(),
                },
                signer_seeds,
            ),
            payout,
        )?;

        // Transfer fee to treasury
        if fee > 0 {
            token::transfer(
                CpiContext::new_with_signer(
                    ctx.accounts.token_program.to_account_info(),
                    Transfer {
                        from: ctx.accounts.escrow_vault.to_account_info(),
                        to: ctx.accounts.treasury_token_account.to_account_info(),
                        authority: ctx.accounts.escrow.to_account_info(),
                    },
                    signer_seeds,
                ),
                fee,
            )?;
        }

        // Update escrow state
        let escrow = &mut ctx.accounts.escrow;
        escrow.status = EscrowStatus::Released;

        emit!(EscrowReleased {
            bounty_id,
            winner: ctx.accounts.winner.key(),
            payout,
            fee,
        });

        Ok(())
    }

    /// Refund escrow to the original funder (bounty cancelled).
    /// Authority: platform signer or original funder.
    pub fn refund(ctx: Context<Refund>, bounty_id: u64) -> Result<()> {
        let escrow = &ctx.accounts.escrow;
        require!(
            escrow.status == EscrowStatus::Funded,
            EscrowError::InvalidStatus
        );

        let amount = escrow.amount;
        let bounty_id_bytes = bounty_id.to_le_bytes();
        let seeds: &[&[u8]] = &[b"escrow", bounty_id_bytes.as_ref(), &[escrow.bump]];
        let signer_seeds = &[seeds];

        // Transfer all tokens back to funder
        token::transfer(
            CpiContext::new_with_signer(
                ctx.accounts.token_program.to_account_info(),
                Transfer {
                    from: ctx.accounts.escrow_vault.to_account_info(),
                    to: ctx.accounts.funder_token_account.to_account_info(),
                    authority: ctx.accounts.escrow.to_account_info(),
                },
                signer_seeds,
            ),
            amount,
        )?;

        // Update escrow state
        let escrow = &mut ctx.accounts.escrow;
        escrow.status = EscrowStatus::Refunded;

        emit!(EscrowRefunded {
            bounty_id,
            funder: ctx.accounts.funder.key(),
            amount,
        });

        Ok(())
    }

    /// Close the escrow account after payout/refund, reclaiming rent.
    /// Only callable when escrow is Released or Refunded.
    pub fn close(ctx: Context<Close>, bounty_id: u64) -> Result<()> {
        let escrow = &ctx.accounts.escrow;
        require!(
            escrow.status == EscrowStatus::Released || escrow.status == EscrowStatus::Refunded,
            EscrowError::InvalidStatus
        );

        // Close the vault token account, returning rent to funder
        let bounty_id_bytes = bounty_id.to_le_bytes();
        let seeds: &[&[u8]] = &[b"escrow", bounty_id_bytes.as_ref(), &[escrow.bump]];
        let signer_seeds = &[seeds];

        token::close_account(CpiContext::new_with_signer(
            ctx.accounts.token_program.to_account_info(),
            CloseAccount {
                account: ctx.accounts.escrow_vault.to_account_info(),
                destination: ctx.accounts.funder.to_account_info(),
                authority: ctx.accounts.escrow.to_account_info(),
            },
            signer_seeds,
        ))?;

        emit!(EscrowClosed {
            bounty_id,
            funder: ctx.accounts.funder.key(),
        });

        Ok(())
    }
}

// ---------------------------------------------------------------------------
// Accounts
// ---------------------------------------------------------------------------

#[derive(Accounts)]
#[instruction(bounty_id: u64, amount: u64)]
pub struct Initialize<'info> {
    #[account(mut)]
    pub funder: Signer<'info>,

    #[account(
        init,
        payer = funder,
        space = 8 + Escrow::INIT_SPACE,
        seeds = [b"escrow", bounty_id.to_le_bytes().as_ref()],
        bump,
    )]
    pub escrow: Account<'info, Escrow>,

    pub token_mint: Account<'info, Mint>,

    #[account(
        mut,
        associated_token::mint = token_mint,
        associated_token::authority = funder,
    )]
    pub funder_token_account: Account<'info, TokenAccount>,

    #[account(
        init,
        payer = funder,
        token::mint = token_mint,
        token::authority = escrow,
        seeds = [b"escrow_vault", bounty_id.to_le_bytes().as_ref()],
        bump,
    )]
    pub escrow_vault: Account<'info, TokenAccount>,

    pub system_program: Program<'info, System>,
    pub token_program: Program<'info, Token>,
    pub rent: Sysvar<'info, Rent>,
}

#[derive(Accounts)]
#[instruction(bounty_id: u64)]
pub struct Release<'info> {
    /// Platform authority that signs off on bounty completion.
    pub authority: Signer<'info>,

    #[account(
        mut,
        seeds = [b"escrow", bounty_id.to_le_bytes().as_ref()],
        bump = escrow.bump,
        constraint = escrow.bounty_id == bounty_id @ EscrowError::BountyMismatch,
    )]
    pub escrow: Account<'info, Escrow>,

    #[account(
        mut,
        seeds = [b"escrow_vault", bounty_id.to_le_bytes().as_ref()],
        bump,
        token::mint = escrow.token_mint,
        token::authority = escrow,
    )]
    pub escrow_vault: Account<'info, TokenAccount>,

    /// CHECK: Winner wallet, validated by token account constraint below.
    pub winner: UncheckedAccount<'info>,

    #[account(
        init_if_needed,
        payer = authority,
        associated_token::mint = token_mint,
        associated_token::authority = winner,
    )]
    pub winner_token_account: Account<'info, TokenAccount>,

    /// CHECK: Treasury wallet, validated by token account constraint below.
    pub treasury: UncheckedAccount<'info>,

    #[account(
        init_if_needed,
        payer = authority,
        associated_token::mint = token_mint,
        associated_token::authority = treasury,
    )]
    pub treasury_token_account: Account<'info, TokenAccount>,

    pub token_mint: Account<'info, Mint>,

    pub system_program: Program<'info, System>,
    pub token_program: Program<'info, Token>,
    pub associated_token_program: Program<'info, AssociatedToken>,
}

#[derive(Accounts)]
#[instruction(bounty_id: u64)]
pub struct Refund<'info> {
    /// Either platform authority or the original funder.
    pub authority: Signer<'info>,

    /// The original funder who receives the refund.
    /// CHECK: Validated against escrow.funder.
    #[account(
        mut,
        constraint = funder.key() == escrow.funder @ EscrowError::UnauthorizedFunder,
    )]
    pub funder: UncheckedAccount<'info>,

    #[account(
        mut,
        seeds = [b"escrow", bounty_id.to_le_bytes().as_ref()],
        bump = escrow.bump,
        constraint = escrow.bounty_id == bounty_id @ EscrowError::BountyMismatch,
    )]
    pub escrow: Account<'info, Escrow>,

    #[account(
        mut,
        seeds = [b"escrow_vault", bounty_id.to_le_bytes().as_ref()],
        bump,
        token::mint = escrow.token_mint,
        token::authority = escrow,
    )]
    pub escrow_vault: Account<'info, TokenAccount>,

    #[account(
        mut,
        associated_token::mint = token_mint,
        associated_token::authority = funder,
    )]
    pub funder_token_account: Account<'info, TokenAccount>,

    pub token_mint: Account<'info, Mint>,
    pub token_program: Program<'info, Token>,
}

#[derive(Accounts)]
#[instruction(bounty_id: u64)]
pub struct Close<'info> {
    /// Platform authority or original funder.
    pub authority: Signer<'info>,

    /// The original funder who gets rent back.
    /// CHECK: Validated against escrow.funder.
    #[account(
        mut,
        constraint = funder.key() == escrow.funder @ EscrowError::UnauthorizedFunder,
    )]
    pub funder: UncheckedAccount<'info>,

    #[account(
        mut,
        seeds = [b"escrow", bounty_id.to_le_bytes().as_ref()],
        bump = escrow.bump,
        constraint = escrow.bounty_id == bounty_id @ EscrowError::BountyMismatch,
        close = funder,
    )]
    pub escrow: Account<'info, Escrow>,

    #[account(
        mut,
        seeds = [b"escrow_vault", bounty_id.to_le_bytes().as_ref()],
        bump,
        token::mint = token_mint,
        token::authority = escrow,
    )]
    pub escrow_vault: Account<'info, TokenAccount>,

    pub token_mint: Account<'info, Mint>,
    pub token_program: Program<'info, Token>,
}

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

#[account]
#[derive(InitSpace)]
pub struct Escrow {
    /// Unique bounty identifier.
    pub bounty_id: u64,
    /// Wallet that funded the escrow.
    pub funder: Pubkey,
    /// SPL token mint ($FNDRY).
    pub token_mint: Pubkey,
    /// Escrowed amount in token base units.
    pub amount: u64,
    /// Current status of the escrow.
    pub status: EscrowStatus,
    /// PDA bump seed.
    pub bump: u8,
    /// Unix timestamp of creation.
    pub created_at: i64,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq, InitSpace)]
pub enum EscrowStatus {
    Funded,
    Released,
    Refunded,
}

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

#[error_code]
pub enum EscrowError {
    #[msg("Amount must be greater than zero")]
    ZeroAmount,
    #[msg("Escrow is not in the correct status for this operation")]
    InvalidStatus,
    #[msg("Bounty ID does not match the escrow")]
    BountyMismatch,
    #[msg("Signer is not the original funder")]
    UnauthorizedFunder,
}

// ---------------------------------------------------------------------------
// Events
// ---------------------------------------------------------------------------

#[event]
pub struct EscrowCreated {
    pub bounty_id: u64,
    pub funder: Pubkey,
    pub amount: u64,
    pub token_mint: Pubkey,
}

#[event]
pub struct EscrowReleased {
    pub bounty_id: u64,
    pub winner: Pubkey,
    pub payout: u64,
    pub fee: u64,
}

#[event]
pub struct EscrowRefunded {
    pub bounty_id: u64,
    pub funder: Pubkey,
    pub amount: u64,
}

#[event]
pub struct EscrowClosed {
    pub bounty_id: u64,
    pub funder: Pubkey,
}
