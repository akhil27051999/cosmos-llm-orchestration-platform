# -*- coding: utf-8 -*-
import base64, json, os

LOGO_DIR = "logos"
def logo_uri(name):
    p = os.path.join(LOGO_DIR, name + ".svg")
    if not os.path.exists(p): return None
    b = base64.b64encode(open(p,"rb").read()).decode()
    return "data:image/svg+xml;base64," + b

# ---------------- DATA ----------------
# component: (id, name, logo|None, glyph|None, path_order|0, what, role, why, pros[], cons[])
def C(id,name,logo,glyph,path,what,role,why,pros,cons):
    return dict(id=id,name=name,logo=logo,glyph=glyph,path=path,what=what,role=role,why=why,pros=pros,cons=cons)

LAYERS = [
 dict(key="edge",name="Client & Edge",color="#5CC8E0",icon="🌐",role="ingress · TLS · protection",cross=False,components=[
   C("cloudflare","Cloudflare CDN","cloudflare",None,1,
     "A global content-delivery & edge network with 300+ locations worldwide.",
     "Serves cached content close to users and absorbs traffic before it hits our servers.",
     "Massive free tier, built-in DDoS protection and WAF, and very low latency.",
     ["Global edge = fast for everyone","Built-in DDoS + bot protection","Cheap / generous free tier"],
     ["One more vendor to manage","Cache invalidation needs care"]),
   C("waf","AWS WAF","amazonwebservices",None,2,
     "A Web Application Firewall that inspects incoming HTTP requests.",
     "Blocks malicious requests (SQL injection, bad bots) before they reach the app.",
     "Fully managed, ships with common attack rule-sets, integrates with our AWS load balancer.",
     ["Managed OWASP rule-sets","Blocks attacks at the edge"],
     ["Per-rule cost","Needs tuning to avoid false blocks"]),
   C("ingress","Ingress controller","nginx",None,3,
     "A reverse proxy that is the single front door into the Kubernetes cluster.",
     "Routes each incoming request to the correct internal service by host/path, terminating TLS.",
     "Nginx ingress is mature, battle-tested and flexible.",
     ["Mature & flexible routing","Central place for TLS & rules"],
     ["A choke point to scale & secure carefully"]),
   C("dns","Route 53 · DNS","amazonwebservices",None,0,
     "Amazon's managed DNS service.",
     "Turns our domain name into the IP address of the load balancer, with health-based failover.",
     "AWS-native, supports latency/geo routing and health checks for multi-region.",
     ["Health-checked failover","Latency & geo routing"],
     ["Ties DNS to AWS"]),
   C("tls","cert-manager / ACM","kubernetes","🔒",0,
     "Automated TLS-certificate issuance and renewal.",
     "Gives every endpoint HTTPS and auto-renews certs so they never expire.",
     "Automates free ACME/Let's Encrypt certs inside the cluster — no manual renewals.",
     ["Auto-renew = no expiry outages","Free certificates"],
     ["Depends on the cluster & DNS setup"]),
 ]),
 dict(key="present",name="Presentation",color="#A99BFF",icon="🖥️",role="dashboard · live view",cross=False,components=[
   C("frontend","Next.js · React · TypeScript","react",None,4,
     "The web dashboard, built with React + Next.js and typed with TypeScript.",
     "Where users submit jobs, watch progress live, and view queue / health / usage.",
     "Server-side rendering, great developer experience, and types that catch bugs early.",
     ["Fast, SEO-friendly rendering","Types prevent whole classes of bugs","Huge ecosystem"],
     ["Build tooling is complex","Frontend churn"]),
   C("sse","SSE live stream","react","📡",0,
     "Server-Sent Events — a one-way live stream over plain HTTP.",
     "Pushes the agent's thinking to the browser token-by-token as it happens.",
     "Simpler than WebSockets when you only need server→browser streaming.",
     ["Simple, HTTP-native, auto-reconnect"],
     ["One-way only","Browser connection limits"]),
 ]),
 dict(key="gateway",name="API Gateway",color="#F2B24A",icon="🚪",role="accept · authenticate · meter",cross=False,components=[
   C("fastapi","FastAPI gateway","fastapi",None,5,
     "An async Python web framework serving as the platform's front door.",
     "Accepts a job and instantly returns 202 + a job id, so the user never waits.",
     "Async-native (handles many requests at once), typed via Pydantic, auto-generates API docs.",
     ["Very fast & async","Typed request validation","Auto OpenAPI docs"],
     ["Requires async discipline","Younger than Django/Flask"]),
   C("idem","Idempotency + OCC","fastapi","🔁",0,
     "Idempotency keys plus optimistic concurrency control.",
     "Makes retries safe (no double-processing) and prevents two writers from clobbering data.",
     "Clients and networks retry automatically — the system must never act twice on one request.",
     ["Safe retries","No lost updates"],
     ["Extra key storage & careful design"]),
   C("keycloak","Keycloak · OAuth2/OIDC/JWT","keycloak2",None,6,
     "An open-source identity provider speaking OAuth2 / OIDC / JWT.",
     "Authenticates every caller and issues tokens that say what they're allowed to do.",
     "Full-featured, standards-based, self-hosted — no per-user SaaS fees.",
     ["Industry-standard auth","No per-user cost","Self-hosted control"],
     ["Heavier to operate yourself"]),
   C("quota","Quotas + usage ledger","fastapi","📊",0,
     "Per-tenant rate/usage limits plus an append-only usage record.",
     "Stops one customer starving the others and records usage for billing.",
     "Multi-tenant fairness and accurate billing both need it.",
     ["Fair sharing","Billing-grade usage data"],
     ["Accounting adds complexity"]),
 ]),
 dict(key="control",name="Control plane",color="#E8C15A",icon="🎛️",role="routing · experiments · provisioning",cross=False,components=[
   C("registry","Provider registry & selector","fastapi","🧭",7,
     "A live registry of available LLM providers plus a routing strategy.",
     "Picks a healthy provider for each job (round-robin / weighted / least-loaded).",
     "We need to route, weight and fail over between providers at runtime, not in code.",
     ["Flexible routing","Easy failover"],
     ["Must track provider health accurately"]),
   C("flags","Experimentation / feature flags","fastapi","🧪",0,
     "An A/B-testing framework with feature flags.",
     "Rolls a new agent config or model out to a small % of traffic and measures results.",
     "Lets us change the product with data and roll back instantly if a metric drops.",
     ["Safe, measurable rollouts","Instant rollback"],
     ["Flag sprawl","Needs statistical rigor"]),
   C("operator","Preview-env provisioner (Operator)","kubernetes",None,0,
     "A custom Kubernetes Operator + CRD we write ourselves.",
     "Spins up and tears down isolated per-tenant environments on demand.",
     "Automates what would otherwise be manual, error-prone ops work.",
     ["Self-service environments","Consistent & repeatable"],
     ["Real engineering effort to build"]),
 ]),
 dict(key="resil",name="Resilience layer",color="#F0623C",icon="🛡️",role="wraps every provider call",cross=False,components=[
   C("ratelimit","Rate limiter","redis","🚦",8,
     "A token-bucket limiter backed by Redis + Lua.",
     "Keeps our call rate within each provider's limits so we're never throttled or banned.",
     "Providers enforce hard rate limits; we must self-regulate across many workers.",
     ["Protects providers","Fair distributed limiting"],
     ["Distributed counting is tricky"]),
   C("breaker","Circuit breaker","redis","⚡",9,
     "A breaker with closed / open / half-open states.",
     "Stops hammering a provider that's already failing, then probes to see if it recovered.",
     "Fail fast instead of piling requests onto a broken dependency.",
     ["Prevents cascading failures","Auto-recovery probing"],
     ["Thresholds need tuning"]),
   C("retry","Retry + backoff + jitter","redis","🔄",0,
     "Smart retries that wait longer each time, with randomness (jitter).",
     "Recovers from brief, transient errors without all workers retrying in sync.",
     "Networks blip; naive retries cause a stampede — jitter spreads them out.",
     ["Higher success rate","Avoids thundering herd"],
     ["Can amplify load if misconfigured"]),
   C("fallback","Fallback chain","redis","🪂",0,
     "An ordered list of backup providers.",
     "If the primary fails, quietly try the next one so the user still gets an answer.",
     "Keeps the service useful during a partial outage.",
     ["Graceful degradation"],
     ["Can hide root causes — use carefully"]),
   C("shed","Load shedding","redis","🚰",0,
     "Deliberately dropping excess requests under overload.",
     "Protects the system so it stays up for most users instead of collapsing for all.",
     "Partial service beats total meltdown when demand exceeds capacity.",
     ["System stays alive under spikes"],
     ["Some requests are rejected"]),
 ]),
 dict(key="event",name="Event backbone",color="#5FD08A",icon="📨",role="durable · decoupled · replayable",cross=False,components=[
   C("kafka","Kafka / Redpanda","kafka",None,10,
     "A distributed, durable event log (Redpanda is a drop-in Kafka).",
     "The queue that decouples the fast gateway from the slower workers; jobs wait here safely.",
     "Durable, ordered, replayable and high-throughput — the backbone of event-driven systems.",
     ["Durable & replayable","Scales to huge throughput","Decouples producers/consumers"],
     ["Operationally complex"]),
   C("schema","Schema Registry","kafka","📐",0,
     "A registry of versioned event schemas.",
     "Lets producers and consumers evolve message formats without breaking each other.",
     "In a big system, message shapes change — this makes that safe.",
     ["Safe schema evolution","Contract enforcement"],
     ["Extra infrastructure"]),
   C("outbox","Outbox pattern","kafka","📤",0,
     "A transactional outbox table + relay.",
     "Publishes an event in the same DB transaction as the data write — no lost or duplicate events.",
     "Guarantees the database and the event stream never disagree.",
     ["Strong consistency"],
     ["Extra table + relay process"]),
   C("dlq","Dead-letter queue","kafka","☠️",0,
     "A side queue for messages that repeatedly fail.",
     "Parks poison messages so one bad job doesn't block the whole stream.",
     "Keeps the pipeline flowing while preserving failures for later inspection.",
     ["Isolates poison messages"],
     ["Needs monitoring & replay tooling"]),
   C("cdc","Debezium · CDC","kafka","🔗",0,
     "Change-Data-Capture that tails the database's change log.",
     "Streams every DB change into the analytics warehouse in real time.",
     "Gets analytics data without risky dual-writes from the app.",
     ["Real-time, decoupled analytics"],
     ["Connectors add ops overhead"]),
 ]),
 dict(key="worker",name="Worker fleet · Go",color="#F2913D",icon="⚙️",role="the agent runtime",cross=False,components=[
   C("go","Go workers","go",None,11,
     "The worker service that does the heavy lifting, written in Go.",
     "Pulls jobs off Kafka and runs the agent to completion, many at once.",
     "Go's goroutines make massive concurrency cheap; binaries are tiny and fast.",
     ["Cheap concurrency","Fast & low memory","Tiny container images"],
     ["A new language to learn"]),
   C("agentloop","Agent loop","anthropic",None,12,
     "The plan → act → observe reasoning cycle.",
     "The core routine that lets the model break a goal into steps and solve it.",
     "This IS the product — an autonomous, tool-using agent.",
     ["Autonomous problem-solving","Uses tools & data"],
     ["Can loop or overspend if unbounded"]),
   C("tools","Tool / function calling","anthropic","🛠️",0,
     "Structured 'function calling' the model can invoke.",
     "Lets the agent take real actions (search, fetch, compute), not just talk.",
     "Bridges the model's reasoning to the outside world.",
     ["Turns text into real actions"],
     ["Inputs must be validated for safety"]),
   C("budget","Token budget","anthropic","🎟️",0,
     "A cap on tokens (and thus cost/time) per job.",
     "Bounds how much a single job can spend before it must stop.",
     "LLM calls cost real money — runaway agents must be contained.",
     ["Predictable cost","Prevents runaways"],
     ["May cut off long tasks"]),
   C("rag","RAG retrieval","postgresql","🔍",0,
     "Retrieval-Augmented Generation over your own data.",
     "Finds relevant documents by meaning and feeds them to the model for grounded answers.",
     "Cuts hallucinations and keeps answers current without retraining.",
     ["Grounded, up-to-date answers"],
     ["Only as good as the retrieval"]),
   C("grpc","gRPC + Protobuf","grpc",None,0,
     "A fast, typed remote-procedure-call system.",
     "How internal services call each other efficiently with strict contracts.",
     "Faster and stricter than REST for internal, high-volume service calls.",
     ["Fast binary protocol","Typed contracts","Streaming"],
     ["Not human-readable; extra tooling"]),
   C("istio","Istio service mesh","istio",None,0,
     "A service mesh that sits beside every service.",
     "Adds mutual-TLS encryption and traffic control between services without app code.",
     "Security and traffic-shaping handled by the platform, not each app.",
     ["mTLS everywhere","Canary & retries at mesh level","Free observability"],
     ["Adds complexity & overhead"]),
 ]),
 dict(key="provider",name="LLM providers",color="#EAB94C",icon="🤖",role="the intelligence",cross=False,components=[
   C("claude","Anthropic Claude API","anthropic",None,13,
     "The large language model that powers the agents.",
     "Does the actual reasoning and tool-use for every job (Messages API).",
     "Strong tool-use, long context and reliable reasoning — ideal for agents.",
     ["Excellent tool-use & reasoning","Long context window"],
     ["External cost & latency","Provider rate limits"]),
 ]),
 dict(key="storage",name="Storage plane · polyglot",color="#3EB6A0",icon="🗄️",role="right store for each data shape",cross=False,components=[
   C("postgres","PostgreSQL","postgresql",None,14,
     "A rock-solid relational (SQL) database.",
     "The source of truth for jobs, tenants, quotas and the billing ledger.",
     "ACID guarantees, decades of maturity, plus JSON and extensions when needed.",
     ["Reliable & consistent","Extremely versatile"],
     ["Write-scaling needs planning"]),
   C("mongo","MongoDB","mongodb",None,0,
     "A document (NoSQL) database.",
     "Stores variable-shaped agent trajectories and payloads that don't fit tidy tables.",
     "Flexible schema is perfect for deeply-nested, evolving agent data.",
     ["Flexible schema","Fast document reads"],
     ["Weaker multi-document transactions"]),
   C("redis","Redis","redis",None,0,
     "An in-memory data store.",
     "Cache, hot state, and the counters behind rate-limiting and circuit-breaking.",
     "Microsecond latency for the things that must be instant.",
     ["Blazing fast","Very versatile"],
     ["Memory-bound","Durability trade-offs"]),
   C("vector","pgvector / Qdrant","qdrant",None,0,
     "A vector database for embeddings.",
     "Stores the numeric 'meaning' of documents so RAG can find similar ones.",
     "Enables semantic (meaning-based) search, not just keyword match.",
     ["Semantic similarity search"],
     ["Index tuning & memory cost"]),
   C("s3","S3 / MinIO","minio",None,0,
     "Object storage (MinIO is S3-compatible, self-hosted).",
     "Holds large artifacts and long-term archives cheaply.",
     "Effectively infinite, durable and inexpensive for blobs.",
     ["Cheap, durable, scalable"],
     ["Higher latency than a DB"]),
   C("clickhouse","ClickHouse","clickhouse",None,0,
     "A columnar OLAP (analytics) database.",
     "The read-model / warehouse for fast analytics and dashboards.",
     "Aggregates billions of rows in milliseconds — built for analytics.",
     ["Extremely fast analytics"],
     ["Not for transactional writes"]),
 ]),
 # ---- cross-cutting ----
 dict(key="platform",name="Platform & runtime",color="#5C8AE0",icon="🚢",role="where everything runs",cross=True,components=[
   C("k8s","Kubernetes · EKS + GKE","kubernetes",None,0,
     "The container orchestrator that runs the whole fleet.",
     "Schedules, heals and scales every service across many machines.",
     "The industry standard for running containers reliably at scale.",
     ["Self-healing & scaling","Portable across clouds"],
     ["Steep learning curve"]),
   C("helm","Helm + Kustomize","helm",None,0,
     "Packaging and configuration tools for Kubernetes.",
     "Bundle each app's manifests and tailor them per environment.",
     "Standard way to template and reuse deployment config.",
     ["Reusable, templated deploys"],
     ["Templating can get complex"]),
   C("crd","Custom Operator + CRD","kubernetes",None,0,
     "A controller we write that extends Kubernetes with our own resource type.",
     "Automates tenant creation and preview environments as native K8s objects.",
     "Encodes our ops knowledge into the platform itself.",
     ["Automates complex ops","Top-tier skill to show"],
     ["Non-trivial to build correctly"]),
   C("keda","KEDA","kubernetes","📈",0,
     "Event-driven autoscaler for Kubernetes.",
     "Adds or removes workers based on how many jobs are waiting in Kafka.",
     "Scales on real backlog, not just CPU.",
     ["Scale on queue depth","Scale to zero"],
     ["Another component to run"]),
   C("vault","HashiCorp Vault","vault",None,0,
     "A secrets manager and PKI.",
     "Issues short-lived database credentials and certificates on demand.",
     "Dynamic, audited secrets beat long-lived passwords in config.",
     ["Dynamic, short-lived secrets","Full audit trail"],
     ["Operationally involved"]),
 ]),
 dict(key="delivery",name="Delivery & supply chain",color="#B57BD6",icon="🔄",role="how code reaches production",cross=True,components=[
   C("gha","GitHub Actions + OIDC","githubactions",None,0,
     "The CI system that builds, tests and ships.",
     "Runs on every push and deploys to the cloud using short-lived OIDC tokens (no stored keys).",
     "Keyless cloud auth removes the biggest secret-leak risk in CI.",
     ["Keyless, safer deploys","Tight GitHub integration"],
     ["YAML sprawl at scale"]),
   C("argocd","Argo CD · GitOps","argocd",None,0,
     "A GitOps continuous-delivery tool.",
     "Keeps the cluster exactly matching what's declared in Git, automatically.",
     "Git becomes the single source of truth; drift self-corrects.",
     ["Declarative & auditable","Auto drift-correction"],
     ["Everything must live in Git"]),
   C("rollouts","Argo Rollouts","argocd",None,0,
     "Progressive-delivery controller.",
     "Releases new versions gradually (canary / blue-green) and auto-rolls-back on bad metrics.",
     "De-risks every deploy by testing on a slice of real traffic first.",
     ["Safe, gradual releases","Metric-based auto-rollback"],
     ["Adds release-config complexity"]),
   C("terraform","Terraform / Crossplane","terraform",None,0,
     "Infrastructure-as-Code tools.",
     "Define all cloud infrastructure (network, clusters, databases) as versioned code.",
     "Reproducible, reviewable infrastructure instead of manual clicking.",
     ["Reproducible infra","Peer-reviewable changes"],
     ["State management care needed"]),
   C("supply","SBOM · cosign · SLSA","github","🔏",0,
     "Software supply-chain security tooling.",
     "Lists everything in each image, signs it, and proves how it was built.",
     "Lets us verify nothing was tampered with before it runs in production.",
     ["Tamper-evident builds","Provenance & trust"],
     ["Extra CI steps to maintain"]),
 ]),
 dict(key="observ",name="Observability & SRE",color="#E0678F",icon="📊",role="is it healthy? is it fast?",cross=True,components=[
   C("otel","OpenTelemetry","opentelemetry",None,0,
     "A vendor-neutral standard for traces, metrics and logs.",
     "Tags each request so we can follow it across every service (async, Kafka, gRPC).",
     "One standard instrumentation instead of per-vendor agents.",
     ["Vendor-neutral","End-to-end request traces"],
     ["Instrumentation effort"]),
   C("prom","Prometheus","prometheus",None,0,
     "A metrics database and alerting engine.",
     "Collects numbers (latency, error rate, queue depth) and fires alerts on rules.",
     "The de-facto standard for cloud-native metrics.",
     ["Powerful queries","Strong alerting"],
     ["Long-term storage needs add-ons"]),
   C("loki","Loki","grafana",None,0,
     "A log aggregation system.",
     "Centralizes logs from every service so we can search them in one place.",
     "Cheap, label-based logs that pair naturally with Grafana.",
     ["Cheap log storage","Grafana-native"],
     ["Not full-text like Elasticsearch"]),
   C("grafana","Grafana","grafana",None,0,
     "The visualization layer.",
     "Dashboards that show the health of the entire system at a glance.",
     "Single pane of glass over metrics, logs and traces.",
     ["One place for everything","Beautiful dashboards"],
     ["Dashboard maintenance"]),
   C("pyro","Pyroscope","grafana","🔥",0,
     "Continuous profiling.",
     "Shows exactly which code lines burn CPU/memory in production.",
     "Finds performance hot-spots that metrics alone can't.",
     ["Pinpoints hot code paths"],
     ["Small runtime overhead"]),
   C("slo","SLOs + burn-rate alerts","prometheus","🎯",0,
     "Service Level Objectives with error budgets.",
     "Define 'good enough' reliability and alert only when we're burning the budget too fast.",
     "Alerts on user-impact, not noise — the heart of SRE.",
     ["Meaningful, low-noise alerts","Aligns eng with users"],
     ["Requires honest target-setting"]),
   C("chaos","Chaos Mesh","kubernetes","🌪️",0,
     "A chaos-engineering tool.",
     "Deliberately injects failures (kill pods, add latency) to prove resilience.",
     "You only know it's resilient if you've tested failure on purpose.",
     ["Proves resilience","Finds weak spots early"],
     ["Must be run carefully"]),
   C("k6","k6","k6",None,0,
     "A load-testing tool.",
     "Simulates heavy traffic to find limits before real users do.",
     "Scriptable, developer-friendly performance testing.",
     ["Realistic load tests","Scriptable in JS"],
     ["Test design takes effort"]),
 ]),
]

