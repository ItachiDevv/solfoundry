use anchor_lang::prelude::*;
use anchor_spl::associated_token::AssociatedToken;
use anchor_spl::token::{self, Mint, Token, TokenAccount, Transfer};

declare_id!("Tre1111111111111111111111111111111111111111");

#[program]
pub mod treasury {
    use super::*;

    /// Initialize the treasury PDA and its token vault.
    /// Seeds: ["treasury"]
    /// Typically called once at deployment.
    pub fn initialize(ctx: Context<Initialize>) -> Result<()> {
        let treasury = &mut ctx.accounts.treasury;
        treasury.admin = ctx.accounts.admin.key();
        treasury.token_mint = ctx.accounts.token_mint.key();
        treasury.total_fees_collected = 0;
        treasury.total_buybacks_executed = 0;
        treasury.total_buyback_amount = 0;
        treasury.bump = ctx.bumps.treasury;
        treasury.vault_bump = ctx.bumps.treasury_vault;
        treasury.created_at = Clock::get()?.unix_timestamp;

        emit!(TreasuryInitialized {
            admin: ctx.accounts.admin.key(),
            token_mint: ctx.accounts.token_mint.key(),
        });

        Ok(())
    }

    /// Deposit platform fees into the treasury vault.
    /// Called by the escrow program or by the platform backend after a release.
    pub fn deposit_fees(ctx: Context<DepositFees>, amount: u64) -> Result<()> {
        require!(amount > 0, TreasuryError::ZeroAmount);

        // Transfer tokens into treasury vault
        token::transfer(
            CpiContext::new(
                ctx.accounts.token_program.to_account_info(),
                Transfer {
                    from: ctx.accounts.depositor_token_account.to_account_info(),
                    to: ctx.accounts.treasury_vault.to_account_info(),
                    authority: ctx.accounts.depositor.to_account_info(),
                },
            ),
            amount,
        )?;

        let treasury = &mut ctx.accounts.treasury;
        treasury.total_fees_collected = treasury
            .total_fees_collected
            .checked_add(amount)
            .unwrap_or(u64::MAX);

        emit!(FeesDeposited {
            depositor: ctx.accounts.depositor.key(),
            amount,
            total_fees_collected: treasury.total_fees_collected,
        });

        Ok(())
    }

    /// Withdraw tokens from treasury for buybacks.
    /// Authority: admin (will be multisig in production).
    pub fn withdraw_for_buyback(ctx: Context<WithdrawBuyback>, amount: u64) -> Result<()> {
        require!(amount > 0, TreasuryError::ZeroAmount);

        // Verify sufficient balance
        let vault_balance = ctx.accounts.treasury_vault.amount;
        require!(vault_balance >= amount, TreasuryError::InsufficientBalance);

        let seeds: &[&[u8]] = &[b"treasury", &[ctx.accounts.treasury.bump]];
        let signer_seeds = &[seeds];

        // Transfer tokens out of treasury vault to destination
        token::transfer(
            CpiContext::new_with_signer(
                ctx.accounts.token_program.to_account_info(),
                Transfer {
                    from: ctx.accounts.treasury_vault.to_account_info(),
                    to: ctx.accounts.destination_token_account.to_account_info(),
                    authority: ctx.accounts.treasury.to_account_info(),
                },
                signer_seeds,
            ),
            amount,
        )?;

        let treasury = &mut ctx.accounts.treasury;
        treasury.total_buybacks_executed = treasury
            .total_buybacks_executed
            .checked_add(1)
            .unwrap_or(u64::MAX);
        treasury.total_buyback_amount = treasury
            .total_buyback_amount
            .checked_add(amount)
            .unwrap_or(u64::MAX);

        emit!(BuybackExecuted {
            admin: ctx.accounts.admin.key(),
            amount,
            total_buybacks: treasury.total_buybacks_executed,
            total_buyback_amount: treasury.total_buyback_amount,
        });

        Ok(())
    }

    /// Transfer admin authority to a new address (e.g., multisig).
    pub fn transfer_admin(ctx: Context<TransferAdmin>, new_admin: Pubkey) -> Result<()> {
        let old_admin = ctx.accounts.treasury.admin;
        ctx.accounts.treasury.admin = new_admin;

        emit!(AdminTransferred {
            old_admin,
            new_admin,
        });

        Ok(())
    }

    /// Read-only query that emits treasury stats as an event.
    pub fn query_stats(ctx: Context<QueryStats>) -> Result<()> {
        let treasury = &ctx.accounts.treasury;
        let vault_balance = ctx.accounts.treasury_vault.amount;

        emit!(TreasuryStats {
            admin: treasury.admin,
            token_mint: treasury.token_mint,
            vault_balance,
            total_fees_collected: treasury.total_fees_collected,
            total_buybacks_executed: treasury.total_buybacks_executed,
            total_buyback_amount: treasury.total_buyback_amount,
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
    pub admin: Signer<'info>,

    pub token_mint: Account<'info, Mint>,

    #[account(
        init,
        payer = admin,
        space = 8 + TreasuryAccount::INIT_SPACE,
        seeds = [b"treasury"],
        bump,
    )]
    pub treasury: Account<'info, TreasuryAccount>,

    #[account(
        init,
        payer = admin,
        token::mint = token_mint,
        token::authority = treasury,
        seeds = [b"treasury_vault"],
        bump,
    )]
    pub treasury_vault: Account<'info, TokenAccount>,

    pub system_program: Program<'info, System>,
    pub token_program: Program<'info, Token>,
    pub rent: Sysvar<'info, Rent>,
}

