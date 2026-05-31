"""Governance policy for dynamic knowledge sources.

The first version is deliberately lightweight: it does not schedule crawls, but
it gives every dynamic source a policy decision before collection and writes the
decision into metadata so later retrieval can reason about source quality.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from urllib.parse import urlparse

from .record import KnowledgeReliability, KnowledgeTimeSensitivity

SourceType = Literal["web_page", "rss_feed"]


class SourceGovernanceError(ValueError):
    """Raised when a dynamic knowledge source violates governance policy."""


@dataclass(frozen=True, slots=True)
class DataSourceRule:
    """Policy rule for a trusted or constrained source domain."""

    name: str
    domains: tuple[str, ...]
    source_types: tuple[SourceType, ...] = ("web_page", "rss_feed")
    default_category: str | None = None
    reliability: KnowledgeReliability = "medium"
    time_sensitivity: KnowledgeTimeSensitivity = "high"
    enabled: bool = True
    max_items_per_collect: int | None = None
    min_refresh_interval_minutes: int | None = None
    trust_score: float | None = None
    allowed_path_prefixes: tuple[str, ...] = ()
    blocked_path_keywords: tuple[str, ...] = ()
    notes: str = ""


@dataclass(frozen=True, slots=True)
class SourceGovernanceDecision:
    """Decision returned by source governance before collection."""

    source_url: str
    source_type: SourceType
    domain: str
    rule_name: str
    category: str
    reliability: KnowledgeReliability
    time_sensitivity: KnowledgeTimeSensitivity
    trust_score: float
    max_items_per_collect: int | None = None
    min_refresh_interval_minutes: int | None = None
    notes: str = ""

    def metadata(self) -> dict[str, object]:
        """Return metadata fields that should travel with collected records."""
        return {
            "source_domain": self.domain,
            "source_rule": self.rule_name,
            "source_type": self.source_type,
            "source_reliability": self.reliability,
            "source_time_sensitivity": self.time_sensitivity,
            "source_trust_score": self.trust_score,
            "source_min_refresh_interval_minutes": self.min_refresh_interval_minutes,
            "source_governance_notes": self.notes,
        }


@dataclass(slots=True)
class DynamicSourceGovernancePolicy:
    """Evaluate dynamic source URLs against allow/block rules."""

    rules: tuple[DataSourceRule, ...] = field(default_factory=tuple)
    blocked_domains: tuple[str, ...] = field(default_factory=tuple)
    allowed_domains: tuple[str, ...] = field(default_factory=tuple)
    allow_unregistered_sources: bool = True
    default_reliability: KnowledgeReliability = "medium"
    default_time_sensitivity: KnowledgeTimeSensitivity = "high"
    default_trust_score: float = 0.5

    def evaluate(
        self,
        source_url: str,
        *,
        source_type: SourceType,
        category: str,
    ) -> SourceGovernanceDecision:
        """Validate and classify a dynamic source URL."""
        domain = normalize_domain(source_url)
        parsed = urlparse(source_url)
        if self._matches_any_domain(domain, self.blocked_domains):
            raise SourceGovernanceError(f"Source domain is blocked by policy: {domain}")

        if self.allowed_domains and not self._matches_any_domain(domain, self.allowed_domains):
            raise SourceGovernanceError(f"Source domain is not in the allowlist: {domain}")

        rule = self._matching_rule(domain, source_type)
        if rule is None:
            if not self.allow_unregistered_sources:
                raise SourceGovernanceError(f"Source domain has no registered rule: {domain}")
            return SourceGovernanceDecision(
                source_url=source_url,
                source_type=source_type,
                domain=domain,
                rule_name="unregistered_source",
                category=category,
                reliability=self.default_reliability,
                time_sensitivity=self.default_time_sensitivity,
                trust_score=self.default_trust_score,
                notes="No registered source rule matched; default governance applied.",
            )

        if not rule.enabled:
            raise SourceGovernanceError(f"Source rule is disabled: {rule.name}")
        self._validate_path_rules(parsed.path or "/", rule)

        return SourceGovernanceDecision(
            source_url=source_url,
            source_type=source_type,
            domain=domain,
            rule_name=rule.name,
            category=rule.default_category or category,
            reliability=rule.reliability,
            time_sensitivity=rule.time_sensitivity,
            trust_score=rule.trust_score
            if rule.trust_score is not None
            else reliability_to_trust_score(rule.reliability),
            max_items_per_collect=rule.max_items_per_collect,
            min_refresh_interval_minutes=rule.min_refresh_interval_minutes,
            notes=rule.notes,
        )

    def _matching_rule(self, domain: str, source_type: SourceType) -> DataSourceRule | None:
        for rule in self.rules:
            if source_type not in rule.source_types:
                continue
            if self._matches_any_domain(domain, rule.domains):
                return rule
        return None

    def _matches_any_domain(self, domain: str, candidates: tuple[str, ...]) -> bool:
        return any(domain_matches(domain, candidate) for candidate in candidates)

    def _validate_path_rules(self, path: str, rule: DataSourceRule) -> None:
        normalized_path = path.lower()
        if rule.allowed_path_prefixes and not any(
            normalized_path.startswith(prefix.lower()) for prefix in rule.allowed_path_prefixes
        ):
            raise SourceGovernanceError(
                f"Source path is outside allowed prefixes for rule {rule.name}: {path}"
            )
        for keyword in rule.blocked_path_keywords:
            if keyword.lower() in normalized_path:
                raise SourceGovernanceError(
                    f"Source path contains a blocked keyword for rule {rule.name}: {keyword}"
                )


def normalize_domain(source_url: str) -> str:
    """Extract a normalized domain from an HTTP(S) source URL."""
    parsed = urlparse(source_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise SourceGovernanceError("Governed sources must be http(s) URLs with a host.")
    return parsed.hostname.lower() if parsed.hostname else parsed.netloc.lower()


def domain_matches(domain: str, candidate: str) -> bool:
    """Return whether a domain matches a root domain or one of its subdomains."""
    normalized_candidate = candidate.lower().strip()
    if not normalized_candidate:
        return False
    return domain == normalized_candidate or domain.endswith(f".{normalized_candidate}")


def reliability_to_trust_score(reliability: KnowledgeReliability) -> float:
    """Map coarse source reliability into a stable numeric trust signal."""
    return {
        "high": 0.9,
        "medium": 0.6,
        "low": 0.3,
    }[reliability]


DEFAULT_DYNAMIC_SOURCE_GOVERNANCE = DynamicSourceGovernancePolicy(
    rules=(
        DataSourceRule(
            name="official_sec_filings",
            domains=("sec.gov",),
            default_category="filing",
            reliability="high",
            time_sensitivity="medium",
            min_refresh_interval_minutes=60,
            notes="Official SEC source; prefer over reposted filing summaries.",
        ),
        DataSourceRule(
            name="example_demo_source",
            domains=("example.com",),
            max_items_per_collect=20,
            notes="Demo/test source used by local examples and tests.",
        ),
    )
)
