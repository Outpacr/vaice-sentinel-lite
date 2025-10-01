# QEME Sentinel Lite - Regulatory Updates Integration (lite, quiet)
import os
import json
import hashlib
import urllib.request
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)
if not logger.handlers:
    # default quiet; override with REGULATORY_LOG_LEVEL=DEBUG if needed
    level = os.environ.get("REGULATORY_LOG_LEVEL", "WARNING").upper()
    logging.basicConfig(level=getattr(logging, level, logging.WARNING),
                        format="(regulatory) %(asctime)s %(levelname)s %(message)s")

@dataclass
class RegulatoryUpdate:
    source: str
    framework: str
    title: str
    impact_level: str  # "low", "medium", "high", "critical"
    detected_date: str
    url: str
    summary: str
    mkb_action_required: bool

def _send_mail(subject: str, body: str) -> None:
    host = os.getenv("SMTP_HOST"); port = int(os.getenv("SMTP_PORT", "25"))
    user = os.getenv("SMTP_USER");  pwd  = os.getenv("SMTP_PASS")
    sender = os.getenv("SMTP_FROM", "sentinel-lite@localhost")
    to = os.getenv("SMTP_TO")
    if not host or not to:
        return
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to
    msg.set_content(body)
    with smtplib.SMTP(host, port, timeout=10) as s:
        if user and pwd:
            s.starttls()
            s.login(user, pwd)
        s.send_message(msg)

class MKBRegulatoryChecker:
    def __init__(self, cache_hours: int = None):
        self.cache_hours = cache_hours if cache_hours is not None else int(os.environ.get("REGULATORY_CACHE_HOURS", "24"))
        self.cache_file = "data/regulatory_cache.json"
        self.sources = self._get_mkb_sources()

    def _get_mkb_sources(self) -> List[Dict]:
        return [
            {
                "name": "EU_AI_Act_Latest",
                "framework": "eu_ai_act",
                "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:52021PC0206",
                "type": "html",
                "mkb_keywords": ["sme", "small", "medium", "enterprise", "startup"]
            },
            {
                "name": "GDPR_EDPB_Guidelines",
                "framework": "gdpr",
                "url": "https://edpb.europa.eu/news/news_en",
                "type": "html",
                "mkb_keywords": ["small business", "sme", "practical", "guidance"]
            },
            {
                "name": "DNB_FinTech_Updates",
                "framework": "fintech",
                "url": "https://www.dnb.nl/en/sector-information/fintech/",
                "type": "html",
                "mkb_keywords": ["startup", "fintech", "innovation", "sandbox"]
            }
        ]

    def check_updates(self, refresh: bool = False) -> List[RegulatoryUpdate]:
        if not refresh:
            cached = self._load_cache()
            if cached and self._is_cache_valid(cached):
                logger.debug("using cached regulatory data")
                return [RegulatoryUpdate(**u) for u in cached.get("updates", [])]

        logger.debug("fetching fresh regulatory updates")
        updates: List[RegulatoryUpdate] = []
        for source in self.sources:
            try:
                req = urllib.request.Request(
                    source["url"],
                    headers={"User-Agent": "QEME-Sentinel-Lite/1.0"}
                )
                with urllib.request.urlopen(req, timeout=30) as response:
                    content_bytes = response.read()
                    try:
                        content = content_bytes.decode("utf-8")
                    except UnicodeDecodeError:
                        content = content_bytes.decode("latin-1", "replace")

                content_hash = hashlib.sha256(content.encode("utf-8", "ignore")).hexdigest()
                last_hash = self._get_last_hash(source["name"])
                if last_hash == content_hash:
                    continue  # no changes

                impact = self._analyze_mkb_impact(content, source)
                self._save_hash(source["name"], content_hash)

                if impact["level"] == "none":
                    continue

                updates.append(RegulatoryUpdate(
                    source=source["name"],
                    framework=source["framework"],
                    title=f"Update detected: {source['framework'].upper()}",
                    impact_level=impact["level"],
                    detected_date=datetime.now().isoformat(),
                    url=source["url"],
                    summary=impact["summary"],
                    mkb_action_required=impact["level"] in ["high", "critical"],
                ))
            except Exception as e:
                # lite behavior: quiet skip, details only in DEBUG
                logger.debug(f"skip source {source.get('name')}: {e}")
                continue

        self._save_cache(updates)

        # mail als kritisch
        critical = [u for u in updates if u.impact_level == "critical"]
        if critical:
            lines = [f"- [{u.framework.upper()}] {u.title} -> {u.url}" for u in critical]
            _send_mail(
                subject="🚨 qeme sentinel lite: kritieke regulatory update",
                body="er zijn kritieke wijzigingen gedetecteerd:\n\n" + "\n".join(lines)
            )
        return updates

    def _analyze_mkb_impact(self, content: str, source: Dict) -> Dict:
        clower = content.lower()
        mkb_matches = sum(1 for kw in source.get("mkb_keywords", []) if kw.lower() in clower)
        urgent_keywords = ["immediate", "urgent", "deadline", "mandatory", "required", "compliance", "enforcement", "penalty", "fine"]
        urgent_matches = sum(1 for kw in urgent_keywords if kw in clower)
        if urgent_matches >= 3:
            level, summary = "critical", "kritieke wijzigingen gedetecteerd - directe actie vereist"
        elif urgent_matches >= 2 or mkb_matches >= 2:
            level, summary = "high", "belangrijke wijzigingen - beoordeling binnen 2 weken"
        elif urgent_matches >= 1 or mkb_matches >= 1:
            level, summary = "medium", "nieuwe ontwikkelingen - monitoring aanbevolen"
        elif any(w in clower for w in ["update", "new", "amended"]):
            level, summary = "low", "algemene updates gedetecteerd"
        else:
            level, summary = "none", "geen relevante wijzigingen voor mkb"
        return {"level": level, "summary": summary, "mkb_matches": mkb_matches, "urgent_matches": urgent_matches}

    def _load_cache(self) -> Optional[Dict]:
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.debug(f"cache load error: {e}")
        return None

    def _save_cache(self, updates: List[RegulatoryUpdate]) -> None:
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump({"timestamp": datetime.now().isoformat(),
                           "updates": [u.__dict__ for u in updates]}, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.debug(f"cache save error: {e}")

    def _is_cache_valid(self, cache_data: Dict) -> bool:
        try:
            cache_time = datetime.fromisoformat(cache_data["timestamp"])
            return datetime.now() - cache_time < timedelta(hours=self.cache_hours)
        except Exception:
            return False

    def _get_last_hash(self, source_name: str) -> Optional[str]:
        hash_file = f"data/hashes/{source_name}.hash"
        try:
            if os.path.exists(hash_file):
                with open(hash_file, "r", encoding="utf-8") as f:
                    return f.read().strip()
        except Exception:
            pass
        return None

    def _save_hash(self, source_name: str, content_hash: str) -> None:
        hash_file = f"data/hashes/{source_name}.hash"
        try:
            os.makedirs(os.path.dirname(hash_file), exist_ok=True)
            with open(hash_file, "w", encoding="utf-8") as f:
                f.write(content_hash)
        except Exception as e:
            logger.debug(f"hash save error: {e}")
