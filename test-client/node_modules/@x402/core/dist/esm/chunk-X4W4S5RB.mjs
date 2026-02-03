// src/types/facilitator.ts
var VerifyError = class extends Error {
  /**
   * Creates a VerifyError from a failed verification response.
   *
   * @param statusCode - HTTP status code from the facilitator
   * @param response - The verify response containing error details
   */
  constructor(statusCode, response) {
    super(`verification failed: ${response.invalidReason || "unknown reason"}`);
    this.name = "VerifyError";
    this.statusCode = statusCode;
    this.invalidReason = response.invalidReason;
    this.payer = response.payer;
  }
};
var SettleError = class extends Error {
  /**
   * Creates a SettleError from a failed settlement response.
   *
   * @param statusCode - HTTP status code from the facilitator
   * @param response - The settle response containing error details
   */
  constructor(statusCode, response) {
    super(`settlement failed: ${response.errorReason || "unknown reason"}`);
    this.name = "SettleError";
    this.statusCode = statusCode;
    this.errorReason = response.errorReason;
    this.payer = response.payer;
    this.transaction = response.transaction;
    this.network = response.network;
  }
};

export {
  VerifyError,
  SettleError
};
//# sourceMappingURL=chunk-X4W4S5RB.mjs.map