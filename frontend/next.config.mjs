/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",  // self-contained server for the container image (frontend/Dockerfile)
  // Spreadsheet uploads go through a server action (limit enforced again by the API: 5 MB).
  experimental: { serverActions: { bodySizeLimit: "6mb" } },
};
export default nextConfig;
