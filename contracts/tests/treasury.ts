import * as anchor from "@coral-xyz/anchor";
import { Program } from "@coral-xyz/anchor";
import {
  createMint,
  createAssociatedTokenAccount,
  mintTo,
  getAccount,
  TOKEN_PROGRAM_ID,
} from "@solana/spl-token";
import { expect } from "chai";

type Treasury = any;

describe("treasury", () => {
  const provider = anchor.AnchorProvider.env();
  anchor.setProvider(provider);

  const program = anchor.workspace.Treasury as Program<Treasury>;
  const admin = provider.wallet as anchor.Wallet;

  let tokenMint: anchor.web3.PublicKey;
  let adminTokenAccount: anchor.web3.PublicKey;

  const [treasuryPda] = anchor.web3.PublicKey.findProgramAddressSync(
    [Buffer.from("treasury")],
    program.programId
  );
  const [treasuryVaultPda] = anchor.web3.PublicKey.findProgramAddressSync(
    [Buffer.from("treasury_vault")],
    program.programId
  );

  before(async () => {
    // Create $FNDRY mint
    tokenMint = await createMint(
      provider.connection,
      (admin as any).payer,
      admin.publicKey,
      null,
      9
    );

    // Create admin ATA and mint tokens
    adminTokenAccount = await createAssociatedTokenAccount(
      provider.connection,
      (admin as any).payer,
      tokenMint,
      admin.publicKey
    );

    await mintTo(
      provider.connection,
      (admin as any).payer,
      tokenMint,
      adminTokenAccount,
      admin.publicKey,
      10_000_000_000 // 10B tokens
    );
  });

  it("initializes the treasury", async () => {
    await program.methods
      .initialize()
      .accounts({
        admin: admin.publicKey,
        tokenMint,
        treasury: treasuryPda,
        treasuryVault: treasuryVaultPda,
        systemProgram: anchor.web3.SystemProgram.programId,
        tokenProgram: TOKEN_PROGRAM_ID,
        rent: anchor.web3.SYSVAR_RENT_PUBKEY,
      })
      .rpc();

    const treasury = await program.account.treasuryAccount.fetch(treasuryPda);
    expect(treasury.admin.toBase58()).to.equal(admin.publicKey.toBase58());
    expect(treasury.tokenMint.toBase58()).to.equal(tokenMint.toBase58());
    expect(treasury.totalFeesCollected.toNumber()).to.equal(0);
    expect(treasury.totalBuybacksExecuted.toNumber()).to.equal(0);
    expect(treasury.totalBuybackAmount.toNumber()).to.equal(0);
  });

  it("deposits fees into the treasury", async () => {
    const depositAmount = new anchor.BN(50_000_000); // 50M tokens

    await program.methods
      .depositFees(depositAmount)
      .accounts({
        depositor: admin.publicKey,
        treasury: treasuryPda,
        treasuryVault: treasuryVaultPda,
        depositorTokenAccount: adminTokenAccount,
        tokenProgram: TOKEN_PROGRAM_ID,
      })
      .rpc();

    // Verify vault balance
    const vault = await getAccount(provider.connection, treasuryVaultPda);
    expect(Number(vault.amount)).to.equal(50_000_000);

    // Verify treasury stats
    const treasury = await program.account.treasuryAccount.fetch(treasuryPda);
    expect(treasury.totalFeesCollected.toNumber()).to.equal(50_000_000);
  });

  it("deposits additional fees", async () => {
    const depositAmount = new anchor.BN(25_000_000);

    await program.methods
      .depositFees(depositAmount)
      .accounts({
        depositor: admin.publicKey,
        treasury: treasuryPda,
        treasuryVault: treasuryVaultPda,
        depositorTokenAccount: adminTokenAccount,
        tokenProgram: TOKEN_PROGRAM_ID,
      })
      .rpc();

    const treasury = await program.account.treasuryAccount.fetch(treasuryPda);
    expect(treasury.totalFeesCollected.toNumber()).to.equal(75_000_000);
  });

  it("rejects zero-amount deposit", async () => {
    try {
      await program.methods
        .depositFees(new anchor.BN(0))
        .accounts({
          depositor: admin.publicKey,
          treasury: treasuryPda,
          treasuryVault: treasuryVaultPda,
          depositorTokenAccount: adminTokenAccount,
          tokenProgram: TOKEN_PROGRAM_ID,
        })
        .rpc();
      expect.fail("Should have thrown");
    } catch (e: any) {
      expect(e.toString()).to.include("ZeroAmount");
    }
  });

  it("withdraws for buyback", async () => {
    const withdrawAmount = new anchor.BN(30_000_000);
    const balanceBefore = await getAccount(
      provider.connection,
      adminTokenAccount
    );

    await program.methods
      .withdrawForBuyback(withdrawAmount)
      .accounts({
        admin: admin.publicKey,
        treasury: treasuryPda,
        treasuryVault: treasuryVaultPda,
        destinationTokenAccount: adminTokenAccount,
        tokenProgram: TOKEN_PROGRAM_ID,
      })
      .rpc();

    // Verify tokens received
    const balanceAfter = await getAccount(
      provider.connection,
      adminTokenAccount
    );
    expect(Number(balanceAfter.amount) - Number(balanceBefore.amount)).to.equal(
      30_000_000
    );

    // Verify treasury stats
    const treasury = await program.account.treasuryAccount.fetch(treasuryPda);
    expect(treasury.totalBuybacksExecuted.toNumber()).to.equal(1);
    expect(treasury.totalBuybackAmount.toNumber()).to.equal(30_000_000);

    // Verify vault balance decreased
    const vault = await getAccount(provider.connection, treasuryVaultPda);
    expect(Number(vault.amount)).to.equal(45_000_000); // 75M - 30M
  });

  it("rejects withdrawal exceeding balance", async () => {
    try {
      await program.methods
        .withdrawForBuyback(new anchor.BN(999_999_999_999))
        .accounts({
          admin: admin.publicKey,
          treasury: treasuryPda,
          treasuryVault: treasuryVaultPda,
          destinationTokenAccount: adminTokenAccount,
          tokenProgram: TOKEN_PROGRAM_ID,
        })
        .rpc();
      expect.fail("Should have thrown");
    } catch (e: any) {
      expect(e.toString()).to.include("InsufficientBalance");
    }
  });

  it("rejects withdrawal from non-admin", async () => {
    const impostor = anchor.web3.Keypair.generate();
    const airdropSig = await provider.connection.requestAirdrop(
      impostor.publicKey,
      anchor.web3.LAMPORTS_PER_SOL
    );
    await provider.connection.confirmTransaction(airdropSig);

    // Create ATA for impostor
    const impostorAta = await createAssociatedTokenAccount(
      provider.connection,
      (admin as any).payer,
      tokenMint,
      impostor.publicKey
    );

    try {
      await program.methods
        .withdrawForBuyback(new anchor.BN(1_000_000))
        .accounts({
          admin: impostor.publicKey,
          treasury: treasuryPda,
          treasuryVault: treasuryVaultPda,
          destinationTokenAccount: impostorAta,
          tokenProgram: TOKEN_PROGRAM_ID,
        })
        .signers([impostor])
        .rpc();
      expect.fail("Should have thrown - impostor is not admin");
    } catch (e: any) {
      expect(e.toString()).to.include("Unauthorized");
    }
  });

  it("transfers admin authority", async () => {
    const newAdmin = anchor.web3.Keypair.generate();

    await program.methods
      .transferAdmin(newAdmin.publicKey)
      .accounts({
        admin: admin.publicKey,
        treasury: treasuryPda,
      })
      .rpc();

    const treasury = await program.account.treasuryAccount.fetch(treasuryPda);
    expect(treasury.admin.toBase58()).to.equal(newAdmin.publicKey.toBase58());

    // Transfer back for subsequent tests
    const airdropSig = await provider.connection.requestAirdrop(
      newAdmin.publicKey,
      anchor.web3.LAMPORTS_PER_SOL
    );
    await provider.connection.confirmTransaction(airdropSig);

    await program.methods
      .transferAdmin(admin.publicKey)
      .accounts({
        admin: newAdmin.publicKey,
        treasury: treasuryPda,
      })
      .signers([newAdmin])
      .rpc();

    const treasuryAfter = await program.account.treasuryAccount.fetch(
      treasuryPda
    );
    expect(treasuryAfter.admin.toBase58()).to.equal(
      admin.publicKey.toBase58()
    );
  });

  it("queries treasury stats", async () => {
    await program.methods
      .queryStats()
      .accounts({
        treasury: treasuryPda,
        treasuryVault: treasuryVaultPda,
      })
      .rpc();

    // Verify directly via account fetch
    const treasury = await program.account.treasuryAccount.fetch(treasuryPda);
    expect(treasury.totalFeesCollected.toNumber()).to.equal(75_000_000);
    expect(treasury.totalBuybacksExecuted.toNumber()).to.equal(1);
    expect(treasury.totalBuybackAmount.toNumber()).to.equal(30_000_000);
  });
});
