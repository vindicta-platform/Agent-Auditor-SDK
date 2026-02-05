# Agent-Auditor-SDK Roadmap

> **Vision**: Quota-aware AI scheduling that never blocks humans  
> **Status**: Active Development  
> **Last Updated**: 2026-02-05

---

## 📅 6-Week Schedule (Feb 4 - Mar 17, 2026)

> **GitHub Project**: https://github.com/orgs/vindicta-platform/projects/4  
> **Master Roadmap**: https://github.com/vindicta-platform/.github/blob/master/ROADMAP.md

### Week 1: Feb 4-10 — Priority Queue ✅
| Day | Task | Priority | Status |
|-----|------|----------|--------|
| Mon 4 | Implement priority queue with human P0 preemption | P1 | ✅ PR #11 |
| Tue 5 | Gemini rate limiting implementation | P1 | ✅ PR #12 |
| Wed 6 | Gemini adapter implementation | P1 | ✅ PR #12 |
| Thu 7 | Unit tests | P1 | ⚠️ Issue #13 |

**Status**: Core implementation complete. BDD tests pending (Week 2).

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
| Metric | Target | Status |
|--------|--------|--------|
| **Human Success Rate** | 100% (when quota exists) | ✅ Achieved |
| **Preemption Latency** | <1 second | ✅ Achieved |
| **Rate Limit Handling** | Zero 429 errors passed to humans | ✅ Achieved |

### Exit Criteria
- [x] `agent-auditor` package installable via pip
- [x] Gemini adapter with proactive rate limiting (merged PR #12)
- [ ] Unit tests passing (BDD tests pending - Issue #13)
- [x] CLI tool functional
- [x] README documentation complete

**Status**: 80% complete. BDD tests moved to Week 2 per architecture review.

---

*Last Updated: 2026-02-05*