#[derive(Accounts)]
pub struct DepositFees<'info> {
    #[account(mut)]
    pub depositor: Signer<'info>,

    #[account(
        mut,
        seeds = [b"treasury"],
        bump = treasury.bump,
    )]
    pub treasury: Account<'info, TreasuryAccount>,

    #[account(
        mut,
        seeds = [b"treasury_vault"],
        bump = treasury.vault_bump,
        token::mint = treasury.token_mint,
        token::authority = treasury,
    )]
    pub treasury_vault: Account<'info, TokenAccount>,

    #[account(
        mut,
        token::mint = treasury.token_mint,
        token::authority = depositor,
    )]
    pub depositor_token_account: Account<'info, TokenAccount>,

    pub token_program: Program<'info, Token>,
}

#[derive(Accounts)]
pub struct WithdrawBuyback<'info> {
    #[account(
        constraint = admin.key() == treasury.admin @ TreasuryError::Unauthorized,
    )]
    pub admin: Signer<'info>,

    #[account(
        mut,
        seeds = [b"treasury"],
        bump = treasury.bump,
    )]
    pub treasury: Account<'info, TreasuryAccount>,

    #[account(
        mut,
        seeds = [b"treasury_vault"],
        bump = treasury.vault_bump,
        token::mint = treasury.token_mint,
        token::authority = treasury,
    )]
    pub treasury_vault: Account<'info, TokenAccount>,

    #[account(
        mut,
        token::mint = treasury.token_mint,
    )]
    pub destination_token_account: Account<'info, TokenAccount>,

    pub token_program: Program<'info, Token>,
}

#[derive(Accounts)]
pub struct TransferAdmin<'info> {
    #[account(
        constraint = admin.key() == treasury.admin @ TreasuryError::Unauthorized,
    )]
    pub admin: Signer<'info>,

    #[account(
        mut,
        seeds = [b"treasury"],
        bump = treasury.bump,
    )]
    pub treasury: Account<'info, TreasuryAccount>,
}

#[derive(Accounts)]
pub struct QueryStats<'info> {
    #[account(
        seeds = [b"treasury"],
        bump = treasury.bump,
    )]
    pub treasury: Account<'info, TreasuryAccount>,

    #[account(
        seeds = [b"treasury_vault"],
        bump = treasury.vault_bump,
        token::mint = treasury.token_mint,
        token::authority = treasury,
    )]
    pub treasury_vault: Account<'info, TokenAccount>,
}

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

#[account]
#[derive(InitSpace)]
pub struct TreasuryAccount {
    /// Admin authority (can be multisig in production).
    pub admin: Pubkey,
    /// The SPL token mint for $FNDRY.
    pub token_mint: Pubkey,
    /// Running total of all fees collected (in token base units).
    pub total_fees_collected: u64,
    /// Number of buyback transactions executed.
    pub total_buybacks_executed: u64,
    /// Total amount of tokens used in buybacks.
    pub total_buyback_amount: u64,
    /// PDA bump seed for treasury.
    pub bump: u8,
    /// PDA bump seed for vault.
    pub vault_bump: u8,
    /// Unix timestamp of creation.
    pub created_at: i64,
}

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

#[error_code]
pub enum TreasuryError {
    #[msg("Amount must be greater than zero")]
    ZeroAmount,
    #[msg("Insufficient balance in treasury vault")]
    InsufficientBalance,
    #[msg("Signer is not the treasury admin")]
    Unauthorized,
}

// ---------------------------------------------------------------------------
// Events
// ---------------------------------------------------------------------------

#[event]
pub struct TreasuryInitialized {
    pub admin: Pubkey,
    pub token_mint: Pubkey,
}

#[event]
pub struct FeesDeposited {
    pub depositor: Pubkey,
    pub amount: u64,
    pub total_fees_collected: u64,
}

#[event]
pub struct BuybackExecuted {
    pub admin: Pubkey,
    pub amount: u64,
    pub total_buybacks: u64,
    pub total_buyback_amount: u64,
}

#[event]
pub struct AdminTransferred {
    pub old_admin: Pubkey,
    pub new_admin: Pubkey,
}

#[event]
pub struct TreasuryStats {
    pub admin: Pubkey,
    pub token_mint: Pubkey,
    pub vault_balance: u64,
    pub total_fees_collected: u64,
    pub total_buybacks_executed: u64,
    pub total_buyback_amount: u64,
}
