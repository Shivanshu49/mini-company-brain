// MOCK: canned answers for the judging demo questions, used only when the backend is unreachable.
import type { Answer } from './api'

const e = (source: string, target: string, label: string) => ({ source, target, label })

export const SAMPLES: Record<string, Omit<Answer, 'sample'>> = {
  'Why does refund-service retry refunds with exponential backoff, and who should I contact if it breaks?': {
    answer:
      'Immediate retries were making refund failures worse. PAY-231 reported that about 4% of refunds failed on Kosha Bank refund API timeouts, and retrying straight away hit the Kosha Bank rate limit (HTTP 429). In the Payments Weekly Sync on 2026-08-12, Priya Sharma chose exponential backoff with jitter over fixed delays or a queue (MTG-2026-08-12). Rahul Verma wrote it up as RFC-014 and shipped it in PR #482, which cut the failure rate from 4% to 0.6% (SLACK-2026-08-20).\n\nIf it breaks, contact Rahul Verma, the refund-service owner. His backup is Neha Gupta, and escalation ends with Priya Sharma (DOC-004).',
    sources: [
      { id: 'PAY-231', type: 'ticket', date: '2026-07-28', title: 'UPI refunds failing when Kosha Bank refund API times out', snippet: 'About 4% of refunds fail with a timeout from the Kosha Bank refund API. refund-service retries immediately and hits the Kosha Bank rate limit.' },
      { id: 'MTG-2026-08-12', type: 'meeting', date: '2026-08-12', title: 'Payments Weekly Sync', snippet: 'Priya Sharma decided on option (b), exponential backoff with jitter and a maximum of 3 retries, because it respects Kosha Bank rate limits and keeps refunds fast for merchants.' },
      { id: 'RFC-014', type: 'document', date: '2026-08-14', title: 'Refund retry strategy for refund-service', snippet: 'refund-service will retry failed refund calls using exponential backoff with jitter. Base delay: 2 seconds. Maximum retries: 3.' },
      { id: 'SLACK-2026-08-20', type: 'slack', date: '2026-08-20', title: '#payments-eng', snippet: 'Rahul Verma: RFC-014 is implemented in refund-service. PR #482 merged. Refund failure rate dropped from 4% to 0.6%.' },
      { id: 'DOC-004', type: 'document', date: '2026-07-01', title: 'Service ownership and on-call escalation', snippet: 'refund-service: owner Rahul Verma, backup Neha Gupta. Escalation path: on-call engineer, service owner, service backup, Priya Sharma.' },
    ],
    path: [
      e('Kosha Bank', 'PAY-231', 'HTTP 429 on retries'),
      e('PAY-231', 'MTG-2026-08-12', 'discussed in'),
      e('Priya Sharma', 'MTG-2026-08-12', 'decided in'),
      e('MTG-2026-08-12', 'RFC-014', 'documented in'),
      e('RFC-014', 'exponential backoff', 'specifies'),
      e('Rahul Verma', 'RFC-014', 'implemented, PR #482'),
      e('Rahul Verma', 'refund-service', 'owns'),
      e('Neha Gupta', 'refund-service', 'backup for'),
    ],
    conflicts: [],
  },
  'What is the current maximum retry count for refunds?': {
    answer:
      'The current maximum is 5 retries with a 10 second base delay. Priya Sharma approved the change in the INC-017 incident review on 2026-09-04 (MTG-2026-09-04), and Rahul Verma confirmed it is live in production (SLACK-2026-09-10). Refunds that exhaust their retries now go to a dead-letter queue instead of being marked FAILED.\n\nRFC-014 still says 3 retries with a 2 second base delay. It is outdated.',
    sources: [
      { id: 'RFC-014', type: 'document', date: '2026-08-14', title: 'Refund retry strategy for refund-service', snippet: 'Maximum retries: 3. After 3 failed retries the refund is marked FAILED and the merchant is notified.' },
      { id: 'MTG-2026-09-04', type: 'meeting', date: '2026-09-04', title: 'INC-017 incident review', snippet: 'Priya Sharma approved increasing the refund maximum retries from 3 to 5 and the base delay from 2 seconds to 10 seconds. Refunds that exhaust retries will go to a dead-letter queue.' },
      { id: 'SLACK-2026-09-10', type: 'slack', date: '2026-09-10', title: '#payments-eng', snippet: 'Rahul Verma: refund.max_retries is now 5 with a 10 second base delay in production, as approved in the INC-017 review.' },
    ],
    path: [
      e('INC-017', 'MTG-2026-09-04', 'reviewed in'),
      e('Priya Sharma', 'MTG-2026-09-04', 'approved in'),
      e('MTG-2026-09-04', 'max retries: 5', 'sets'),
      e('SLACK-2026-09-10', 'max retries: 5', 'confirms live'),
      e('RFC-014', 'max retries: 3', 'sets'),
      e('MTG-2026-09-04', 'RFC-014', 'supersedes'),
    ],
    conflicts: [
      { outdated: 'RFC-014', current: 'MTG-2026-09-04', note: 'RFC-014 (14 Aug) says 3 retries with a 2 second base delay. MTG-2026-09-04 (4 Sep) raised it to 5 retries, 10 second base delay, plus a dead-letter queue.' },
    ],
  },
  'Which cloud provider does PayNest host its services on?': {
    answer: 'Not found in company knowledge.',
    sources: [],
    path: [],
    conflicts: [],
  },
}
