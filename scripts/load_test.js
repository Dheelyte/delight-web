// k6 smoke load test for the public surface.
//
// Usage:
//   k6 run -e BASE=https://<your-domain> --vus 50 --duration 2m scripts/load_test.js
//
// Targets:
//   - Homepage p95 < 100 ms with warm CDN cache
//   - Search p95 < 200 ms (always dynamic, no CDN cache)
//   - Error rate < 0.1%

import { check, sleep } from "k6";
import http from "k6/http";

const BASE = __ENV.BASE || "http://localhost:3000";

export const options = {
  thresholds: {
    http_req_duration: ["p(95)<200"],
    http_req_failed: ["rate<0.001"],
  },
};

export default function () {
  const home = http.get(`${BASE}/`);
  check(home, {
    "home 200": (r) => r.status === 200,
    "home has feed": (r) => /<article/.test(r.body),
  });

  const sitemap = http.get(`${BASE}/sitemap.xml`);
  check(sitemap, { "sitemap 200": (r) => r.status === 200 });

  const search = http.get(`${BASE}/search?q=stack`);
  check(search, { "search 200": (r) => r.status === 200 });

  sleep(Math.random() * 2);
}
