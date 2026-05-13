// Verify cross-language parity: derive EVM + Solana addresses from the
// canonical Trezor "abandon" BIP-39 test vector using ClawRouter's exact
// algorithm (mirrors ClawRouter/src/wallet.ts). The Python plugin's
// wallet.py must produce identical addresses.
//
// Resolves dependencies from the sibling ClawRouter checkout so we don't
// duplicate node_modules in this repo. Override with CLAWROUTER_DIR env.

import { createRequire } from "node:module";
import { existsSync } from "node:fs";
import { resolve, dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const clawrouterDir = process.env.CLAWROUTER_DIR
  ? resolve(process.env.CLAWROUTER_DIR)
  : resolve(here, "..", "..", "ClawRouter");

const clawrouterPkgJson = join(clawrouterDir, "package.json");
if (!existsSync(clawrouterPkgJson)) {
  console.error(
    `ClawRouter checkout not found at ${clawrouterDir}. ` +
    `Set CLAWROUTER_DIR=<path>.`,
  );
  process.exit(2);
}

const req = createRequire(clawrouterPkgJson);
const { HDKey } = req("@scure/bip32");
const { mnemonicToSeedSync } = req("@scure/bip39");
const { hmac } = req("@noble/hashes/hmac.js");
const { sha512 } = req("@noble/hashes/sha2.js");
const { privateKeyToAccount } = req("viem/accounts");

// @solana/kit is ESM-only — load via createRequire path resolution then dynamic import.
const solanaKitEntry = req.resolve("@solana/kit");
const { createKeyPairSignerFromPrivateKeyBytes } = await import(solanaKitEntry);

const MNEMONIC =
  "abandon abandon abandon abandon abandon abandon abandon abandon " +
  "abandon abandon abandon about";

const seed = mnemonicToSeedSync(MNEMONIC);

// EVM: BIP-44 m/44'/60'/0'/0/0
const hd = HDKey.fromMasterSeed(seed).derive("m/44'/60'/0'/0/0");
const evmPriv = `0x${Buffer.from(hd.privateKey).toString("hex")}`;
const evmAddr = privateKeyToAccount(evmPriv).address;

// Solana: SLIP-10 Ed25519 m/44'/501'/0'/0'
const SOLANA_HARDENED_INDICES = [
  44 + 0x80000000, 501 + 0x80000000, 0 + 0x80000000, 0 + 0x80000000,
];
let I = hmac(sha512, new TextEncoder().encode("ed25519 seed"), seed);
let key = I.slice(0, 32);
let chainCode = I.slice(32);
for (const index of SOLANA_HARDENED_INDICES) {
  const data = new Uint8Array(37);
  data[0] = 0x00;
  data.set(key, 1);
  data[33] = (index >>> 24) & 0xff;
  data[34] = (index >>> 16) & 0xff;
  data[35] = (index >>> 8) & 0xff;
  data[36] = index & 0xff;
  I = hmac(sha512, chainCode, data);
  key = I.slice(0, 32);
  chainCode = I.slice(32);
}
const solanaPrivBytes = new Uint8Array(key);
const signer = await createKeyPairSignerFromPrivateKeyBytes(solanaPrivBytes);

console.log(JSON.stringify({
  mnemonic: MNEMONIC,
  evm_address: evmAddr,
  solana_address: signer.address,
  evm_priv: evmPriv,
  solana_priv_hex: Buffer.from(solanaPrivBytes).toString("hex"),
}, null, 2));
