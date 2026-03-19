import * as anchor from "@coral-xyz/anchor";
import { Program } from "@coral-xyz/anchor";
import { expect } from "chai";

type Reputation = any;

describe("reputation", () => {
  const provider = anchor.AnchorProvider.env();
  anchor.setProvider(provider);

  const program = anchor.workspace.Reputation as Program<Reputation>;
  const authority = provider.wallet as anchor.Wallet;

  const contributorKeypair = anchor.web3.Keypair.generate();

  const [reputationPda] = anchor.web3.PublicKey.findProgramAddressSync(
    [Buffer.from("reputation"), contributorKeypair.publicKey.toBuffer()],
    program.programId
  );

  it("initializes reputation for a contributor", async () => {
    await program.methods
      .initialize()
      .accounts({
        payer: authority.publicKey,
        contributor: contributorKeypair.publicKey,
        reputation: reputationPda,
        systemProgram: anchor.web3.SystemProgram.programId,
      })
      .rpc();

    const rep = await program.account.reputationAccount.fetch(reputationPda);
    expect(rep.contributor.toBase58()).to.equal(
      contributorKeypair.publicKey.toBase58()
    );
    expect(rep.score.toNumber()).to.equal(0);
    expect(rep.bountiesCompleted.toNumber()).to.equal(0);
    expect(rep.bountiesFailed.toNumber()).to.equal(0);
    expect(rep.strikes).to.equal(0);
    expect(rep.bannedUntil.toNumber()).to.equal(0);
  });

  it("increments reputation on bounty completion", async () => {
    await program.methods
      .increment(new anchor.BN(5))
      .accounts({
        authority: authority.publicKey,
        contributor: contributorKeypair.publicKey,
        reputation: reputationPda,
      })
      .rpc();

    const rep = await program.account.reputationAccount.fetch(reputationPda);
    expect(rep.score.toNumber()).to.equal(5);
    expect(rep.bountiesCompleted.toNumber()).to.equal(1);
  });

  it("reaches Builder tier after accumulating points", async () => {
    // Add 10 more points to get to 15 total (Builder tier: 11-50)
    await program.methods
      .increment(new anchor.BN(10))
      .accounts({
        authority: authority.publicKey,
        contributor: contributorKeypair.publicKey,
        reputation: reputationPda,
      })
      .rpc();

    const rep = await program.account.reputationAccount.fetch(reputationPda);
    expect(rep.score.toNumber()).to.equal(15);
    expect(rep.bountiesCompleted.toNumber()).to.equal(2);
  });

  it("decrements reputation on failed submission", async () => {
    await program.methods
      .decrement(new anchor.BN(3))
      .accounts({
        authority: authority.publicKey,
        contributor: contributorKeypair.publicKey,
        reputation: reputationPda,
      })
      .rpc();

    const rep = await program.account.reputationAccount.fetch(reputationPda);
    expect(rep.score.toNumber()).to.equal(12);
    expect(rep.bountiesFailed.toNumber()).to.equal(1);
    expect(rep.strikes).to.equal(1);
  });

  it("applies temp ban after 3 strikes", async () => {
    // Strike 2
    await program.methods
      .decrement(new anchor.BN(1))
      .accounts({
        authority: authority.publicKey,
        contributor: contributorKeypair.publicKey,
        reputation: reputationPda,
      })
      .rpc();

    // Strike 3 -> ban
    await program.methods
      .decrement(new anchor.BN(1))
      .accounts({
        authority: authority.publicKey,
        contributor: contributorKeypair.publicKey,
        reputation: reputationPda,
      })
      .rpc();

    const rep = await program.account.reputationAccount.fetch(reputationPda);
    expect(rep.strikes).to.equal(3);
    expect(rep.bannedUntil.toNumber()).to.be.greaterThan(0);
    expect(rep.score.toNumber()).to.equal(10);
  });

  it("rejects increment while banned", async () => {
    try {
      await program.methods
        .increment(new anchor.BN(5))
        .accounts({
          authority: authority.publicKey,
          contributor: contributorKeypair.publicKey,
          reputation: reputationPda,
        })
        .rpc();
      expect.fail("Should have thrown - contributor is banned");
    } catch (e: any) {
      expect(e.toString()).to.include("TemporarilyBanned");
    }
  });

  it("admin resets strikes and lifts ban", async () => {
    await program.methods
      .resetStrikes()
      .accounts({
        authority: authority.publicKey,
        contributor: contributorKeypair.publicKey,
        reputation: reputationPda,
      })
      .rpc();

    const rep = await program.account.reputationAccount.fetch(reputationPda);
    expect(rep.strikes).to.equal(0);
    expect(rep.bannedUntil.toNumber()).to.equal(0);
  });

  it("allows increment after ban is lifted", async () => {
    await program.methods
      .increment(new anchor.BN(5))
      .accounts({
        authority: authority.publicKey,
        contributor: contributorKeypair.publicKey,
        reputation: reputationPda,
      })
      .rpc();

    const rep = await program.account.reputationAccount.fetch(reputationPda);
    expect(rep.score.toNumber()).to.equal(15);
  });

  it("queries reputation data", async () => {
    // Just ensure the query instruction doesn't fail
    await program.methods
      .query()
      .accounts({
        contributor: contributorKeypair.publicKey,
        reputation: reputationPda,
      })
      .rpc();

    // Direct account fetch for verification
    const rep = await program.account.reputationAccount.fetch(reputationPda);
    expect(rep.contributor.toBase58()).to.equal(
      contributorKeypair.publicKey.toBase58()
    );
  });

  describe("second contributor", () => {
    const contributor2 = anchor.web3.Keypair.generate();
    const [rep2Pda] = anchor.web3.PublicKey.findProgramAddressSync(
      [Buffer.from("reputation"), contributor2.publicKey.toBuffer()],
      program.programId
    );

    it("initializes independent reputation for another contributor", async () => {
      await program.methods
        .initialize()
        .accounts({
          payer: authority.publicKey,
          contributor: contributor2.publicKey,
          reputation: rep2Pda,
          systemProgram: anchor.web3.SystemProgram.programId,
        })
        .rpc();

      const rep = await program.account.reputationAccount.fetch(rep2Pda);
      expect(rep.score.toNumber()).to.equal(0);
      expect(rep.contributor.toBase58()).to.equal(
        contributor2.publicKey.toBase58()
      );
    });
  });
});
