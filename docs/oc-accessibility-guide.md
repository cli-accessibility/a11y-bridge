# Using axcli with OpenShift CLI (oc)

This guide demonstrates how axcli improves the accessibility of the OpenShift CLI (`oc`) across different use cases. The `oc` CLI barely passes the CLI-ACS conformance test for color and visual accessibility — it produces plain, uncolored table output with no text-based status indicators, no structured output alternatives for many commands, and no screen reader optimizations.

axcli compensates for these gaps automatically.

---

## 1. Listing Projects

### Without axcli

```
$ oc projects
You have access to the following projects and can switch between them with ' project <projectname>':

  * arewm-tenant - arewm
    crt-redhat-acm-tenant - crt-redhat-acm
    gatekeeper-tenant - gatekeeper
    rhtas-tenant - rhtas

Using project "arewm-tenant" on server "https://api.stone-prd-rh01.pg1f.p1.openshiftapps.com:6443".
```

**Problem for sighted users:** All projects look the same — the `*` marker is easy to miss in a long list. No visual distinction between active and inactive projects.

**Problem for screen reader users:** The `*` character is announced as "asterisk" with no context. The user must remember that asterisk means "active."

### With axcli (sighted mode)

```
$ axcli oc projects
status: Running: oc projects
  * arewm-tenant - arewm          ← bold green (active project highlighted)
    crt-redhat-acm-tenant - crt-redhat-acm
    gatekeeper-tenant - gatekeeper
    rhtas-tenant - rhtas
```

The active project is bold green — immediately visible in a long list.

### With axcli (screen reader mode)

```
$ axcli --domain screen-reader oc projects
status: Running: oc projects
result: You have access to the following projects...
result:   * arewm-tenant - arewm
result:     crt-redhat-acm-tenant - crt-redhat-acm
result:     gatekeeper-tenant - gatekeeper
result:     rhtas-tenant - rhtas
result: Using project "arewm-tenant" on server "https://api.stone-prd-rh01.pg1f.p1.openshiftapps.com:6443".
```

Every line has a `result:` prefix — screen reader users can navigate between results using search.

---

## 2. Listing Pods (Table Output)

This is where axcli provides the most value. Kubernetes/OpenShift table output is the single hardest format for screen readers.

### Without axcli

```
$ oc get pods -n rhtas-tenant
NAME                                                              READY   STATUS      RESTARTS   AGE
mod8a0422cf7e487a5a07f411fa0847526b66edf9d9b2c69a8c2b0fabfc-pod   0/1     Completed   0          3m
model-transparency-on-push-z8v8x-build-images-0-pod               0/4     Completed   0          5m28s
model-transparency-on-push-z8v8x-clone-repository-pod             0/2     Completed   0          5m51s
```

**Problem for screen readers:** The output is a whitespace-aligned table. A screen reader reads it as: "NAME READY STATUS RESTARTS AGE mod8a zero four two two..." — a stream of words with no way to tell which value belongs to which column. With 242 pods, this is completely unusable.

### With axcli (sighted mode)

```
$ axcli oc get pods -n rhtas-tenant
status: Running: oc get pods -n rhtas-tenant
NAME                                                              READY   STATUS      RESTARTS   AGE
mod8a0422cf7e487a5a07f411fa0847526b66edf9d9b2c69a8c2b0fabfc-pod   0/1     Completed   0          3m     ← "Completed" in green
model-transparency-on-push-z8v8x-build-images-0-pod               0/4     Completed   0          5m28s  ← "Completed" in green
```

Status words are color-coded: `Completed` → green, `Pending` → yellow, `CrashLoopBackOff` → red, `Error` → red. The header row is bold. Sighted users can scan the STATUS column by color.

### With axcli (screen reader mode)