# request path steps (ordered)
PATH = []
for L in LAYERS:
    for c in L["components"]:
        if c["path"]:
            PATH.append((c["path"], c["id"], c["name"], L["color"], c["role"]))
PATH.sort()
PATH_STEPS = [dict(id=i, name=n, color=col, role=r) for (o,i,n,col,r) in PATH]

# detail dict for JS
DETAIL = {}
LOGOS = {}
for L in LAYERS:
    for c in L["components"]:
        DETAIL[c["id"]] = dict(name=c["name"], layer=L["name"], color=L["color"],
                               logo=c["logo"], glyph=c["glyph"],
                               what=c["what"], role=c["role"], why=c["why"],
                               pros=c["pros"], cons=c["cons"])
        if c["logo"] and c["logo"] not in LOGOS:
            u = logo_uri(c["logo"]);
            if u: LOGOS[c["logo"]] = u

def badge_html(c, size=44):
    # concepts/patterns (glyph set) show a clean symbol; real products show their logo
    if c["glyph"]:
        inner = '<span class="glyph">%s</span>' % c["glyph"]
        cls = "badge concept"
    elif c["logo"] and c["logo"] in LOGOS:
        inner = '<img src="%s" alt="%s">' % (LOGOS[c["logo"]], c["name"])
        cls = "badge"
    else:
        inner = '<span class="glyph">•</span>'
        cls = "badge concept"
    return '<span class="%s">%s</span>' % (cls, inner)

