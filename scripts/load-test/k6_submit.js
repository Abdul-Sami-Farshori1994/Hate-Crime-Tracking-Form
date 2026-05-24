/**
 * Light load smoke test (requires k6: https://k6.io).
 *
 *   k6 run -e API=http://localhost:8787 -e USER=user -e PASS=user scripts/load-test/k6_submit.js
 */
import http from 'k6/http'
import { check, sleep } from 'k6'

export const options = {
  vus: 5,
  duration: '30s',
  thresholds: {
    http_req_failed: ['rate<0.05'],
  },
}

const API = __ENV.API || 'http://localhost:8787'

export function setup() {
  const login = http.post(
    `${API}/auth/login`,
    JSON.stringify({ username: __ENV.USER || 'user', password: __ENV.PASS || 'user' }),
    { headers: { 'Content-Type': 'application/json' } },
  )
  check(login, { 'login ok': (r) => r.status === 200 })
  return { token: login.json('access_token') }
}

export default function (data) {
  const headers = {
    Authorization: `Bearer ${data.token}`,
    'Content-Type': 'application/json',
  }
  const flow = http.get(`${API}/form/flow`, { headers })
  check(flow, { 'flow ok': (r) => r.status === 200 })
  sleep(1)
}
