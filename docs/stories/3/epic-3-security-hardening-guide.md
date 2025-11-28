# Epic 3 - Security Hardening Guide per Uso Privato

**Data:** 2025-01-27  
**Epic:** Epic 3 - Streamlit UI Observability  
**Focus:** Protezione da attacchi esterni e controllo costi

---

## Obiettivo

Implementare protezioni multi-layer per prevenire:

1. **Accesso non autorizzato** alla Streamlit UI
2. **Abuse/DDoS** che generano costi OpenAI non controllati
3. **Cost explosion** da attacchi esterni

---

## Analisi Rischi Attuali

### Rischio 1: Streamlit UI Esposta Pubblicamente

**Scenario Critico:**

- Streamlit app esposta su internet senza autenticazione
- Attaccante trova URL e fa migliaia di query
- Costi OpenAI esplosivi ($100+/giorno possibili)

**Protezioni Attuali:**

- ❌ Nessuna autenticazione
- ❌ Nessun rate limiting Streamlit nativo
- ❌ Nessun cost threshold enforcement
- ✅ RLS Supabase (protegge solo DB, non Streamlit UI)

**Gap di Sicurezza:** **ALTO** - Streamlit UI completamente esposta

### Rischio 2: Cost Monitoring Passivo

**Scenario:**

- Attaccante fa query costose senza essere rilevato
- Costi accumulati scoperti solo a fine mese
- Nessun alert real-time

**Protezioni Attuali:**

- ✅ LangFuse tracking costi (Epic 2)
- ❌ Nessun alert automatico su threshold
- ❌ Nessun cost limit enforcement

**Gap di Sicurezza:** **MEDIO** - Monitoring presente ma senza enforcement

### Rischio 3: Network Exposure

**Scenario:**

- Streamlit esposto su porta pubblica (8501)
- Nessun firewall/IP whitelist
- Accessibile da qualsiasi IP

**Protezioni Attuali:**

- ❌ Nessuna configurazione network security documentata
- ❌ Nessun IP whitelist
- ❌ Nessun VPN requirement

**Gap di Sicurezza:** **ALTO** - Network completamente aperto

---

## Soluzioni di Sicurezza Multi-Layer

### Layer 1: Network Security (Priorità ALTA)

**Obiettivo:** Limitare accesso a livello network

#### Opzione A: VPN Only Access (Raccomandato per Uso Privato)

**Implementazione:**

1. **Deploy Streamlit su server privato** (non esposto su internet pubblico)
2. **VPN access required** per accedere al server
3. **Firewall rules:** Blocca porta 8501 da IP esterni

**Configurazione Firewall (Linux):**

```bash
# UFW (Ubuntu/Debian)
sudo ufw allow from <your-vpn-ip-range> to any port 8501
sudo ufw deny 8501

# O solo localhost (più restrittivo)
sudo ufw allow from 127.0.0.1 to any port 8501
sudo ufw deny 8501
```

**Configurazione Streamlit (`app.py` o `.streamlit/config.toml`):**

```python
# app.py - Bind solo a localhost o VPN interface
import streamlit as st

# In produzione, bind solo a localhost
# Accesso via SSH tunnel o VPN
```

**Streamlit Config (`.streamlit/config.toml`):**

```toml
[server]
address = "127.0.0.1"  # Solo localhost
port = 8501
enableCORS = false
enableXsrfProtection = true
```

**SSH Tunnel per Accesso Remoto:**

```bash
# Client: Crea tunnel SSH
ssh -L 8501:localhost:8501 user@your-server

# Poi accedi a http://localhost:8501
```

**Vantaggi:**

- ✅ Protezione completa a livello network
- ✅ Zero overhead applicativo
- ✅ Nessuna modifica codice necessaria
- ✅ Compatibile con uso privato

**Svantaggi:**

- ⚠️ Richiede VPN setup
- ⚠️ Accesso remoto più complesso

#### Opzione B: Reverse Proxy con IP Whitelist (Nginx)

**Implementazione:**

