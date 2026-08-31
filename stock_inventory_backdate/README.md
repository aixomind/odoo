# Inventory Adjustment Backdating — Odoo 18

Odoo 18 · depends on `stock_account`

Validating an inventory adjustment stamps "now" on several records at once, and
Odoo offers no supported way to correct that afterwards, so an adjustment keyed
in today can never be reported in the period it belongs to. This module adds a
wizard that moves a validated adjustment — and everything it created — to a
chosen past date.

This is the **Odoo 18** edition. The 19.0 build lives separately: Odoo 19
removed `stock.valuation.layer` entirely and the two cannot share code.

## Records rewritten

```
stock.move.date                        (datetime, user timezone → UTC)
  ├─ stock.move.line.date              (datetime)
  ├─ stock.valuation.layer.create_date (datetime)
  └─ account.move.date                 (date)
       └─ account.move.line.date       (date)
            └─ account.analytic.line.date (date)
stock.quant.last_count_date            (recomputed, optional)
```

Odoo 18 exposes every link as a plain ORM relation on `stock.move`, so nothing
has to be discovered at runtime and every `UPDATE` is static SQL:

| Target | Reached by |
| --- | --- |
| Valuation layers | `stock.move.stock_valuation_layer_ids` |
| Journal entries | `stock.move.account_move_ids` (inverse of `account.move.stock_move_id`), unioned with `stock.valuation.layer.account_move_id` |
| Analytic lines | `stock.move.analytic_account_line_ids`, unioned with `account.analytic.line.move_line_id` |

The layer path to the journal entry is kept alongside the move-side one because
on older data the back-reference is not always populated.

## Usage

**Inventory → Date Corrections → Backdate Inventory Adjustments**

1. **Find** — set the date range the adjustments were validated in (defaults to
   today), optionally narrowing by product, location or reference, then press
   *Load Adjustments*. Only `state = done` moves with `is_inventory = True` in
   the selected company are returned.
2. **Pick** — the list shows each adjustment with its current date, its
   valuation-layer count and the journal entries attached to it. Untick the rows
   you want to leave alone; *Select All* / *Unselect All* are there for bulk runs.
3. **Set the new date** — a date plus a time of day, entered in your own
   timezone and converted to UTC for the datetime fields. The `account.move`
   side takes the plain date.
4. **Apply** — every update runs in the current request transaction. If any
   statement fails, the whole batch rolls back and nothing changes.

## Importing a past-dated counting sheet

**Inventory → Date Corrections → Past Inventory Counts**, then *Favorites →
Import records*. Three columns are enough:

| Product | Counted Date | Counted Quantity |
| --- | --- | --- |
| GHEE ROAST | 2025-05-20 | 100 |
| CASHEW 500G | 2025-05-20 | 42 |

Each row is applied on creation. There is no separate "post" step: the row's
`create()` records the count on the quant, calls Odoo's own
`_apply_inventory()`, and then dates everything it produced — stock move, move
lines, valuation layer, journal entry and its items — to the counted date.

Optional columns:

| Column | Effect |
| --- | --- |
| **Location** | Count somewhere other than the warehouse's default stock location |
| **Lot/Serial** | Required for products tracked by lot or serial |
| **Counted Time** | Time of day for the move/layer timestamp (default 09:00) |
| **Apply on Import** | Set to `0` to stage rows for review; apply later with the button |
| **Cost Price** | Unit cost this stock actually carried on the counted date — see below |

### Costing a count at its historical price

Left blank, a count is valued the way Odoo would value any inventory
adjustment: at whatever the product's cost happens to be *right now*. For a
count you are entering today about stock from months ago, that is usually
wrong — the cost has often moved since.

Set **Cost Price** and, once the count posts, its valuation layer and journal
entry are corrected to `movement quantity × Cost Price`, so the Inventory
Valuation report reads the value this stock actually carried on the counted
date rather than today's cost applied retroactively.

```
Counted Quantity: 10   Cost Price: 100   →  layer value: 1,000
```

Only this count's own layer and journal entry lines are touched. The
product's `standard_price` — and, on AVCO, its running average cost — are
**not** recalculated. This is a correction to the historical record, not a
re-run of costing: every move made between the counted date and today keeps
whatever cost it already posted at. On AVCO in particular, that means the
average cost the system used for later moves is not retroactively fixed by
inserting an earlier-dated cost — only the count's own line is.

