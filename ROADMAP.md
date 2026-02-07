# Agent-Auditor-SDK Roadmap

> **Vision**: Quota-aware AI scheduling that never blocks humans
> **Status**: Active Development
> **Last Updated**: 2026-02-05

---

## 📅 6-Week Schedule (Feb 4 - Mar 17, 2026)

> **GitHub Project**: https://github.com/orgs/vindicta-platform/projects/4
> **Master Roadmap**: https://github.com/vindicta-platform/.github/blob/master/ROADMAP.md

### Week 1: Feb 4-10 — Priority Queue
| Day | Task | Priority | Status |
|-----|------|----------|--------|
| Mon 4 | Implement priority queue with human P0 preemption | P1 | [x] |
| Tue 5 | Gemini rate limiting implementation | P1 | [x] |
| Wed 6 | Gemini adapter implementation | P1 | [x] |
| Thu 7 | Unit tests | P1 | [x] |


### Week 3: Feb 18-24 — Prediction Engine
| Day | Task | Priority |
|-----|------|----------|
| Mon 18 | Quota prediction algorithm | P1 |
| Tue 19 | SQLite journal implementation (part 1) | P1 |
| Wed 20 | SQLite journal implementation (part 2) | P1 |
| Thu 21 | Batch job processing | P1 |
| **Sun 24** | **v0.2.0 Prediction Release** | ⭐ |

### Week 5: Mar 4-10 — Integration
| Day | Task | Priority |
|-----|------|----------|
| Mon 4 | Meta-Oracle integration | P1 |
| Tue 5 | Primordia integration | P1 |
| Wed 6 | WARScribe integration | P1 |
| Thu 7 | Integration tests | P1 |
| **Sun 10** | **v0.3.0 Integration Release** | ⭐ |

---

## v1.0 Target: March 2026

### Mission Statement

Deliver a production-ready SDK that manages AI API quota across all Vindicta products, ensuring human requests always succeed while maximizing background task throughput.

---

## Milestone Timeline

```
┌─────────────────────────────────────────────────────────────────┐
│  Feb 2026          Mar 2026          Apr 2026                   │
│  ─────────────────────────────────────────────────────────────  │
│  [v0.1.0]          [v0.2.0]          [v0.3.0]      [v1.0.0]     │
│  Priority Queue    Prediction        Integration   Dashboard    │
│                                                                  │
│  Week 1-2          Week 3-4          Week 5-6      Week 7-8     │
└─────────────────────────────────────────────────────────────────┘
```

---

## v0.1.0 — Priority Queue (Target: Feb 10, 2026)

### Deliverables
- [x] Dual-priority queue (HUMAN P0, BACKGROUND P1-P5)
- [x] Gemini API adapter with rate limiting
- [x] Human priority guarantee (preemption)
- [x] In-memory task queue
- [x] Basic retry with exponential backoff


### Key Measurable Results
| Metric | Target | Measurement |
|--------|--------|-------------|
| **Human Success Rate** | 100% (when quota exists) | Integration test |
| **Preemption Latency** | <1 second | Benchmark |
| **Rate Limit Handling** | Zero 429 errors passed to humans | Error logs |

### Exit Criteria
- [ ] Human requests never blocked by background tasks
- [ ] Rate limiting prevents API abuse
- [ ] Retry logic handles transient failures

---

## v0.2.0 — Prediction Engine (Target: Feb 24, 2026)

### Deliverables
- [ ] UsageJournal persistence (SQLite)
- [ ] QuotaPredictor with historical patterns
- [ ] Safe budget calculation algorithm
- [ ] Time-of-day / day-of-week awareness
- [ ] Configurable human reserve (default 20%)

### Key Measurable Results
| Metric | Target | Measurement |
|--------|--------|-------------|
| **Prediction Accuracy** | Within 15% of actual | 7-day comparison |
| **Budget Utilization** | 80-95% of predicted surplus | Usage logs |
| **Adaptation Speed** | Pattern learning in <24 hours | Test with synthetic data |

### Exit Criteria
- [ ] Predictor trained on 7 days of data
- [ ] Background tasks throttle appropriately
- [ ] Usage history persists across restarts

---

## v0.3.0 — Product Integration (Target: Mar 10, 2026)

### Deliverables
- [ ] Meta-Oracle integration
- [ ] Primordia AI integration
- [ ] WARScribe-Parser (Whisper) integration
- [ ] Persistent task queue (survives restarts)
- [ ] Task cost estimation

### Key Measurable Results
| Metric | Target | Measurement |
|--------|--------|-------------|
| **Products Integrated** | 3+ products using SDK | Code review |
| **Queue Persistence** | 100% task recovery after restart | Integration test |
| **Cost Estimation Accuracy** | Within 20% of actual | Token comparison |

