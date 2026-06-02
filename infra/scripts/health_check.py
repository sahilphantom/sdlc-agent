import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

import httpx
import redis
import psycopg2
from qdrant_client import QdrantClient
from config.settings import settings


def check(name: str, fn) -> bool:
    try:
        fn()
        print(f"  ✅ {name}")
        return True
    except Exception as e:
        print(f"  ❌ {name}: {e}")
        return False


def run_health_checks():
    print("\n🔍 SDLC Agent — Infrastructure Health Check\n")
    results = []

    # Ollama
    results.append(check("Ollama", lambda:
                         httpx.get(f"{settings.ollama_host}/api/tags",
                                   timeout=5).raise_for_status()
                         ))

    # PostgreSQL
    results.append(check("PostgreSQL", lambda:
                         psycopg2.connect(settings.database_url).close()
                         ))

    # Redis
    results.append(check("Redis", lambda:
                         redis.from_url(settings.redis_url).ping()
                         ))

    # Qdrant
    results.append(check("Qdrant", lambda:
                         QdrantClient(
                             url=settings.qdrant_url).get_collections()
                         ))

    # Prometheus
    results.append(check("Prometheus", lambda:
                         httpx.get("http://localhost:9090/-/healthy",
                                   timeout=5).raise_for_status()
                         ))

    # Grafana
    results.append(check("Grafana", lambda:
                         httpx.get("http://localhost:3001/api/health",
                                   timeout=5).raise_for_status()
                         ))

    # Phoenix
    results.append(check("Arize Phoenix", lambda:
                         httpx.get("http://localhost:6006",
                                   timeout=5).raise_for_status()
                         ))

    passed = sum(results)
    total = len(results)
    print(
        f"\n{'✅ All' if passed == total else '⚠️ '}{passed}/{total} services healthy\n")
    return passed == total


if __name__ == "__main__":
    success = run_health_checks()
    exit(0 if success else 1)