def chip_html(c):
    p = (' data-path="%d"' % c["path"]) if c["path"] else ""
    return ('<button class="chip" data-id="%s"%s>%s<span class="chip-t">%s</span></button>'
            % (c["id"], p, badge_html(c), c["name"]))

def bands_html():
    out = []
    req_layers = [L for L in LAYERS if not L["cross"]]
    cross_layers = [L for L in LAYERS if L["cross"]]
    for idx, L in enumerate(req_layers):
        chips = "".join(chip_html(c) for c in L["components"])
        out.append(
          '<section class="band" style="--c:%s;--i:%d" data-layer="%s">'
          '<div class="band-head"><span class="band-ic">%s</span>'
          '<span class="band-tag">Layer %d</span><span class="band-name">%s</span>'
          '<span class="band-role">%s</span></div>'
          '<div class="chips">%s</div></section>'
          % (L["color"], idx, L["key"], L["icon"], idx+1, L["name"], L["role"], chips))
        if idx < len(req_layers)-1:
            out.append('<div class="conn" style="--i:%d"><div class="rail"></div><span class="arrow">▼</span></div>' % idx)
    banner = ('<div class="cross-divider"><span>▽ Spans every layer above ▽</span></div>')
    cross = []
    for L in cross_layers:
        chips = "".join(chip_html(c) for c in L["components"])
        cross.append(
          '<section class="band cross" style="--c:%s" data-layer="%s">'
          '<div class="band-head"><span class="band-ic">%s</span>'
          '<span class="band-tag">Cross-cutting</span><span class="band-name">%s</span>'
          '<span class="band-role">%s</span></div>'
          '<div class="chips">%s</div></section>'
          % (L["color"], L["key"], L["icon"], L["name"], L["role"], chips))
    return "".join(out) + banner + "".join(cross)

