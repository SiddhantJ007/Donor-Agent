import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  poweredByHeader: false,
  output: "export",
  // Allow this LAN browser to load Next's dev chunks, fonts, and HMR endpoint.
  // This affects `next dev` only; update the IP if the development machine changes.
  allowedDevOrigins: ["192.168.1.184"],
};

export default nextConfig;