The journal entry side is corrected by shifting its two lines — the stock
valuation account and the offsetting account — by the value difference, in
place. That only works on the plain two-line shape `_apply_inventory()`
actually produces; if something else has since reshaped the entry, the
quantity/date side of the count still applies but the value is left alone,
and a note to that effect appears in the row's *Result* field instead of
being silently skipped.

Leaving **Cost Price** at `0` is treated the same as leaving it blank — there
is currently no way to value a count at a genuine zero cost through this
column.

### Why this avoids the renumbering problem

The journal entry is created with `force_period_date` set to the counted date,
which `stock_account` honours when it builds the entry. The entry is therefore
*born* in the right period and its number is drawn from that period's sequence —
so unlike backdating an existing adjustment, nothing needs renumbering and no
gap is left behind. This is the cleaner of the two routes; the wizard exists for
adjustments that were already validated.

The move and layer dates still get rewritten, because `_action_done()` hardcodes
`now()` with no hook. That happens a moment later, in the same transaction.

### A count is a movement, so it shifts every later figure

Odoo's on-hand is the running total of every movement ever posted. A count dated
in the past is still a movement, so inserting one raises or lowers **today's**
on-hand by the same amount. There is no way to change a past figure alone — the
same reason a backdated deposit changes your bank balance today, not just
yesterday's statement.

So this does not do what it looks like it should:

| Product | Counted Date | Counted Quantity | | Result |
| --- | --- | --- | --- | --- |
| GHEE ROAST | 2026-07-23 | 50 | | 23rd reads 50, **and today reads 50** |

If the reality is *50 yesterday, 30 today*, then 20 units left in between — and
that is a real movement that has to be recorded. State both levels:

| Product | Counted Date | Counted Quantity | | Result |
| --- | --- | --- | --- | --- |
| GHEE ROAST | 2026-07-23 | 50 | | +20 posted on the 23rd |
| GHEE ROAST | 2026-07-24 | 30 | | −20 posted on the 24th |

Now the report reads 50 on the 23rd and 30 today, and the 20 that left is
visible as stock movement rather than hidden.

Rows are applied **oldest first**, whatever order the sheet lists them in, since
each count measures against the level the earlier ones left behind. Sorting the
sheet by date is therefore optional, but it makes the intent readable.

### Inserting a count into history without disturbing today

This is the part that catches everyone, so here it is worked through.

A product has one adjustment already, made in native Odoo: **+9 on 2 May 2026**.
On-hand today is **9**. You now discover you had **10** on **31 March 2026** and
want that recorded — without today changing.

Import the 31 March row alone and you get this:

| Date | Movement | Running total |
| --- | --- | --- |
| 31 Mar 2026 | **+10** ← your row | 10 |
| 2 May 2026 | +9 *(unchanged)* | 19 |
| today | — | **19** |

The 2 May line still reads `+9`. It never held a total — when you made that
adjustment Odoo recorded *"9 units arrived on 2 May"*, and on-hand read 9 only
because `0 + 9 = 9`. Odoo stores no "stock was N on this date" record anywhere;
every figure you see is the running sum of movements up to that point. Insert
`+10` before `+9` and 19 is simply what the arithmetic gives.

Add a second row and it lands where you want:

| Product | Counted Date | Counted Quantity | Counted Time |
| --- | --- | --- | --- |
| BEEF SATAY PREMIUM SPICY | 2026-03-31 | 10 | |
| BEEF SATAY PREMIUM SPICY | 2026-05-02 | 9 | 23:00 |

| Date | Movement | Running total |
| --- | --- | --- |
| 31 Mar 2026 | **+10** | **10** |
| 2 May 2026 | +9 *(existing)* **−10** *(second row)* | **9** |
| today | — | **9** |

Net movement on 2 May is now `−1`, which is what that day's adjustment would
have posted all along had the 10 units been in the system when it was made.

**The `23:00` matters.** 2 May already has a movement on it. The default 09:00
could place the new row *before* it, measuring against 10 instead of 19 and
posting `−1` instead of `−10`, leaving today at 18. A late Counted Time
guarantees it lands last that day. Only needed on dates that already have
activity.

**The recipe:** one row for the historical date, then one row for the next date
that already has stock activity restating the total there. The second row is
what absorbs the difference; without it the insertion carries all the way
through to today.

### One row failing does not lose the others

An import runs many rows in one transaction, so each row applies inside its own
savepoint. A row that fails is kept with `Failed` status and the reason in its
*Result* field; fix the sheet value and press **Apply** to retry it. Without
this, one bad product name would roll back the whole sheet.

Rows are validated before anything is posted: the product must be storable
goods, the quantity non-negative, a lot given for tracked products, and the
counted date outside any accounting lock date.