```
$ axcli --domain screen-reader oc get pods -n rhtas-tenant
status: Running: oc get pods -n rhtas-tenant
result: 242 item(s).
result: 1. NAME: mod8a0422cf7e487a5a07f411fa0847526b66edf9d9b2c69a8c2b0fabfc-pod. READY: 0/1. STATUS: Completed. RESTARTS: 0. AGE: 3m.
result: 2. NAME: model-transparency-on-push-z8v8x-build-images-0-pod. READY: 0/4. STATUS: Completed. RESTARTS: 0. AGE: 5m28s.
result: 3. NAME: model-transparency-on-push-z8v8x-clone-repository-pod. READY: 0/2. STATUS: Completed. RESTARTS: 0. AGE: 5m51s.
```

Every column value is paired with its header: `STATUS: Completed`, `RESTARTS: 0`, `AGE: 3m`. A screen reader user can hear exactly which pod has which status without memorizing column positions.

If any pods had status issues (and the output had color), axcli would add semantic prefixes:

```
result: 5. [ERROR] NAME: failing-pod. READY: 0/1. STATUS: CrashLoopBackOff. RESTARTS: 47. AGE: 3d.
result: 6. [WARN] NAME: slow-pod. READY: 0/1. STATUS: Pending. RESTARTS: 0. AGE: 10m.
result: 7. [OK] NAME: healthy-pod. READY: 1/1. STATUS: Running. RESTARTS: 0. AGE: 5d.
```

---

## 3. Pod Details (Long Output)

### Without axcli

```
$ oc describe pod my-pod -n rhtas-tenant
Name:                 mod8a0422cf7e487a5a07f411fa0847526b66edf9d9b2c69a8c2b0fabfc-pod
Namespace:            rhtas-tenant
Priority:             0
Priority Class Name:  konflux-default
Service Account:      build-pipeline-model-transparency-v1-0
Node:                 ip-10-206-29-200.ec2.internal/10.206.29.200
Start Time:           Mon, 14 Sep 2026 10:39:17 +0100
Labels:               app.kubernetes.io/managed-by=tekton-pipelines
                      app.kubernetes.io/version=v0.50.0
                      appstudio.openshift.io/application=model-transparency-v1-0
...
(200+ lines)
```

**Problem:** `oc describe` output can be 200+ lines of key-value pairs, nested sections, and multi-line values. Screen readers read every line — there's no way to jump to the section you care about.

### With axcli (screen reader mode)

```
$ axcli --domain screen-reader oc describe pod my-pod -n rhtas-tenant
status: Running: oc describe pod my-pod -n rhtas-tenant
result: 200+ lines of output. First 20 shown.
result: Name:                 mod8a0422cf7e487a5a07f411fa0847526b66edf9d9b2c69a8c2b0fabfc-pod
result: Namespace:            rhtas-tenant
result: Priority:             0
...
result: ... (180+ more lines)
```

Long output is truncated with a line count — the user knows how much there is before deciding to continue.

---

## 4. Error Handling

### Without axcli

```
$ oc get pods -n nonexistent-ns
Error from server (Forbidden): pods is forbidden: User "sacm" cannot list resource "pods" in API group "" in the namespace "nonexistent-ns"
```

**Problem:** The error goes to stderr. If stdout is piped, the user might miss it entirely. The error text has no prefix — a screen reader user hearing a stream of output doesn't know this is an error versus a result.

### With axcli (screen reader mode)

```
$ axcli --domain screen-reader oc get pods -n nonexistent-ns
status: Running: oc get pods -n nonexistent-ns
error: Error from server (Forbidden): pods is forbidden: User "sacm" cannot list resource "pods" in API group "" in the namespace "nonexistent-ns"
```

The `error:` prefix makes the error immediately identifiable to both screen readers and sighted users. The exit code is preserved for scripts.

### With axcli (sighted mode)

```
$ axcli oc get pods -n nonexistent-ns
status: Running: oc get pods -n nonexistent-ns
error: Error from server (Forbidden): ...    ← red text
```

The error line is displayed in red.

---

## 5. Project Status

### Without axcli

