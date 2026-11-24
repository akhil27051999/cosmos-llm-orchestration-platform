# 0008: Close the roadmap's skill gaps

**Status:** Accepted · **Date:** 2026-11-25 · **Milestone:** all (amends [0007](0007-sre-focused-roadmap.md))

## Context
I mapped every stage of the [0007](0007-sre-focused-roadmap.md) roadmap to the topics a 2–4 year DevOps/SRE
interview covers. The roadmap is strong on containers, Kubernetes, GitOps, observability and SLOs, but leaves
gaps: AWS (S8 said only "managed cluster"), Python ops scripting, Kustomize, Linux internals, TCP-level
networking, system design and Ansible.

## Decision
Keep the 0007 order and stage numbers. Add to existing stages instead of inserting new ones, so nothing
already written has to be renumbered:
1. **S1:** multi-arch images (arm64 + amd64) and graceful SIGTERM shutdown in the worker (PID 1, signals).
2. **S2:** `securityContext`, Pod Security Admission and NetworkPolicy listed explicitly.
3. **S3:** dev/prod as **Kustomize overlays** over the Helm chart.
4. **S4:** trace one request end to end with `tcpdump`.
5. **S6:** Linux drills (OOMKill, disk full, file-descriptor exhaustion) and **`cosmosctl`**, a Python ops CLI.
6. **S8:** run on **AWS EKS** (VPC, IAM roles for service accounts, ALB controller, ECR, S3, Route 53).
7. **New S9:** a "Cosmos at 100×" design doc.
8. **New S10 (optional):** Ansible installing k3s on two Multipass VMs.

## Alternatives considered
- **A second project for the gaps:** would split the 20 h/week and leave both projects half finished.
- **GKE for S8:** fine technically, but most DevOps job listings ask for AWS.
- **Keep Ansible dropped (as in 0007):** still true that Cosmos has no VMs. S10 creates two only to learn
  Ansible and systemd, so it stays optional and last.
- **Design doc right after S6:** S9 comes after S8 so the doc can use real numbers from the cloud run.

## Consequences
- Estimate grows from ~75–80 h to **~103 h** (+10 h for S10): about 5–6 weeks at 20 h/week, finishing
  mid-January 2027. The README Status and Timeline track it.
- The project doesn't cover the whole interview loop. Live coding, design practice and real incident
  stories are practised outside it, every week.
- The next free decision number for M6 becomes **0009**.