```nginx
# /etc/nginx/sites-available/streamlit
server {
    listen 80;
    server_name your-domain.com;

    # IP Whitelist
    allow 1.2.3.4;  # Your home IP
    allow 5.6.7.8;  # Your office IP
    deny all;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Vantaggi:**

- ✅ Accesso pubblico con IP whitelist
- ✅ Rate limiting possibile via Nginx
- ✅ SSL/TLS termination

**Svantaggi:**

- ⚠️ Richiede Nginx setup
- ⚠️ IP whitelist da mantenere aggiornata

---

### Layer 2: Rate Limiting Streamlit (Priorità MEDIA)

**Obiettivo:** Prevenire abuse anche se accesso ottenuto

#### Opzione A: Rate Limiting via Middleware Python

**Implementazione:**

```python
# utils/rate_limiter.py (NEW)
import time
from collections import defaultdict
from functools import wraps
import streamlit as st

class RateLimiter:
    """Simple in-memory rate limiter per Streamlit."""

    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)

    def check_rate_limit(self, identifier: str) -> bool:
        """Check if request should be allowed."""
        now = time.time()
        window_start = now - self.window_seconds

        # Clean old requests
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if req_time > window_start
        ]

        # Check limit
        if len(self.requests[identifier]) >= self.max_requests:
            return False

        # Record request
        self.requests[identifier].append(now)
        return True

# Global rate limiter
rate_limiter = RateLimiter(max_requests=20, window_seconds=60)

def rate_limit_decorator(func):
    """Decorator per rate limiting funzioni Streamlit."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Usa session_id come identifier (o IP se disponibile)
        identifier = st.session_state.get('session_id', 'default')

        if not rate_limiter.check_rate_limit(identifier):
            st.error("⚠️ Rate limit exceeded. Please wait before making another request.")
            st.stop()
            return None

        return func(*args, **kwargs)
    return wrapper
```

**Uso in `app.py`:**

```python
from utils.rate_limiter import rate_limit_decorator

@rate_limit_decorator
async def run_agent(user_input: str):
    # ... existing code ...
```

**Limitazioni:**

- ⚠️ In-memory (reset su restart)
- ⚠️ Non persistente tra istanze multiple
- ✅ Semplice da implementare
- ✅ Zero dipendenze aggiuntive

#### Opzione B: Rate Limiting via Redis (Più Robusto)

**Implementazione:**

```python
# utils/rate_limiter_redis.py (NEW)
import redis
import time
from functools import wraps
import streamlit as st

redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))

def rate_limit_redis(max_requests: int = 20, window_seconds: int = 60):
    """Rate limiting via Redis (persistente)."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            identifier = st.session_state.get('session_id', 'default')
            key = f"rate_limit:{identifier}"

            # Get current count
            current = redis_client.get(key)
            if current and int(current) >= max_requests:
                st.error("⚠️ Rate limit exceeded. Please wait.")
                st.stop()
                return None

            # Increment counter
            pipe = redis_client.pipeline()
            pipe.incr(key)
            pipe.expire(key, window_seconds)
            pipe.execute()

            return func(*args, **kwargs)
        return wrapper
    return decorator
```

**Vantaggi:**

- ✅ Persistente tra restart
- ✅ Funziona con multiple istanze
- ✅ Più robusto per produzione

**Svantaggi:**

- ⚠️ Richiede Redis setup
- ⚠️ Dipendenza aggiuntiva

---

### Layer 3: Cost Monitoring & Alerting (Priorità ALTA)

**Obiettivo:** Rilevare costi anomali in real-time

#### Implementazione: Cost Threshold Enforcement

**File: `utils/cost_monitor.py` (NEW)**

```python
"""
Cost monitoring e alerting per prevenire cost explosion.
"""
import os
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
import asyncio

logger = logging.getLogger(__name__)