## Why raw SQL

The ORM refuses `write()` on the `date` of a posted `account.move`, and writing
to `stock.move.date` re-triggers valuation logic that would create *new* layers
instead of correcting the existing ones. The wizard therefore issues direct
`UPDATE` statements, but never calls `cr.commit()` — leaving the commit to
Odoo's own request handling is what keeps the batch atomic. `flush_all()` runs
before the first statement and `invalidate_all()` after the last, so no stale
cached value survives.

## Safety

| Guard | Behaviour |
| --- | --- |
| Security group | *Backdate Inventory Adjustments* (implies Inventory Administrator). Granted to the system administrator on install; assign it to anyone else explicitly. It gets its own `ir.module.category` — groups sharing a category render as a single selection on the user form, so reusing the Inventory category would make it compete with Inventory User / Administrator. |
| State check | Refuses moves that are not `done`, and moves that are not inventory adjustments. |
| Lock dates | Blocks a target date on or before the company's `hard_lock_date` or `fiscalyear_lock_date`. Only a member of *Settings* can tick **Ignore Accounting Lock Dates** to override. (Odoo 18 has no `period_lock_date`; the tax, sale and purchase lock dates do not apply to a miscellaneous stock entry.) |
| Audit trail | One `inventory.backdate.log` record per adjustment: old date, new date, old and new accounting date, journal entries, counts of touched rows, user, timestamp. Read-only, no create or edit from the UI. |
| Chatter | Optionally posts the change on each affected journal entry. |
| Atomicity | All statements in one transaction. |

## Renumbering the journal entry

A journal entry number encodes its period. Move `STJ/2026/07/0938` to May 2025
and the date reads `20/05/2025` while the number still says `2026/07`.

Ticking **Renumber Journal Entry** fixes that: the name is cleared and the
sequence mixin assigns the next one. Because `account.move` scopes its sequence
lookup to the entry's own date, and the date has already been rewritten by the
time this runs, the new number is drawn from the new period — `STJ/2025/05/…`.
This is the same route Odoo's own *Resequence* wizard takes.

It is **off by default**, for a reason worth stating plainly:

> Renumbering leaves a gap where the entry used to be — `0937, [gap], 0939` in
> `2026/07`. A gap is exactly what sequence-integrity checks and auditors look
> for. In several jurisdictions a hole in the numbering is a more serious
> finding than a number whose period no longer matches its date. Decide which
> of the two you would rather explain.

Two guards:

- **Hash-secured journals are refused.** If the journal has *Secure Posted
  Entries with Hash* enabled, renaming a posted entry would break the hash
  chain, so the entry is skipped and the reason recorded on the log.
- **Failures do not cost you the date change.** Each entry is renumbered inside
  its own savepoint. The backdating is the point of the exercise and is already
  written; a numbering problem is recorded on the log rather than rolling the
  batch back.

Either way the log records what happened — old number, new number, or why it
was skipped — and the history's *Journal Entry Numbers* column shows the entry
as it now stands.

## Differences from the Odoo 19 build

| | Odoo 18 (this) | Odoo 19 |
| --- | --- | --- |
| Group category | `res.groups.category_id` → own `ir.module.category` | `res.groups.privilege_id` → own `res.groups.privilege` |
| Valuation record | `stock.valuation.layer` (`create_date`) | none — value lives on `stock.move`; `product.value` holds manual adjustments only |
| Entry link | `stock.move.account_move_ids` | `stock.move.account_move_id` |
| Lock dates | `hard_lock_date`, `fiscalyear_lock_date` | plus `period_lock_date` where present |
| Search Group By | `<group expand="0" string="Group By">` | bare `<group>` — 19's RNG dropped both attributes |

## Files

```
stock_inventory_backdate/
├── __manifest__.py
├── doc/
│   └── past_inventory_counts_template.xlsx
├── models/
│   ├── backdate_common.py                timezone, lock-date checks - shared by both routes
│   ├── stock_move.py                     date rewrite + value correction, both by raw SQL
│   ├── inventory_past_count.py           past-count row: apply, cost correction, retry
│   └── inventory_backdate_log.py         audit model
├── wizard/
│   ├── inventory_backdate_wizard.py      search, checks, SQL, logging
│   └── inventory_backdate_wizard_views.xml
├── security/
│   ├── backdate_security.xml             category + group
│   └── ir.model.access.csv
└── views/
    ├── inventory_backdate_log_views.xml  list / form / search
    ├── inventory_past_count_views.xml    list / form / search / import help
    └── menu.xml
```
