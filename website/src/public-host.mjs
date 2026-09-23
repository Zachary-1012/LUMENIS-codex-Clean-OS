const reservedHosts = new Set([
  "localhost",
  "example.com",
  "example.net",
  "example.org",
]);

const reservedSuffixes = [
  ".localhost",
  ".invalid",
  ".example",
  ".test",
  ".example.com",
  ".example.net",
  ".example.org",
];

export function isReservedPublicHost(hostname) {
  const host = hostname.toLowerCase().replace(/\.$/, "");
  return reservedHosts.has(host) ||
    ["invalid", "example", "test"].includes(host) ||
    reservedSuffixes.some((suffix) => host.endsWith(suffix));
}
