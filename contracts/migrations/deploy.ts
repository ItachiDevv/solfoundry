// Anchor migration script for deploying SolFoundry contracts.
// Run via: anchor migrate

const anchor = require("@coral-xyz/anchor");

module.exports = async function (provider: any) {
  // Configure client to use the provider.
  anchor.setProvider(provider);

  console.log("Deploying SolFoundry contracts...");
  console.log("Provider cluster:", provider.connection.rpcEndpoint);
  console.log("Wallet:", provider.wallet.publicKey.toBase58());

  // Programs are deployed by `anchor deploy`.
  // This script can be used for post-deploy initialization (e.g., treasury init).
  // For now, it's a placeholder for future migration logic.

  console.log("Migration complete.");
};