BANDS = bands_html()
DETAIL_JSON = json.dumps(DETAIL)
PATH_JSON = json.dumps(PATH_STEPS)

# ---------------- INTERACTIVE HTML ----------------
CSS = """
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#0B0E14;--panel:#141A24;--panel2:#1A212D;--line:#28313F;--text:#EAEEF5;--dim:#9AA6B6;--faint:#68748A;--accent:#F2913D}
.page{background:linear-gradient(var(--gridc,rgba(120,140,180,.05)) 1px,transparent 1px) 0 0/26px 26px,linear-gradient(90deg,rgba(120,140,180,.05) 1px,transparent 1px) 0 0/26px 26px,radial-gradient(1100px 460px at 50% -120px,rgba(242,145,61,.10),transparent 70%),var(--bg);color:var(--text);font-family:-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;min-height:100vh}
.wrap{max-width:1180px;margin:0 auto;padding:26px 20px 90px}
.banner{text-align:center;padding:15px 20px;border-radius:12px;margin-bottom:14px;background:linear-gradient(100deg,#8a4a12,#c4611e 45%,#e08a2c);box-shadow:0 10px 34px -14px rgba(242,145,61,.5)}
.banner h1{font-size:clamp(22px,3.6vw,34px);font-weight:800;color:#fff}
.banner .sub{font-size:13px;color:#fff;opacity:.92;margin-top:4px}
.controls{display:flex;flex-wrap:wrap;gap:10px;align-items:center;justify-content:center;margin:16px 0 6px}
.seg{display:inline-flex;background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.seg button{background:transparent;border:0;color:var(--dim);font:600 13px/1 inherit;padding:9px 16px;cursor:pointer}
.seg button.on{background:var(--accent);color:#12151b}
.btn{background:var(--panel);border:1px solid var(--line);color:var(--text);border-radius:10px;padding:9px 15px;font:600 13px/1 inherit;cursor:pointer;display:inline-flex;gap:7px;align-items:center}
.btn:hover{border-color:var(--accent)}
.btn.play{background:linear-gradient(90deg,#f2913d,#f0623c);color:#12151b;border:0}
.hint{text-align:center;color:var(--faint);font:12px/1.5 ui-monospace,monospace;margin-bottom:16px}
.legend{display:flex;flex-wrap:wrap;gap:6px 12px;justify-content:center;margin-bottom:18px;font-size:11px}
.lg{display:inline-flex;align-items:center;gap:5px;color:var(--dim)} .lg .d{width:9px;height:9px;border-radius:3px}
/* diagram */
.diagram{display:flex;flex-direction:column;transition:transform .5s ease}
.band{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:11px 13px;position:relative;opacity:0;transform:translateY(14px);animation:rise .5s cubic-bezier(.16,1,.3,1) forwards;animation-delay:calc(var(--i,0)*.06s)}
.band::before{content:"";position:absolute;left:0;top:12px;bottom:12px;width:3px;border-radius:3px;background:var(--c)}
.band.cross{border-style:dashed}
.band-head{display:flex;align-items:center;gap:9px;margin-bottom:9px;padding-left:6px}
.band-ic{font-size:16px}.band-tag{font:700 9px/1 ui-monospace,monospace;letter-spacing:.13em;text-transform:uppercase;color:var(--c)}
.band-name{font-size:13.5px;font-weight:750}.band-role{margin-left:auto;font:11px ui-monospace,monospace;color:var(--faint)}
.chips{display:flex;flex-wrap:wrap;gap:8px;padding-left:6px}
.chip{display:flex;align-items:center;gap:9px;background:var(--panel2);border:1px solid var(--line);border-top:2px solid var(--c);border-radius:10px;padding:7px 12px 7px 8px;cursor:pointer;color:var(--text);font:inherit;transition:transform .15s,box-shadow .15s,border-color .15s;text-align:left}
.chip:hover{transform:translateY(-2px);box-shadow:0 8px 20px -10px rgba(0,0,0,.7);border-color:var(--c)}
.chip.active{box-shadow:0 0 0 2px var(--c),0 0 26px -4px var(--c);transform:translateY(-2px)}
.chip-t{font-size:12.5px;font-weight:650}
.badge{width:34px;height:34px;border-radius:8px;background:#fff;display:flex;align-items:center;justify-content:center;flex:none}
.badge img{width:22px;height:22px;object-fit:contain}
.badge.concept{background:color-mix(in srgb,var(--c) 22%,#0b0e14)}
.badge .glyph{font-size:17px}
.conn{height:26px;display:flex;justify-content:center;position:relative}
.conn .rail{width:2px;height:100%;background:var(--line);position:relative;overflow:hidden}
.conn .rail::after{content:"";position:absolute;left:-1px;width:4px;height:11px;border-radius:4px;background:linear-gradient(var(--accent),transparent);box-shadow:0 0 10px 2px rgba(242,145,61,.6);animation:flow 2.4s linear infinite;animation-delay:calc(var(--i,0)*.16s)}
.conn .arrow{position:absolute;bottom:-3px;color:var(--line);font-size:12px}
.cross-divider{text-align:center;margin:22px 0 14px;font:700 10px/1 ui-monospace,monospace;letter-spacing:.2em;text-transform:uppercase;color:var(--faint)}
/* isometric mode */
.diagram.iso{transform:perspective(2400px) rotateX(51deg) rotateZ(-42deg);transform-style:preserve-3d;gap:16px;margin:40px auto 120px;width:78%}
.diagram.iso .conn,.diagram.iso .cross-divider{display:none}
.diagram.iso .band{box-shadow:-24px 24px 40px -18px rgba(0,0,0,.8);border-top:1px solid rgba(255,255,255,.12)}
.diagram.iso .band::after{content:"";position:absolute;left:0;right:0;bottom:-10px;height:10px;background:var(--c);opacity:.35;transform:skewX(-45deg);transform-origin:top;border-radius:0 0 10px 10px}
/* drawer */
.scrim{position:fixed;inset:0;background:rgba(4,7,12,.6);opacity:0;pointer-events:none;transition:.25s;z-index:40}
.scrim.show{opacity:1;pointer-events:auto}
.drawer{position:fixed;top:0;right:0;height:100%;width:min(430px,92vw);background:var(--panel);border-left:1px solid var(--line);transform:translateX(100%);transition:transform .32s cubic-bezier(.16,1,.3,1);z-index:50;overflow-y:auto;padding:24px}
.drawer.show{transform:none}
.d-close{position:absolute;top:16px;right:18px;background:var(--panel2);border:1px solid var(--line);color:var(--dim);border-radius:8px;width:32px;height:32px;cursor:pointer;font-size:16px}
.d-head{display:flex;align-items:center;gap:14px;margin-bottom:6px}
.d-badge{width:56px;height:56px;border-radius:13px;background:#fff;display:flex;align-items:center;justify-content:center;flex:none}
.d-badge img{width:36px;height:36px;object-fit:contain}
.d-badge.concept{background:color-mix(in srgb,var(--dc) 24%,#0b0e14)}.d-badge .glyph{font-size:28px}
.d-name{font-size:20px;font-weight:800;letter-spacing:-.01em}
.d-layer{font:11px ui-monospace,monospace;color:var(--dc);text-transform:uppercase;letter-spacing:.1em;margin-top:2px}
.d-sec{margin-top:18px}
.d-sec h4{font:700 10.5px/1 ui-monospace,monospace;letter-spacing:.14em;text-transform:uppercase;color:var(--faint);margin-bottom:6px;display:flex;align-items:center;gap:7px}
.d-sec h4::before{content:"";width:8px;height:8px;border-radius:2px;background:var(--dc)}
.d-sec p{font-size:14px;color:var(--text);line-height:1.55}
.d-why{background:var(--panel2);border:1px solid var(--line);border-left:3px solid var(--dc);border-radius:8px;padding:11px 13px;font-size:13.5px;color:var(--dim);line-height:1.55}
.pc{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:6px}
.pc ul{list-style:none}.pc li{font-size:12.8px;line-height:1.45;margin-bottom:6px;padding-left:18px;position:relative;color:var(--dim)}
.pros li::before{content:"✓";position:absolute;left:0;color:#3EB6A0;font-weight:700}
.cons li::before{content:"–";position:absolute;left:0;color:#F0623C;font-weight:700}
.pc h5{font:700 10px/1 ui-monospace,monospace;letter-spacing:.1em;text-transform:uppercase;margin-bottom:8px}
.pros h5{color:#3EB6A0}.cons h5{color:#F0623C}
/* narration bar */
.narr{position:fixed;left:50%;bottom:22px;transform:translateX(-50%) translateY(140%);width:min(760px,92vw);background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:14px 18px;z-index:45;box-shadow:0 20px 50px -20px rgba(0,0,0,.8);transition:transform .35s cubic-bezier(.16,1,.3,1)}
.narr.show{transform:translateX(-50%)}
.narr .step{font:700 10px/1 ui-monospace,monospace;letter-spacing:.14em;text-transform:uppercase;color:var(--accent)}
.narr .nm{font-size:16px;font-weight:750;margin:5px 0 3px}
.narr .rl{font-size:13px;color:var(--dim)}
.narr .nav{display:flex;gap:8px;margin-top:12px;align-items:center}
.narr .prog{flex:1;height:5px;background:var(--panel2);border-radius:4px;overflow:hidden}
.narr .prog i{display:block;height:100%;background:linear-gradient(90deg,#f2913d,#f0623c);width:0;transition:width .3s}
.foot{margin-top:30px;text-align:center;font:10.5px/1.6 ui-monospace,monospace;color:var(--faint);border-top:1px solid var(--line);padding-top:14px}
@keyframes rise{to{opacity:1;transform:none}}
@keyframes flow{0%{top:-14px;opacity:0}12%{opacity:1}88%{opacity:1}100%{top:100%;opacity:0}}
@media (prefers-reduced-motion:reduce){.band{opacity:1;transform:none;animation:none}.conn .rail::after{animation:none}}
@media (max-width:640px){.diagram.iso{transform:none;width:100%}.pc{grid-template-columns:1fr}}
"""