class CostMonitor:
    """Monitor costi e blocca se threshold superato."""

    def __init__(
        self,
        daily_limit: Decimal = Decimal("10.00"),  # $10/giorno default
        hourly_limit: Decimal = Decimal("2.00"),  # $2/ora default
        alert_threshold: Decimal = Decimal("5.00")  # Alert a $5/giorno
    ):
        self.daily_limit = daily_limit
        self.hourly_limit = hourly_limit
        self.alert_threshold = alert_threshold

    async def check_daily_cost(self, session_id: str) -> tuple[bool, Decimal]:
        """Verifica costo giornaliero e restituisce (allowed, current_cost)."""
        from utils.db_utils import DatabasePool

        db = DatabasePool()
        await db.initialize()

        async with db.pool.acquire() as conn:
            # Calcola costo giornaliero
            result = await conn.fetchval("""
                SELECT COALESCE(SUM(cost), 0)
                FROM query_logs
                WHERE timestamp >= CURRENT_DATE
            """)

            current_cost = Decimal(str(result))
            allowed = current_cost < self.daily_limit

            if not allowed:
                logger.error(
                    f"🚨 DAILY COST LIMIT EXCEEDED: ${current_cost:.2f} "
                    f"(limit: ${self.daily_limit:.2f})"
                )

            if current_cost >= self.alert_threshold:
                logger.warning(
                    f"⚠️ COST ALERT: ${current_cost:.2f} oggi "
                    f"(threshold: ${self.alert_threshold:.2f})"
                )

            return allowed, current_cost

    async def check_hourly_cost(self, session_id: str) -> tuple[bool, Decimal]:
        """Verifica costo orario e restituisce (allowed, current_cost)."""
        from utils.db_utils import DatabasePool

        db = DatabasePool()
        await db.initialize()

        async with db.pool.acquire() as conn:
            result = await conn.fetchval("""
                SELECT COALESCE(SUM(cost), 0)
                FROM query_logs
                WHERE timestamp >= NOW() - INTERVAL '1 hour'
            """)

            current_cost = Decimal(str(result))
            allowed = current_cost < self.hourly_limit

            if not allowed:
                logger.error(
                    f"🚨 HOURLY COST LIMIT EXCEEDED: ${current_cost:.2f} "
                    f"(limit: ${self.hourly_limit:.2f})"
                )

            return allowed, current_cost

    async def enforce_cost_limits(self, session_id: str) -> tuple[bool, str]:
        """Verifica tutti i limiti e restituisce (allowed, message)."""
        daily_allowed, daily_cost = await self.check_daily_cost(session_id)
        hourly_allowed, hourly_cost = await self.check_hourly_cost(session_id)

        if not daily_allowed:
            return False, (
                f"⚠️ Limite costo giornaliero superato: ${daily_cost:.2f} "
                f"(limite: ${self.daily_limit:.2f}). "
                f"Accesso bloccato per prevenire costi eccessivi."
            )

        if not hourly_allowed:
            return False, (
                f"⚠️ Limite costo orario superato: ${hourly_cost:.2f} "
                f"(limite: ${self.hourly_limit:.2f}). "
                f"Attendi prima di fare altre query."
            )

        return True, ""

# Global cost monitor
cost_monitor = CostMonitor(
    daily_limit=Decimal(os.getenv("COST_DAILY_LIMIT", "10.00")),
    hourly_limit=Decimal(os.getenv("COST_HOURLY_LIMIT", "2.00")),
    alert_threshold=Decimal(os.getenv("COST_ALERT_THRESHOLD", "5.00"))
)
```

**Integrazione in `app.py`:**

```python
from utils.cost_monitor import cost_monitor

async def run_agent(user_input: str):
    """Run the agent with cost limit enforcement."""

    # Check cost limits before processing
    session_id = st.session_state.get('session_id', 'default')
    allowed, message = await cost_monitor.enforce_cost_limits(session_id)

    if not allowed:
        st.error(message)
        st.stop()
        return None

    # ... existing agent code ...
```

**Variabili d'Ambiente:**

```env
# Cost Protection (Epic 3)
COST_DAILY_LIMIT=10.00      # Limite giornaliero $10
COST_HOURLY_LIMIT=2.00      # Limite orario $2
COST_ALERT_THRESHOLD=5.00   # Alert a $5/giorno
```

---

### Layer 4: Streamlit Authentication (Opzionale, se Network Security Non Sufficiente)

**Se VPN/Network security non è possibile, implementare auth minimale:**

**File: `utils/streamlit_auth.py` (NEW)**

```python
"""
Simple authentication per Streamlit (uso privato).
"""
import streamlit as st
import hashlib
import os

