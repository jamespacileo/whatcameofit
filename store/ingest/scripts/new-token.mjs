// Makes a token for the ingest service and prints it once, with the entry to add to the
// secret INGEST_TOKENS. The service keeps only the SHA-256. Nothing is written or sent.
//   node scripts/new-token.mjs device mini
import { createHash, randomBytes } from "node:crypto";

const [role, device] = process.argv.slice(2);
const roles = ["device", "daily", "lookup", "consumer", "export", "operator"];
if (!roles.includes(role) || (role === "device" && !device)) {
  console.error(`usage: node scripts/new-token.mjs <${roles.join("|")}> [device]   (a device token needs the device's name)`);
  process.exit(2);
}
const token = randomBytes(32).toString("base64url");
const entry = { name: device ? `${role}-${device}` : role, role, ...(device ? { device } : {}), sha256: createHash("sha256").update(token).digest("hex") };
console.error("The token, shown once. Give it to the writer and keep it nowhere else:");
console.log(token);
console.error("\nThe entry to add to the INGEST_TOKENS list:");
console.error(JSON.stringify(entry));