JS = """
var DETAIL = __DETAIL__;
var PATH = __PATH__;
var diagram = document.getElementById('diagram');
var scrim = document.getElementById('scrim');
var drawer = document.getElementById('drawer');

function openDetail(id){
  var d = DETAIL[id]; if(!d) return;
  drawer.style.setProperty('--dc', d.color);
  var badge = d.glyph ? '<span class="d-badge concept"><span class="glyph">'+d.glyph+'</span></span>'
            : (d.logo ? '<span class="d-badge"><img src="'+(window.LOGOS[d.logo]||'')+'" alt=""></span>'
                      : '<span class="d-badge concept"><span class="glyph">•</span></span>');
  var pros = d.pros.map(function(x){return '<li>'+x+'</li>'}).join('');
  var cons = d.cons.map(function(x){return '<li>'+x+'</li>'}).join('');
  drawer.innerHTML =
    '<button class="d-close" onclick="closeDetail()">×</button>'+
    '<div class="d-head">'+badge+'<div><div class="d-name">'+d.name+'</div><div class="d-layer">'+d.layer+'</div></div></div>'+
    '<div class="d-sec"><h4>What it is</h4><p>'+d.what+'</p></div>'+
    '<div class="d-sec"><h4>Its job in this layer</h4><p>'+d.role+'</p></div>'+
    '<div class="d-sec"><h4>Why we chose it</h4><div class="d-why">'+d.why+'</div></div>'+
    '<div class="d-sec"><h4>Trade-offs</h4><div class="pc">'+
      '<div class="pros"><h5>Advantages</h5><ul>'+pros+'</ul></div>'+
      '<div class="cons"><h5>Watch-outs</h5><ul>'+cons+'</ul></div></div></div>';
  scrim.classList.add('show'); drawer.classList.add('show');
}
function closeDetail(){ scrim.classList.remove('show'); drawer.classList.remove('show'); }
scrim.addEventListener('click', closeDetail);
document.addEventListener('keydown',function(e){ if(e.key==='Escape'){closeDetail(); stopPlay();} });

diagram.addEventListener('click', function(e){
  var c = e.target.closest('.chip'); if(c) openDetail(c.dataset.id);
});

// view toggle
document.getElementById('vflow').addEventListener('click', function(){ setView('flow'); });
document.getElementById('viso').addEventListener('click', function(){ setView('iso'); });
function setView(v){
  diagram.classList.toggle('iso', v==='iso');
  document.getElementById('vflow').classList.toggle('on', v==='flow');
  document.getElementById('viso').classList.toggle('on', v==='iso');
}

// flow player
var narr = document.getElementById('narr');
var step = -1, timer = null;
function chipEl(id){ return diagram.querySelector('.chip[data-id="'+id+'"]'); }
function showStep(i){
  document.querySelectorAll('.chip.active').forEach(function(c){c.classList.remove('active')});
  step = i; var s = PATH[i];
  var el = chipEl(s.id);
  if(el){ el.classList.add('active'); if(!diagram.classList.contains('iso')) el.scrollIntoView({behavior:'smooth',block:'center'}); }
  narr.style.setProperty('--nc', s.color);
  narr.innerHTML =
    '<div class="step">Step '+(i+1)+' / '+PATH.length+' · request flow</div>'+
    '<div class="nm">'+s.name+'</div>'+
    '<div class="rl">'+s.role+'</div>'+
    '<div class="nav"><button class="btn" onclick="prevStep()">‹ Back</button>'+
    '<button class="btn" onclick="nextStep()">Next ›</button>'+
    '<div class="prog"><i style="width:'+Math.round((i+1)/PATH.length*100)+'%"></i></div>'+
    '<button class="btn" onclick="stopPlay()">Close</button></div>';
  narr.classList.add('show');
}
function nextStep(){ if(step < PATH.length-1) showStep(step+1); else stopPlay(); }
function prevStep(){ if(step > 0) showStep(step-1); }
function play(){ setView('flow'); showStep(0);
  clearInterval(timer); timer = setInterval(function(){ if(step<PATH.length-1) showStep(step+1); else { clearInterval(timer); } }, 2600); }
function stopPlay(){ clearInterval(timer); narr.classList.remove('show'); document.querySelectorAll('.chip.active').forEach(function(c){c.classList.remove('active')}); step=-1; }
document.getElementById('play').addEventListener('click', play);
"""