```
$ oc status -n rhtas-tenant
In project rhtas (rhtas-tenant) on server https://api.stone-prd-rh01.pg1f.p1.openshiftapps.com:6443

pod/rhtas-operator-bundle-on-push-rkdws-clamav-scan-pod runs quay.io/konflux-ci/clamav-db:latest, quay.io/konflux-ci/task-runner:2.1.0@sha256:c34c...
pod/rhtas-operator-bundle-on-push-2kx6f-sast-snyk-check-pod runs quay.io/konflux-ci/build-trusted-artifacts@sha256:15c5...
```

**Problem:** Each line is extremely long (image digests with full SHA256 hashes). Screen readers read every character of every hash. The actual information (which pod is running what) is buried in noise.

### With axcli (screen reader mode)

```
$ axcli --domain screen-reader oc status -n rhtas-tenant
status: Running: oc status -n rhtas-tenant
result: In project rhtas (rhtas-tenant) on server https://api.stone-prd-rh01.pg1f.p1.openshiftapps.com:6443
result:
result: pod/rhtas-operator-bundle-on-push-rkdws-clamav-scan-pod runs quay.io/konflux-ci/clamav-db:latest, ...
```

The `result:` prefix on every line lets screen reader users jump between results. Future versions will summarize long SHA256 hashes.

---

## 6. Version and Identity

### Without axcli

```
$ oc version --client
Client Version: 4.19.10
Kustomize Version: v5.5.0

$ oc whoami
sacm
```

### With axcli

```
$ axcli oc version --client
status: Running: oc version --client
result: Client Version: 4.19.10
result: Kustomize Version: v5.5.0

$ axcli oc whoami
status: Running: oc whoami
result: sacm
```

Simple commands pass through with labels — minimal overhead, consistent format.

---

## 7. Piping (Script Compatibility)

axcli is pipe-safe — when stdout is not a terminal, it passes raw output through without labels:

```bash
# Count pods by status
axcli oc get pods -n rhtas-tenant | awk '{print $3}' | sort | uniq -c

# Find failing pods
axcli oc get pods -n rhtas-tenant | grep -v Completed

# Use in scripts
POD_COUNT=$(axcli oc get pods -n rhtas-tenant | tail -n +2 | wc -l)
echo "Total pods: $POD_COUNT"
```

The ANSI stripping still happens in pipe mode — scripts get clean text without escape sequences.

---

## Summary: What oc Lacks vs What axcli Adds

| oc behavior | CLI-ACS gap | axcli compensation |
|---|---|---|
| Plain table output with no column labels per row | CV-1: Color not sole info (tables rely on spatial position) | Converts tables to labeled sentences: `NAME: x. STATUS: y.` |
| No color for status indicators | CV-1: No visual distinction between Running/Failed/Pending | Adds semantic color (sighted) or text prefixes `[OK]`/`[ERROR]` (screen reader) |
| Respects NO_COLOR but no --no-color flag | CV-3: Missing per-invocation flag | axcli always strips ANSI regardless |
| No structured output for many commands (oc projects, oc status) | OS-6: No --json for some commands | axcli formats output with labels |
| Long output with no pagination or summary | HD-6: No progressive disclosure | Truncates with line count, shows first 20 |
| Errors to stderr with no prefix | EF-6: No visual error distinction | Adds `error:` prefix, red color |
| No screen reader detection | No --screen-reader or --accessible flag | Auto-detects via NO_COLOR, TERM, orca/nvda process |

---

## Quick Reference

```bash
# Adaptive (default) — adds color for sighted, text for screen reader
axcli oc get pods -n myns

# Force screen reader mode
axcli --domain screen-reader oc get pods -n myns

# Force screen reader mode via env var
NO_COLOR=1 axcli oc get pods -n myns
AXCLI_SCREEN_READER=1 axcli oc get pods -n myns

# Audio mode — speaks results aloud
axcli --domain audio oc get pods -n myns

# AI session with voice — describe what you want, hear results
axcli --domain audio --askai oc
# you: what pods are running in my namespace
# (results spoken one by one)
# you: v  (voice input — speak your next command)

# Strip ANSI only, no reformatting
axcli --raw oc describe pod my-pod -n myns

# Pass through with NO_COLOR=1 TERM=dumb set
axcli --passthrough oc diff -f manifest.yaml
```
