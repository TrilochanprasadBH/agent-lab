"""A small internal-docs corpus and a question set with known gold documents.

The documents are written the way real runbooks are written: dense with domain
vocabulary, inconsistent about phrasing, and full of near-neighbours. The queries
are written the way people actually ask: shorter, differently inflected, and
using the word they know rather than the word the document chose.

That gap is the whole exercise. A naive term counter ranks the wrong document
first because common words ("service", "error", "request", "cache") appear
everywhere; a retrievable corpus needs term weighting, morphology, and an alias
table — all of which are engineering, not magic.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Doc:
    doc_id: str
    title: str
    body: str


@dataclass(frozen=True)
class Query:
    doc_id: str
    text: str
    gold: str
    raw: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "raw", self.text)


DOCS: tuple[Doc, ...] = (
    Doc("d01", "Authentication and single sign-on",
        "Users sign in through the identity provider with SAML. A failed sign-in is "
        "almost always an assertion consumer URL mismatch or clock skew beyond five minutes."),
    Doc("d02", "Rotating SAML signing certificates",
        "Signing certificates expire yearly. Publish the new certificate to the identity "
        "provider before removing the old one, then rerun the sign-in smoke test."),
    Doc("d03", "API rate limits",
        "Each API key gets a token bucket of 600 requests per minute. Exceeding the bucket "
        "returns HTTP 429 together with a Retry-After response header."),
    Doc("d04", "Handling 429 responses",
        "Back off exponentially when you receive a 429. Do not retry immediately: the bucket "
        "refills steadily rather than in bursts, so hammering wastes your quota."),
    Doc("d05", "Nightly Postgres backups",
        "A base backup runs at 02:00 UTC and WAL segments stream continuously afterwards. "
        "Retention is 35 days for the base and the same window for the logs."),
    Doc("d06", "Restoring a database from backup",
        "Restore the base backup, then replay WAL to the target time. Validate row counts on "
        "the three largest tables before any traffic is switched over to the new instance."),
    Doc("d07", "Reverting a bad deploy",
        "Run the rollback job for the previous release tag. Migrations are kept unless the "
        "change was marked destructive, in which case you need the database team."),
    Doc("d08", "Feature flag lifecycle",
        "Flags default to off and are scoped to one audience. Remove a flag within 30 days of "
        "full rollout; stale flags are the main source of dead code in this service."),
    Doc("d09", "Postgres failover",
        "A promoted replica takes over within 40 seconds. The connection pooler retries, but "
        "in-flight transactions are lost and must be replayed by the client."),
    Doc("d10", "Redis memory and eviction",
        "Under memory pressure keys are evicted with an allkeys-lru policy. Session data must "
        "not live only in Redis without a database fallback, or users are logged out at random."),
    Doc("d11", "Consumer lag",
        "Lag above 50000 messages for ten minutes pages the on-call engineer. Scale consumers "
        "before adding partitions; a rebalance causes its own delay and hides the real problem."),
    Doc("d12", "TLS certificates",
        "Certificates are issued by the internal CA and expire in 90 days. Renewal is automatic "
        "unless the DNS challenge fails, which happens after a nameserver change."),
    Doc("d13", "DNS changes",
        "Records carry a 300 second TTL. Lower the TTL a full day before a cutover, or the old "
        "address stays authoritative for hours after you think you moved."),
    Doc("d14", "CDN cache purges",
        "Purge by tag rather than by path. A full purge takes up to five minutes to propagate "
        "to every edge location, so purge precisely when you are in a hurry."),
    Doc("d15", "Log retention",
        "Application logs are retained 14 days and audit logs 400 days. Audit retention is a "
        "compliance requirement and cannot be reduced by the service owner."),
    Doc("d16", "Rotating secrets",
        "Service credentials rotate every 90 days through the vault. Consumers read the latest "
        "version at boot, so a rotation needs a redeploy before the old secret is revoked."),
    Doc("d17", "CI build cache",
        "The dependency cache is keyed on the lockfile hash. A cache hit takes 20 seconds; a "
        "miss takes about four minutes, which is why lockfile churn is expensive."),
    Doc("d18", "Intermittent test failures",
        "A test that fails intermittently is quarantined, never retried in place. Retries hide "
        "the race condition that will eventually reach production at the worst moment."),
    Doc("d19", "Billing webhooks",
        "Payment providers deliver webhooks at least once. Every handler must be idempotent on "
        "the provider event id, or a retry double-charges the customer."),
    Doc("d20", "Currency rounding",
        "Amounts are stored in minor units as integers. Round half-up exactly once, at "
        "presentation time, and never at each intermediate step of a calculation."),
    Doc("d21", "Failed payment recovery",
        "A failed charge starts a dunning sequence with retries on days one, three and seven "
        "before the subscription is downgraded to the free tier."),
    Doc("d22", "Issuing refunds",
        "Refunds use the same idempotency path as charges. A partial refund cannot exceed the "
        "captured amount, and a refund after a chargeback is blocked automatically."),
    Doc("d23", "Deletion requests",
        "A verified erasure request must remove personal data from the primary store, the "
        "search index and the backups within 30 days. Backups age out on their own schedule."),
    Doc("d24", "Customer data export",
        "Exports stream as newline-delimited JSON. Large exports are delivered as signed URLs "
        "that stay valid for 24 hours and are single-use."),
    Doc("d25", "Redacting PII in logs",
        "The logger redacts email, phone and card fields before shipping. Redaction happens "
        "inside the process, never in the log pipeline, because the pipeline sees everything."),
    Doc("d26", "Quarterly access reviews",
        "Managers certify their team's permissions every quarter. Unreviewed grants expire "
        "automatically after 14 days, which is deliberate: silence is denial."),
    Doc("d27", "API versioning",
        "A breaking change requires a new major version path. Deprecated versions are supported "
        "for 12 months, after which they return 410 Gone with a migration link."),
    Doc("d28", "Pagination",
        "Cursor pagination is required for collections above 1000 items. Offset pagination "
        "drifts whenever a row is inserted, and duplicates rows the client already saw."),
    Doc("d29", "Idempotency keys",
        "Clients send an Idempotency-Key header. The server stores the first response for 24 "
        "hours and replays it for duplicates instead of performing the work twice."),
    Doc("d30", "Outbound webhook retries",
        "Delivery retries with exponential backoff for 24 hours. After that the endpoint is "
        "marked failing and the owner is notified, with no further attempts made."),
    Doc("d31", "Rate limit headers",
        "Responses include X-RateLimit-Remaining and X-RateLimit-Reset so a client can pace "
        "itself instead of bouncing off a 429 and guessing at the delay."),
    Doc("d32", "Mobile push notifications",
        "Push tokens expire silently. A stale token returns unregistered and must be pruned "
        "from the device table, otherwise every send wastes a round trip."),
    Doc("d33", "Email deliverability",
        "Authenticate sending domains with SPF and DKIM. A domain without DMARC alignment "
        "lands in spam at the major consumer providers regardless of content quality."),
    Doc("d34", "SMS fallback",
        "When push is unavailable, fall back to SMS only for transactional alerts. Promotional "
        "SMS requires explicit consent and is a legal problem, not a product decision."),
    Doc("d35", "Search relevance",
        "Ranking blends lexical match with recency. A document that matches the phrase exactly "
        "outranks one that matches many terms loosely, which is why phrase boosts matter."),
    Doc("d36", "Embedding index refresh",
        "The index rebuilds hourly. Documents written after the last rebuild are invisible to "
        "semantic search until the next cycle completes, usually within the hour."),
    Doc("d37", "Vector store sizing",
        "Each vector is 1536 dimensions at float32, about 6 KB. Budget memory before choosing "
        "the replica count; replicas are cheap to add and expensive to run."),
    Doc("d38", "Chunking documents",
        "Chunk on headings, then on paragraphs, with 15 percent overlap. Chunks below 200 "
        "tokens lose context and chunks above 800 dilute the match with irrelevant text."),
    Doc("d39", "Prompt caching",
        "Stable prefixes are cached for five minutes. Put the long instructions first and the "
        "variable question last, or nothing is reused and you pay full price every call."),
    Doc("d40", "Model fallback",
        "When the primary model returns a 5xx three times in a row the router falls back to "
        "the secondary and marks the primary degraded for ten minutes."),
)

QUERIES: tuple[Query, ...] = (
    Query("q01", "sign-in keeps failing for users going through the identity provider", "d01"),
    Query("q02", "how often should we roll the identity signing certificate", "d02"),
    Query("q03", "callers are being throttled after a short burst", "d03"),
    Query("q04", "what should a client do when it receives a 429", "d04"),
    Query("q05", "how long do nightly database dumps stick around", "d05"),
    Query("q06", "bring a database back to an earlier point in time", "d06"),
    Query("q07", "undo a release that broke production", "d07"),
    Query("q08", "cleaning up toggles nobody removed", "d08"),
    Query("q09", "replica promotion lost in-flight transactions", "d09"),
    Query("q10", "redis evicting session keys and logging users out", "d10"),
    Query("q11", "consumers far behind the topic", "d11"),
    Query("q12", "when does the internal certificate expire", "d12"),
    Query("q13", "lower the ttl before moving a host", "d13"),
    Query("q14", "flush the edge cache by tag", "d14"),
    Query("q15", "how long are audit entries kept", "d15"),
    Query("q16", "rotate credentials without downtime", "d16"),
    Query("q17", "build is slow after a dependency change", "d17"),
    Query("q18", "intermittent test failures, should we retry them", "d18"),
    Query("q19", "duplicate payment notifications charged twice", "d19"),
    Query("q20", "rounding pennies on an invoice total", "d20"),
    Query("q21", "recovering customers with failed charges", "d21"),
    Query("q22", "give money back partially", "d22"),
    Query("q23", "erase a customer when they ask", "d23"),
    Query("q24", "download everything a tenant has", "d24"),
    Query("q25", "keep emails and phone numbers out of logs", "d25"),
    Query("q26", "who certifies permissions every quarter", "d26"),
    Query("q27", "deprecating an old api version", "d27"),
    Query("q28", "listing a huge collection without duplicates", "d28"),
    Query("q29", "client retrying the same charge twice", "d29"),
    Query("q30", "deliveries failing to a customer endpoint", "d30"),
)

# Real systems carry a synonym table, and so must yours. Query language rarely
# matches document language, and no amount of term counting closes that gap.
ALIASES: dict[str, tuple[str, ...]] = {
    "sso": ("single sign-on", "saml", "identity provider", "sign-in", "signin", "login"),
    "sign-in": ("login", "sign in", "single sign-on"),
    "throttle": ("rate limit", "429", "quota"),
    "throttled": ("rate limit", "429"),
    "429": ("rate limit", "throttle"),
    "undo": ("revert", "rollback", "roll back"),
    "revert": ("rollback", "undo"),
    "rollback": ("revert", "undo"),
    "release": ("deploy", "deployment"),
    "production": ("prod",),
    "behind": ("lag",),
    "lag": ("behind",),
    "flush": ("purge",),
    "purge": ("flush",),
    "tls": ("certificate", "cert"),
    "cert": ("certificate", "tls"),
    "credentials": ("secrets", "secret"),
    "dumps": ("backup", "backups"),
    "dump": ("backup",),
    "toggle": ("flag", "flags"),
    "toggles": ("flags", "flag"),
    "erase": ("delete", "erasure", "deletion"),
    "deleted": ("erasure", "deletion"),
    "refund": ("money back", "charge back"),
    "spam": ("deliverability", "dmarc"),
    "penny": ("rounding", "minor units"),
    "pennies": ("rounding", "minor units"),
    "download": ("export", "exports"),
    "tenant": ("customer", "account"),
    "cleanup": ("stale", "remove"),
    "cleaning": ("cleanup", "stale"),
    "certifies": ("certify", "review", "approve"),
    "partially": ("partial",),
    "ask": ("request", "erasure"),
}


def documents() -> list[Doc]:
    return list(DOCS)


def corpus() -> list[Query]:
    return list(QUERIES)