INTER = ('<title>Helios — Interactive Architecture</title><style>'+CSS+'</style>'
 '<div class="page"><div class="wrap">'
 '<div class="banner"><h1>Helios — Interactive Architecture</h1>'
 '<div class="sub">Cloud-Native LLM Orchestration Platform · click any component to learn what it is &amp; why it is here</div></div>'
 '<div class="controls">'
 '<span class="seg"><button id="vflow" class="on">Flow view</button><button id="viso">3-D stack</button></span>'
 '<button id="play" class="btn play">▶ Play the request flow</button>'
 '</div>'
 '<div class="hint">Tip: click a logo tile for a plain-English detail card · press ▶ to walk the request component-by-component</div>'
 '<div class="legend">'
 + "".join('<span class="lg"><span class="d" style="background:%s"></span>%s</span>'%(L["color"],L["name"]) for L in LAYERS)
 + '</div>'
 '<div class="diagram" id="diagram">'+BANDS+'</div>'
 '<div class="foot">Helios · every component annotated with what it is, its role, why chosen, and its trade-offs · logos identify each tool</div>'
 '</div></div>'
 '<div class="scrim" id="scrim"></div><aside class="drawer" id="drawer"></aside>'
 '<div class="narr" id="narr"></div>'
 '<script>window.LOGOS='+json.dumps(LOGOS)+';</script>'
 '<script>'+JS.replace("__DETAIL__",DETAIL_JSON).replace("__PATH__",PATH_JSON)+'</script>')

