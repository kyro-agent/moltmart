// src/constants.ts
var authorizationTypes = {
  TransferWithAuthorization: [
    { name: "from", type: "address" },
    { name: "to", type: "address" },
    { name: "value", type: "uint256" },
    { name: "validAfter", type: "uint256" },
    { name: "validBefore", type: "uint256" },
    { name: "nonce", type: "bytes32" }
  ]
};
var eip3009ABI = [
  {
    inputs: [
      { name: "from", type: "address" },
      { name: "to", type: "address" },
      { name: "value", type: "uint256" },
      { name: "validAfter", type: "uint256" },
      { name: "validBefore", type: "uint256" },
      { name: "nonce", type: "bytes32" },
      { name: "v", type: "uint8" },
      { name: "r", type: "bytes32" },
      { name: "s", type: "bytes32" }
    ],
    name: "transferWithAuthorization",
    outputs: [],
    stateMutability: "nonpayable",
    type: "function"
  },
  {
    inputs: [
      { name: "from", type: "address" },
      { name: "to", type: "address" },
      { name: "value", type: "uint256" },
      { name: "validAfter", type: "uint256" },
      { name: "validBefore", type: "uint256" },
      { name: "nonce", type: "bytes32" },
      { name: "signature", type: "bytes" }
    ],
    name: "transferWithAuthorization",
    outputs: [],
    stateMutability: "nonpayable",
    type: "function"
  },
  {
    inputs: [{ name: "account", type: "address" }],
    name: "balanceOf",
    outputs: [{ name: "", type: "uint256" }],
    stateMutability: "view",
    type: "function"
  },
  {
    inputs: [],
    name: "version",
    outputs: [{ name: "", type: "string" }],
    stateMutability: "view",
    type: "function"
  }
];

// src/utils.ts
import { toHex } from "viem";
function getEvmChainId(network) {
  const networkMap = {
    base: 8453,
    "base-sepolia": 84532,
    ethereum: 1,
    sepolia: 11155111,
    polygon: 137,
    "polygon-amoy": 80002
  };
  return networkMap[network] || 1;
}
function createNonce() {
  const cryptoObj = typeof globalThis.crypto !== "undefined" ? globalThis.crypto : globalThis.crypto;
  if (!cryptoObj) {
    throw new Error("Crypto API not available");
  }
  return toHex(cryptoObj.getRandomValues(new Uint8Array(32)));
}

export {
  authorizationTypes,
  eip3009ABI,
  getEvmChainId,
  createNonce
};
//# sourceMappingURL=chunk-ZYXTTU74.mjs.map