### Exit Criteria
- [ ] All AI products route through Agent-Auditor
- [ ] Queue survives process restarts
- [ ] Cost estimates inform scheduling

---

## v1.0.0 — Production Dashboard (Target: Mar 31, 2026)

### Deliverables
- [ ] Quota visibility dashboard
- [ ] Real-time usage display
- [ ] Historical usage charts
- [ ] Task breakdown by product
- [ ] PyPI publication

### Key Measurable Results
| Metric | Target | Measurement |
|--------|--------|-------------|
| **Dashboard Latency** | <5 second refresh | Performance test |
| **Visibility** | 100% of API calls tracked | Audit log |
| **User Satisfaction** | "I know where my quota went" | User feedback |
| **Uptime** | 99%+ | Monitoring |

### Exit Criteria
- [ ] Dashboard shows live quota status
- [ ] Complete audit trail for all API calls
- [ ] No critical bugs for 2 weeks

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | — | Personal API key (required) |
| `QUOTA_HUMAN_RESERVE_PERCENT` | 20 | Always keep this % for humans |
| `QUOTA_PREDICTION_LOOKBACK_DAYS` | 7 | Historical data for prediction |
| `QUOTA_RPM_LIMIT` | Auto | Requests per minute |
| `QUOTA_TPM_LIMIT` | Auto | Tokens per minute |

---

## API Key Security

### Storage & Access

| Protection | Implementation |
|------------|----------------|
| **No Hardcoding** | Key ONLY via environment variable, never in code |
| **No Git Exposure** | `.env` files in `.gitignore`, pre-commit hooks |
| **Memory Only** | Key loaded once at startup, not persisted to disk |
| **Process Isolation** | Key not passed to child processes or shared memory |

### Logging & Audit

| Rule | Implementation |
|------|----------------|
| **Never Log Keys** | All logging sanitizes `GEMINI_API_KEY` patterns |
| **Redact in Errors** | Exception handlers strip key from stack traces |
| **Audit Without Exposure** | Usage journal logs task IDs, not request payloads |
| **Masked Display** | Dashboard shows `AI***...***EY` format only |

### Abuse Prevention

| Protection | Mechanism |
|------------|-----------|
| **Rate Limiting** | SDK enforces tier limits BEFORE hitting API |
| **Budget Caps** | Background tasks capped at predicted surplus |
| **Exponential Backoff** | On 429 errors: 1s → 2s → 4s → 8s → pause |
| **Circuit Breaker** | After 5 consecutive failures, pause for 1 hour |
| **Max Daily Budget** | Configurable ceiling (default: 80% of RPD limit) |

### Terms of Service Compliance

| Requirement | Compliance |
|-------------|------------|
| **Rate Limits** | Respects all RPM/TPM/RPD limits from API tier |
| **No Aggressive Retry** | Backoff on 429, no retry spam |
| **Single User** | Key used by owner (Brandon Fox) |
| **No Sharing** | Key never transmitted to external services |
| **Minimal Footprint** | Background tasks yield to API tier constraints |
| **Purpose Aligned** | Usage for Vindicta platform development only |

### Security Checklist (v0.1.0)

- [ ] Pre-commit hook: block commits containing API keys
- [ ] Logging sanitizer: regex filter for key patterns
- [ ] Startup validation: verify key format, test with minimal call
- [ ] Shutdown cleanup: zero key from memory
- [ ] Error redaction: strip key from all exception messages

## Priority Levels

| Priority | Name | Use Case | Preemption |
|----------|------|----------|------------|
| P0 | HUMAN | Interactive requests | Immediate |
| P1 | CRITICAL | Rule-Sage audits | High |
| P2 | HIGH | Active debates | Normal |
| P3 | NORMAL | Batch processing | Deferrable |
| P4 | LOW | Exploratory work | Deferrable |
| P5 | BACKGROUND | Training runs | Lowest |

---

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| Gemini API | ✅ Available | Primary AI backend |
| SQLite | ✅ Available | Usage journal storage |
| Whisper API | ✅ Available | Secondary API support |

---

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Prediction inaccuracy | Medium | Medium | Conservative 20% reserve |
| API tier changes | Low | Low | Auto-detect limits |
| Queue grows unbounded | Medium | Medium | TTL on stale tasks |

---

## Success Criteria for v1

1. **Human Guarantee**: 100% human request success when quota exists
2. **Utilization**: >80% of safe budget used for background work
3. **Visibility**: Complete audit trail for all API usage
4. **Adoption**: All AI products integrated

---

*Maintained by: Vindicta Platform Team*