open("helios-arch-interactive.html","w").write(INTER)
print("interactive:", len(INTER), "bytes")

# ---------------- PRINT / PDF HTML ----------------
def ref_card(c, color, layer):
    b = badge_html(c, 40)
    pros = "".join('<li>%s</li>'%x for x in c["pros"])
    cons = "".join('<li>%s</li>'%x for x in c["cons"])
    return ('<div class="rc" style="--c:%s"><div class="rc-h">%s<div><div class="rc-n">%s</div>'
            '<div class="rc-l">%s</div></div></div>'
            '<p class="rc-w"><b>What:</b> %s</p>'
            '<p class="rc-w"><b>Role:</b> %s</p>'
            '<p class="rc-y"><b>Why chosen:</b> %s</p>'
            '<div class="rc-pc"><ul class="pros">%s</ul><ul class="cons">%s</ul></div></div>'
            % (color, b, c["name"], layer, c["what"], c["role"], c["why"], pros, cons))

ref_sections = []
for L in LAYERS:
    cards = "".join(ref_card(c, L["color"], L["name"]) for c in L["components"])
    ref_sections.append('<h3 class="rs" style="--c:%s"><span>%s</span> %s</h3><div class="rgrid">%s</div>'
                         % (L["color"], L["icon"], L["name"], cards))

