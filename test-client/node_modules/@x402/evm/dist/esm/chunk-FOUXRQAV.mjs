import {
  authorizationTypes,
  createNonce
} from "./chunk-ZYXTTU74.mjs";

// src/exact/client/scheme.ts
import { getAddress } from "viem";
var ExactEvmScheme = class {
  /**
   * Creates a new ExactEvmClient instance.
   *
   * @param signer - The EVM signer for client operations
   */
  constructor(signer) {
    this.signer = signer;
    this.scheme = "exact";
  }
  /**
   * Creates a payment payload for the Exact scheme.
   *
   * @param x402Version - The x402 protocol version
   * @param paymentRequirements - The payment requirements
   * @returns Promise resolving to a payment payload
   */
  async createPaymentPayload(x402Version, paymentRequirements) {
    const nonce = createNonce();
    const now = Math.floor(Date.now() / 1e3);
    const authorization = {
      from: this.signer.address,
      to: getAddress(paymentRequirements.payTo),
      value: paymentRequirements.amount,
      validAfter: (now - 600).toString(),
      // 10 minutes before
      validBefore: (now + paymentRequirements.maxTimeoutSeconds).toString(),
      nonce
    };
    const signature = await this.signAuthorization(authorization, paymentRequirements);
    const payload = {
      authorization,
      signature
    };
    return {
      x402Version,
      payload
    };
  }
  /**
   * Sign the EIP-3009 authorization using EIP-712
   *
   * @param authorization - The authorization to sign
   * @param requirements - The payment requirements
   * @returns Promise resolving to the signature
   */
  async signAuthorization(authorization, requirements) {
    const chainId = parseInt(requirements.network.split(":")[1]);
    if (!requirements.extra?.name || !requirements.extra?.version) {
      throw new Error(
        `EIP-712 domain parameters (name, version) are required in payment requirements for asset ${requirements.asset}`
      );
    }
    const { name, version } = requirements.extra;
    const domain = {
      name,
      version,
      chainId,
      verifyingContract: getAddress(requirements.asset)
    };
    const message = {
      from: getAddress(authorization.from),
      to: getAddress(authorization.to),
      value: BigInt(authorization.value),
      validAfter: BigInt(authorization.validAfter),
      validBefore: BigInt(authorization.validBefore),
      nonce: authorization.nonce
    };
    return await this.signer.signTypedData({
      domain,
      types: authorizationTypes,
      primaryType: "TransferWithAuthorization",
      message
    });
  }
};

export {
  ExactEvmScheme
};
//# sourceMappingURL=chunk-FOUXRQAV.mjs.map