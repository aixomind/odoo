# l4e_custom_approval — Odoo 19 Custom Approval Module

## Overview
A dynamic, extensible approval framework for Odoo 19 covering:
- **CRM PO Fields** (Date, No, Amount, Attachment)
- **Sale Order Confirmation Approval** (with auto-confirm + CRM Won on approval)
- **Discount Limit & Approval Workflow** (per-salesperson limits, approval gate)
- **Dynamic Approval Framework** (reusable categories for any future model)

---

## Installation

1. Copy `l4e_custom_approval/` to your Odoo addons path.
2. Update the Apps list in Odoo.
3. Install **L4E Custom Approval**.

**Dependencies installed automatically:**
- `sale_management`, `crm`, `approvals`, `mail`, `sale_discount`

On install, two **Approval Categories** are auto-created:
- `Sale Order Done`
- `Discount Approval`

---

## Feature Breakdown

### 1. CRM PO Fields
Go to any CRM Opportunity → **PO Information** tab:
| Field | Type |
|-------|------|
| PO Date | Date |
| PO No | Char |
| PO Amount | Monetary |
| PO Attachment | Binary (multi) |

A yellow ribbon appears on the CRM form when PO fields are incomplete.  
A computed boolean `po_fields_filled` tracks completion.

---

### 2. Sale Order Approval

**Enable:** Sales → Configuration → Settings → *Require Approval Before Confirming Sale Order*

**Flow:**
```
Quotation (Draft/Sent)
    ↓  Click "Request Approval & Confirm"
    ↓  [Validate CRM PO Fields]
    ↓  [Check Discount Approval if needed]
    ↓  Creates Approval Request → "Sale Order Done" category
    ↓  Approval request submitted
    ↓  Approver approves in Approvals module
    ↓  Sale Order auto-confirmed (bypass)
    ↓  CRM Lead → moved to Won stage
    ↓  Salesperson notified via Email + Chatter
```

- `l4e_approval_state`: `not_required | pending | approved | refused`
- Refused → email + chatter notifies salesperson, SO stays in draft

---

### 3. Discount Approval

**Enable:** Sales → Configuration → Settings → *Enable Discount Approval Workflow*

**Setup Limits:**
- **Company-wide defaults**: Set `Global Discount Limit` and `Line Discount Limit` in Settings
- **Per-salesperson**: Sales → L4E Approvals → Discount Limits

**Security Group:** Sales → *Discount Sales Person*
- Only users in this group have their discounts checked against limits
- *Discount Manager* group can configure limits and approve requests

**Flow:**
```
Salesperson enters discount (global or line-level)
    ↓  onchange checks limit for that user
    ↓  If exceeded → l4e_discount_needs_review = True
    ↓  Warning banner appears on SO
    ↓  "Request Discount Approval" button shown
    ↓  Cannot confirm SO until discount approved (or stage blocked)
    ↓  Click button → Approval Request created → "Discount Approval" category
    ↓  Approver approves
    ↓  l4e_discount_approval_state = 'approved'
    ↓  Line review flags cleared
    ↓  Email + chatter to salesperson
```

---

### 4. Dynamic Approval Framework

Each `approval.category` now has:
| Field | Purpose |
|-------|---------|
| `l4e_approval_type` | `sale_order / discount / custom` |
| `l4e_model_id` | Link to any Odoo model (for custom types) |
| `l4e_auto_validate` | Auto-process linked record on approval |
| `l4e_notify_salesperson` | Email + chatter on approval/refusal |

To add a new approval type:
1. Create a new `approval.category` with `l4e_approval_type = custom`
2. Link it to your model via `l4e_model_id`
3. Extend `approval_request.py` with a handler for your type

---

## Mail Templates

| Template | Trigger |
|----------|---------|
| Sale Order Approval — Approved | SO approval approved |
| Sale Order Approval — Refused | SO approval refused |
| Discount Approval — Approved | Discount approved |
| Discount Approval — Refused | Discount refused |

---

## Menus

**Sales → L4E Approvals**
- Sale Order Approvals
- Discount Approvals
- Discount Limits *(managers only)*

---

## Configuration Parameters (ir.config_parameter)

| Key | Default |
|-----|---------|
| `l4e_custom_approval.sale_order_approval_required` | `False` |
| `l4e_custom_approval.discount_approval_required` | `False` |
| `l4e_custom_approval.global_discount_limit` | `0.0` |
| `l4e_custom_approval.line_discount_limit` | `0.0` |

---

## Author
**L4E** | Odoo 19 | License: LGPL-3