PCSS = CSS + """
@page{size:A4;margin:12mm}
.page{background:var(--bg)!important}
.wrap{max-width:none;padding:0}
.band{opacity:1;transform:none;animation:none;break-inside:avoid}
.diagram{transform:none!important;width:auto}
.chip{cursor:default}
.conn .rail::after{animation:none;opacity:.5;top:30%}
.refhead{break-before:page;border-top:2px solid var(--accent);padding-top:10px;margin-top:26px}
.refhead h2{font-size:22px;font-weight:800}
.refhead p{color:var(--dim);font-size:12px;margin-top:4px}
.rs{display:flex;align-items:center;gap:9px;font-size:14px;font-weight:750;margin:16px 0 9px;color:var(--text);break-after:avoid}
.rs span{color:var(--c)}
.rgrid{display:grid;grid-template-columns:1fr 1fr;gap:9px;margin-bottom:6px}
.rc{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--c);border-radius:9px;padding:9px 11px;break-inside:avoid}
.rc-h{display:flex;align-items:center;gap:9px;margin-bottom:6px}
.rc .badge{width:32px;height:32px}.rc .badge img{width:20px;height:20px}
.rc-n{font-size:12.5px;font-weight:750}.rc-l{font:9px ui-monospace,monospace;color:var(--faint);text-transform:uppercase;letter-spacing:.08em}
.rc-w{font-size:10.5px;color:var(--dim);line-height:1.4;margin-bottom:3px}.rc-w b{color:var(--text)}
.rc-y{font-size:10.5px;color:var(--dim);line-height:1.4;margin:4px 0 6px}.rc-y b{color:var(--c)}
.rc-pc{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.rc-pc ul{list-style:none}.rc-pc li{font-size:10px;line-height:1.35;padding-left:13px;position:relative;color:var(--dim);margin-bottom:3px}
.rc-pc .pros li::before{content:"✓";position:absolute;left:0;color:#3EB6A0}
.rc-pc .cons li::before{content:"–";position:absolute;left:0;color:#F0623C}
"""

PRINT = ('<title>Helios Architecture</title><style>'+PCSS+'</style>'
 '<div class="page"><div class="wrap">'
 '<div class="banner"><h1>Helios — End-to-End Architecture</h1>'
 '<div class="sub">Cloud-Native LLM Orchestration Platform · the full request flow, layer by layer</div></div>'
 '<div class="legend">'
 + "".join('<span class="lg"><span class="d" style="background:%s"></span>%s</span>'%(L["color"],L["name"]) for L in LAYERS)
 + '</div>'
 '<div class="diagram">'+BANDS+'</div>'
 '<div class="refhead"><h2>Component Reference</h2><p>Every component in plain English — what it is, its role in the layer, why we chose it, and its trade-offs.</p></div>'
 + "".join(ref_sections) +
 '<div class="foot">Helios · Cloud-Native LLM Orchestration Platform — architecture &amp; component reference</div>'
 '</div></div>')

open("helios-arch-print.html","w").write(PRINT)
print("print:", len(PRINT), "bytes")
print("components:", len(DETAIL), "| path steps:", len(PATH_STEPS))
