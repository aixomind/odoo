# L4E Discount Approval — Odoo 19

A multi-tier discount governance module for Sale Orders. Controls how much
discount a salesperson can give without approval, routes approval requests to
the right approvers based on the discount range, and blocks order confirmation
until approval is granted.

---

## Table of Contents

1. [How It Works — Overview](#how-it-works--overview)
2. [Three Config Layers & Their Roles](#three-config-layers--their-roles)
3. [Step-by-Step Flow](#step-by-step-flow)
4. [Real-World Example](#real-world-example)
5. [Setup Guide](#setup-guide)
6. [Approval Modes](#approval-modes)
7. [States & What They Mean](#states--what-they-mean)
8. [UI Elements on Sale Order](#ui-elements-on-sale-order)
9. [Security & Access](#security--access)
10. [Configuration Parameters](#configuration-parameters)

---

## How It Works — Overview

```
Salesperson adds discount on sale order lines
            ↓
System checks: does the discount exceed this salesperson's allowed limit?
            ↓
      YES → Approval required       NO → Confirm normally
            ↓
System finds the matching Discount Tier for the discount range
            ↓
Approval request created → Approvers notified
            ↓
Approver approves / refuses
            ↓
   APPROVED → Salesperson can now confirm the order
   REFUSED  → Salesperson must adjust discount or re-request
```

---

## Three Config Layers & Their Roles

These three configurations serve **completely different purposes** and work together:

| Layer | Where Configured | Purpose |
|---|---|---|
| **Default Limit** | Sales → Configuration → Settings | Fallback threshold for salespersons with no custom limit |
| **Salesperson Limit** | Sales → L4E Approvals → Discount Limits | Per-person override — replaces the default for that user |
| **Discount Tier** | Sales → L4E Approvals → Discount Tiers | Routing — determines WHO approves based on how large the discount is |

### How priority works

When the system checks whether a discount needs approval:

```
Does the salesperson have a custom Discount Limit record?
    ├── YES → use their custom limit (default is ignored for this person)
    └── NO  → use the Default Limit from Sales Settings
```

Once it's confirmed approval is needed, the system finds the matching tier:

```
Max discount % on the order falls in which tier range?
    ├── Tier 1: 0–20%    → Sales Manager approves
    ├── Tier 2: 20–40%   → Sales Director approves
    └── Tier 3: 40–100%  → CEO approves
```

---

## Step-by-Step Flow

### 1. Salesperson creates a quotation with a discount

The system automatically computes on every change:
- The **max discount %** across all lines
- Whether it **exceeds** the salesperson's limit
- Which **tier** it falls into
- A per-line flag `⚠ Over Limit` on any line that exceeds the limit

### 2. Salesperson clicks "Confirm"

The system checks:

| Condition | Result |
|---|---|
| Feature disabled in Settings | Normal Odoo confirm, no check |
| Discount does not exceed limit | Normal Odoo confirm |
| Discount exceeds limit, no request yet | Automatically creates request + blocks confirm |
| Request is **pending** | Blocked — "Wait for approval" error |
| Request is **refused** | Blocked — "Adjust discount or re-request" error |
| Request is **approved** | Proceeds to normal Odoo confirm |

### 3. Approval request created

The system:
- Cancels any previous pending request for this order
- Finds the matching **Discount Tier** for the max discount %
- Creates an `l4e.discount.approval.request` with:
  - The matched tier's approvers copied in
  - A snapshot of the max discount %
  - A summary text of all lines that exceed the limit
- Sets the sale order state to `pending`
- Posts a chatter message on the order
- Notifies all approvers via chatter + email + DM

### 4. Approver receives notification and opens the request

The approver sees:
- Which sale order triggered the request
- Who requested it and when
- The max discount % and which tier matched
- A summary of all lines over the limit
- **Approve** and **Refuse** buttons

### 5a. Approver approves

- Request state → `approved`
- Sale order `l4e_discount_approval_state` → `approved`
- Requester notified via chatter + email

The salesperson can now go back and click **Confirm** — the order goes through normally.

### 5b. Approver refuses

- Refuse wizard opens — approver must enter a reason
- Request state → `refused`
- Sale order `l4e_discount_approval_state` → `refused`
- Requester notified with the refusal reason via chatter + email

The salesperson must either:
- Reduce the discounts to within the allowed limit, then confirm normally
- Or click **Request Discount Approval** again to start a new approval cycle

---

## Real-World Example

### Configuration

| Setting | Value |
|---|---|
| Default Line Limit (Settings) | 10% |
| Ahmed's custom limit | 25% |
| Sara has no custom limit | uses default → 10% |
| Tier 1 | 10% < discount ≤ 25% → Sales Manager (any) |
| Tier 2 | 25% < discount ≤ 50% → Sales Director (any) |
| Tier 3 | 50% < discount ≤ 100% → CEO (all) |

---

### Scenario A — Ahmed gives 15% discount

```
Ahmed's limit = 25%
Max discount on order = 15%
15% < 25%  →  No approval needed  →  Order confirms normally
```

---

### Scenario B — Ahmed gives 30% discount

```
Ahmed's limit = 25%
Max discount on order = 30%
30% > 25%  →  Approval needed

Tier match: 25% < 30% ≤ 50%  →  Tier 2: Sales Director (any one)

→ Request created → Sales Director notified
→ Sale order state = 'Pending Approval'
→ Sales Director approves
→ Ahmed confirms the order normally
```

---

### Scenario C — Sara gives 12% discount

```
Sara has no custom limit → uses default = 10%
Max discount on order = 12%
12% > 10%  →  Approval needed

Tier match: 10% < 12% ≤ 25%  →  Tier 1: Sales Manager (any one)

→ Request created → Sales Manager notified
→ Sale order state = 'Pending Approval'
→ Sales Manager approves
→ Sara confirms the order normally
```

---

### Scenario D — Ahmed gives 60% discount (needs all approvers)

```
Ahmed's limit = 25%
Max discount on order = 60%
60% > 25%  →  Approval needed

Tier match: 50% < 60% ≤ 100%  →  Tier 3: CEO (ALL must approve)

→ Request created → CEO notified
→ Approval mode = 'all' → every listed approver must click Approve
→ Once all approve → Ahmed confirms the order
```

---

### Scenario E — Sara gives 12% discount, manager refuses

```
Sara's limit exceeded → request created → Sales Manager refuses with reason:
"Discount too high for this customer category."

→ Sale order state = 'Refused'
→ Sara notified with the reason
→ Sara reduces discount to 9% (within limit) → confirms normally
   OR
→ Sara keeps 12% → clicks Request Discount Approval again → new request created
```

---

## Setup Guide

### 1. Enable the feature

**Sales → Configuration → Settings → Pricing**
- Toggle **Require Discount Approval** → ON
- Set **Default Global Limit (%)** → e.g. `10`
- Set **Default Per-Line Limit (%)** → e.g. `10`
- Save

### 2. Configure Discount Tiers

**Sales → L4E Approvals → Discount Tiers → New**

| Field | Example |
|---|---|
| Name | Mid-range Discount |
| Min (%) | 10 (exclusive lower bound) |
| Max (%) | 25 (inclusive upper bound) |
| Approvers | Select users (Sales Manager) |
| Approval Mode | Any one approver |

Create one tier per range. Tiers must cover all possible discount values that
could exceed any salesperson's limit — otherwise the system raises an error
asking the admin to configure a tier for that range.

**Tip:** Always create a catch-all high tier (e.g. 50–100%) so no discount is
left without routing.

### 3. Configure per-salesperson limits (optional)

**Sales → L4E Approvals → Discount Limits → New**

| Field | Example |
|---|---|
| Salesperson | Ahmed |
| Line Discount Limit | 25% |
| Company | Your Company |

Leave blank for salespersons who should use the company default.

---

## Approval Modes

Set on each **Discount Tier**:

| Mode | Behaviour |
|---|---|
| **Any one approver** | First approver to click Approve completes the request |
| **All approvers** | Every listed approver must click Approve |

---

## States & What They Mean

### Sale Order — `l4e_discount_approval_state`

| State | Meaning | Can Confirm? |
|---|---|---|
| `not_required` | Discount within limit, no approval needed | ✅ Yes |
| `pending` | Approval request open, waiting for decision | ❌ No |
| `approved` | Approver approved the discount | ✅ Yes |
| `refused` | Approver refused — salesperson must act | ❌ No |

### Approval Request — `state`

| State | Meaning |
|---|---|
| `pending` | Awaiting approver decision |
| `approved` | Fully approved |
| `refused` | Refused with a reason |
| `cancelled` | Cancelled (e.g. when a new request replaces it) |

---

## UI Elements on Sale Order

| Element | Visible When | Purpose |
|---|---|---|
| **Disc. Approval** smart button | Always (count shows) | Jump to all approval requests for this order |
| **⚠ Yellow banner** | State = pending | "Discount Approval Pending — waiting for decision" |
| **🔴 Red banner** | State = refused | "Discount Approval Refused — adjust or re-request" |
| **🔵 Blue banner** | Discount exceeds limit, state = not_required | "Discount Limit Exceeded — click to request approval" |
| **Request Discount Approval** button | Discount exceeds limit + not pending/approved | Creates the approval request |
| **⚠ Over Limit** flag | On each order line | Highlights which specific lines are over the limit |

---

## Security & Access

| Group | Access |
|---|---|
| `Discount Salesperson` | Can view their own discount limit record |
| `Discount Manager` | Can view/manage all discount limits, configure tiers, approve requests |

Row-level security ensures salespersons can only see their own limit records.

---

## Configuration Parameters

Stored as `ir.config_parameter`:

| Key | Default | Description |
|---|---|---|
| `l4e_discount_approval.required` | `False` | Master on/off switch |
| `l4e_discount_approval.default_global_limit` | `0.0` | Fallback global limit % |
| `l4e_discount_approval.default_line_limit` | `0.0` | Fallback per-line limit % |

---

## Module Info

| | |
|---|---|
| **Version** | 19.0.1.0.0 |
| **Depends** | `sale_management`, `mail` |
| **License** | LGPL-3 |
| **Author** | L4E |