def check_password():
    """Verifica password semplice per uso privato."""

    def password_entered():
        """Check if password is correct."""
        password_hash = hashlib.sha256(
            st.session_state["password"].encode()
        ).hexdigest()

        # Password hash memorizzato in env (non plaintext)
        correct_hash = os.getenv("STREAMLIT_PASSWORD_HASH")

        if password_hash == correct_hash:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show password input
        st.text_input(
            "Password",
            type="password",
            on_change=password_entered,
            key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password incorrect
        st.text_input(
            "Password",
            type="password",
            on_change=password_entered,
            key="password"
        )
        st.error("Password incorrect")
        return False
    else:
        # Password correct
        return True
```

**Uso in `app.py`:**

```python
from utils.streamlit_auth import check_password

# All'inizio di app.py
if not check_password():
    st.stop()  # Blocca app se password errata
```

**Setup Password Hash:**

```bash
# Genera hash password
python -c "import hashlib; print(hashlib.sha256('your-password'.encode()).hexdigest())"

# Aggiungi a .env
STREAMLIT_PASSWORD_HASH=<generated-hash>
```

**Limitazioni:**

- ⚠️ Password semplice (non production-grade)
- ⚠️ Nessun session timeout
- ✅ Semplice da implementare
- ✅ Sufficiente per uso privato

---

### Layer 5: Supabase Security Hardening

**Protezioni già implementate:**

- ✅ RLS enabled su tutte le tabelle
- ✅ Policies `service_role` only per `sessions` e `query_logs`

**Protezioni aggiuntive consigliate:**

#### 1. SSL Enforcement PostgreSQL

**Se deployment pubblico:**

```bash
# Via Supabase Dashboard: Settings > Database > SSL Configuration
# Abilita "Enforce SSL on incoming connections"
```

**O via CLI:**

```bash
supabase ssl-enforcement --project-ref {ref} update --enable-db-ssl-enforcement
```

#### 2. IP Restrictions Supabase (Se Disponibile)

**Limita accesso database a IP specifici:**

- Supabase Dashboard: Settings > Database > Connection Pooling
- Configura IP whitelist se disponibile nel piano

#### 3. API Keys Rotation

**Best practice:**

- Ruota `service_role` key periodicamente (ogni 3-6 mesi)
- Genera nuova key in Supabase Dashboard
- Aggiorna `DATABASE_URL` con nuova password

---

## Checklist Sicurezza Completa

### Network Security

- [ ] **VPN Only Access** (Raccomandato)

  - [ ] Deploy Streamlit su server privato
  - [ ] Configura VPN per accesso remoto
  - [ ] Firewall: Blocca porta 8501 da IP esterni
  - [ ] Streamlit config: `address = "127.0.0.1"`

- [ ] **O Alternativa: Reverse Proxy con IP Whitelist**
  - [ ] Setup Nginx con IP whitelist
  - [ ] SSL/TLS termination
  - [ ] Rate limiting via Nginx

### Application Security

- [ ] **Rate Limiting Streamlit**

  - [ ] Implementare `utils/rate_limiter.py` (in-memory)
  - [ ] O `utils/rate_limiter_redis.py` (persistente)
  - [ ] Integrare in `app.py` con decorator

- [ ] **Cost Monitoring & Enforcement**

  - [ ] Implementare `utils/cost_monitor.py`
  - [ ] Configurare threshold in `.env`
  - [ ] Integrare check costi in `app.py`
  - [ ] Testare alert e blocking

- [ ] **Streamlit Authentication (Opzionale)**
  - [ ] Implementare `utils/streamlit_auth.py` se necessario
  - [ ] Generare password hash
  - [ ] Configurare in `.env`

### Supabase Security

- [ ] **RLS Verification**

  - [ ] Verificare RLS enabled su tutte le tabelle
  - [ ] Verificare policies `service_role` only
  - [ ] Test accesso `anon` role (dovrebbe fallire)

- [ ] **SSL Enforcement**

  - [ ] Abilitare SSL enforcement PostgreSQL se deployment pubblico
  - [ ] Verificare connessioni SSL

- [ ] **API Keys Security**
  - [ ] Verificare `service_role` key non esposta in frontend
  - [ ] Pianificare rotation periodica

### Monitoring & Alerting

- [ ] **Cost Monitoring**

  - [ ] Configurare LangFuse dashboard per cost tracking
  - [ ] Setup alert su costi anomali (> threshold)
  - [ ] Verificare cost breakdown per query

- [ ] **Logging Security Events**
  - [ ] Log rate limit violations
  - [ ] Log cost limit exceeded
  - [ ] Log access attempts sospetti

---

## Configurazione Raccomandata per Uso Privato

### Setup Minimale (Protezione Base)

```env
# Cost Protection
COST_DAILY_LIMIT=10.00
COST_HOURLY_LIMIT=2.00
COST_ALERT_THRESHOLD=5.00

# Streamlit Auth (opzionale)
STREAMLIT_PASSWORD_HASH=<sha256-hash>
```

**Implementazioni:**

1. ✅ Rate limiting in-memory (`utils/rate_limiter.py`)
2. ✅ Cost monitoring (`utils/cost_monitor.py`)
3. ✅ Network: VPN only o IP whitelist

### Setup Completo (Protezione Massima)

```env
# Cost Protection
COST_DAILY_LIMIT=10.00
COST_HOURLY_LIMIT=2.00
COST_ALERT_THRESHOLD=5.00

# Streamlit Auth
STREAMLIT_PASSWORD_HASH=<sha256-hash>

# Redis (per rate limiting persistente)
REDIS_URL=redis://localhost:6379
```

**Implementazioni:**

1. ✅ Rate limiting Redis (`utils/rate_limiter_redis.py`)
2. ✅ Cost monitoring con enforcement
3. ✅ Streamlit authentication
4. ✅ Network: VPN + Firewall
5. ✅ SSL enforcement PostgreSQL

---

## Priorità Implementazione

### Priorità ALTA (Implementare Subito)

1. **Network Security:**

   - VPN only access O IP whitelist
   - Firewall rules
   - Streamlit bind a localhost/VPN

2. **Cost Monitoring:**
   - `utils/cost_monitor.py` con enforcement
   - Threshold configurabili
   - Alert su costi anomali

### Priorità MEDIA (Implementare Dopo)

3. **Rate Limiting:**
   - `utils/rate_limiter.py` (in-memory)
   - O `utils/rate_limiter_redis.py` (persistente)
   - Integrazione in `app.py`

### Priorità BASSA (Opzionale)

4. **Streamlit Auth:**

   - Solo se network security non sufficiente
   - `utils/streamlit_auth.py` semplice

5. **SSL Enforcement PostgreSQL:**
   - Solo se deployment pubblico
   - Già configurato Supabase HTTP APIs

---

## Test di Sicurezza

### Test 1: Network Access

```bash
# Test: Tentativo accesso da IP esterno (dovrebbe fallire)
curl http://your-server:8501
# Risultato atteso: Connection refused o timeout
```

### Test 2: Rate Limiting

```python
# Test: Fare 21 query in 60 secondi
# Risultato atteso: 20° query ok, 21° bloccata
```

### Test 3: Cost Enforcement

```python
# Test: Superare threshold giornaliero
# Risultato atteso: Query bloccate con messaggio errore
```

### Test 4: RLS Protection

```sql
-- Test: Tentativo accesso via anon role
SET ROLE anon;
SELECT * FROM sessions;  -- Dovrebbe restituire 0 righe
SELECT * FROM query_logs;  -- Dovrebbe restituire 0 righe
RESET ROLE;
```

---

## Conclusione

**Protezioni Essenziali per Uso Privato:**

1. ✅ **Network Security** (VPN/IP whitelist) - **CRITICO**
2. ✅ **Cost Monitoring con Enforcement** - **CRITICO**
3. ✅ **Rate Limiting** - **IMPORTANTE**
4. ✅ **RLS Supabase** - **GIÀ IMPLEMENTATO**

**Con queste protezioni:**

- ✅ Accesso limitato a utenti autorizzati (VPN/IP whitelist)
- ✅ Costi controllati con threshold enforcement
- ✅ Abuse prevenuto con rate limiting
- ✅ Database protetto con RLS

**Rischio residuo:** **BASSO** con implementazione completa

---

**Documento creato per:** Security hardening Epic 3  
**Prossimi passi:** Implementare Layer 1 (Network) e Layer 3 (Cost Monitoring)
