# Functional Requirements Specification
## Cabinet Door Configurator — Frappe / ERPNext

| | |
|---|---|
| **Document** | Functional Requirements Specification (FRS) |
| **System** | Cabinet Door Configurator |
| **Platform** | Frappe v16.33.1 / ERPNext v16.34.2, app `poc` |
| **Source system** | Epicor / Infor Design Studio CPQ — ruleset `JS-CabinetDoor-A-Rev02`, ruleset name `CONFIGURE` |
| **Version** | 1.0 |
| **Date** | 2026-09-18 |
| **Author** | Savyant Systems |
| **Status** | Draft for client review |

### Revision history

| Ver | Date | Author | Change |
|---|---|---|---|
| 1.0 | 2026-09-18 | Savyant Systems | Initial issue. Documents the delivered proof of concept and the requirements for a full build. |

---

## 1. Purpose

This document specifies the functional requirements for a cabinet door configurator to run on Frappe/ERPNext, replacing or complementing the client's existing Epicor/Infor **Design Studio** CPQ ruleset.

It serves three audiences:

1. **The client**, as a statement of what was demonstrated and what a full build would cover.
2. **The delivery team**, as the requirement baseline for estimation and construction.
3. **Test**, as the source of acceptance criteria.

Each requirement carries a status:

| Status | Meaning |
|---|---|
| **Implemented** | Built and verified in the proof of concept. |
| **Deferred** | Understood and specified, not built in the POC. Scheduled for a later phase. |
| **Blocked** | Cannot be built until the client supplies a missing artifact (see §10). |

---

## 2. Background

The client supplied a Design Studio ruleset export and a screen recording of the configurator in use. Analysis of the export established its scale:

| Element | Count |
|---|---|
| File size | 5,627 lines |
| `ComponentAttribute` (configurable attributes) | 95 |
| `Rule` nodes | 530 |
| — of which disabled (`Enabled="false"`) | 109 (21%) |
| `Screen` / `ScreenOption` | 79 / 105 |
| `Detail` (printed spec lines) | 120 |
| `Range` (per-unit min/max/increment) | 36 |
| `Message` (validation) | 46 |
| `RuleSet` includes (external sub-rulesets) | 7 |

Four structural characteristics drive the design:

1. **Dual-unit modelling.** Every dimension exists twice — an imperial attribute and a metric one — with different ranges and increments per unit. All rule arithmetic is written against the imperial values regardless of the operator's selection.
2. **Array-typed dividers.** Rail and stile dividers are `NumberArray` attributes indexed by a loop counter (`RailDividerHeightImperial[RailNumber]`), a repeating sub-structure rather than flat fields.
3. **Derived values from nested condition trees.** Part numbers, collapse adjustments and panel geometry are computed through deeply nested `Condition` → `Variable` rules.
4. **An assembled print layer.** An `OrderDetails` category with an incrementing `DetailSeq` cursor builds a formatted specification sheet as the buyer configures.

**The export is not self-contained.** It references external artifacts that were not supplied. See §10 — this is the principal risk to a full build.

---

## 3. Glossary

| Term | Meaning |
|---|---|
| **Collapse** | Automatic reduction of frame member widths when the finished panel would fall below the minimum panel size. |
| **Rail** | Horizontal frame member, or a horizontal divider within the door opening. |
| **Stile** | Vertical frame member, or a vertical divider. |
| **Inside profile** | The machined edge where the frame meets the panel. |
| **Outside profile** | The machined edge on the outer perimeter of the door. |
| **Reveal** | Visible offset between adjacent surfaces. |
| **Panel** | A field bounded by frame members and dividers. A door with 2 rails and 1 stile divider has 6 panels. |
| **IPN** | Internal Part Number. |
| **`X-IPNResolution`** | The external matrix that resolves a configuration to a catalogue part number. |
| **OrderDetails** | The ruleset's printed specification output category. |
| **Catalogue item** | A saved, named configuration that preloads every option (e.g. "104 Shaker"). |

---

## 4. Scope

### 4.1 In scope (proof of concept)

The POC implements a **vertical slice**: one door family configured end to end, with the structurally difficult behaviour built for real rather than mocked.

- Product lines **SQUARE** (90° frame) and **MITRE** (45° frame); MDF and Slab are selectable and modelled at tile level only.
- Approximately 30 configurable attributes of the 95, chosen to exercise every structural pattern in the source ruleset.
- Dual imperial/metric entry with fractional display to 1/16".
- Up to 3 rail dividers and 3 stile dividers, with per-index validation and a computed panel grid (max 16 panels).
- Collapse / minimum-panel-size arithmetic, transcribed from source.
- Live scale drawing of the configured door.
- Specification sheet, ERPNext quotation, and reusable catalogue items.

### 4.2 Out of scope (proof of concept)

| Excluded | Rationale |
|---|---|
| Generic XML ruleset importer and expression interpreter | Deliberate. The engine surface is small; the domain arithmetic is the hard part. A generic engine adds cost without de-risking the build. |
| The remaining ~65 attributes (finishing, paint, stain, glaze, lacquer, sheen, edge wrap, applied moulding variants, arches, mullion arrangements) | Phase 2. Structurally similar to what is built. |
| Ethos, MDF, SLAB, WRAP, DD product lines (full behaviour) | Their logic lives in sub-rulesets not supplied (§10). |
| BOM / cut-list explosion | Phase 2. |
| Pricing engine | POC uses placeholder pricing (area × species rate), clearly labelled as such. |
| Migration of existing catalogue data | Phase 2, and dependent on §10. |

---

## 5. Functional requirements

### 5.1 Order line context

| ID | Requirement | Status |
|---|---|---|
| FR-001 | The configurator shall capture a **Line Number** (integer, default 1) and **Quantity** (decimal, default 1) for the configured item. | Implemented |
| FR-002 | Each configuration shall be identified by a unique **Configuration Name**. | Implemented |
| FR-003 | The system shall display the resolved **Configured Part Number** read-only at all times. | Implemented |

### 5.2 Catalogue and product selection

| ID | Requirement | Status |
|---|---|---|
| FR-010 | The operator shall select either a saved **catalogue item** or the literal value `CONFIGURE` to begin. | Implemented |
| FR-011 | Selecting a catalogue item shall preload every configurable option, including divider rows, without altering the current document's identity (name, line number, quantity). | Implemented |
| FR-012 | The **Product** shall be selected from a row of large image tiles — Square (90° Frame), Mitre (45° Frame), MDF, Slab — with the selected tile visually distinguished. | Implemented |
| FR-013 | Product tiles shall be keyboard operable and expose their selected state assistively. | Implemented |
| FR-014 | Any configuration may be flagged as a catalogue item, after which it appears in the catalogue picker for all users. | Implemented |

### 5.3 Units of measure

| ID | Requirement | Status |
|---|---|---|
| FR-020 | The operator shall select **Measurement Units** of Imperial or Metric, presented as a radio group. | Implemented |
| FR-021 | Imperial dimensions shall be entered and displayed as fractions to 1/16" (e.g. `24 3/16`). Input shall also accept whole numbers and decimals. | Implemented |
| FR-022 | Metric dimensions shall be entered and displayed in millimetres to one decimal place. | Implemented |
| FR-023 | The system shall store **imperial as the canonical unit** and derive metric values from it, mirroring the source ruleset. All rule arithmetic shall operate on imperial values regardless of the operator's selection. | Implemented |
| FR-024 | Switching units shall convert all dimensions without loss: a value entered in imperial, converted to metric and back, shall return the identical fraction. | Implemented |
| FR-025 | Fields not relevant to the selected unit shall be hidden, not merely disabled. | Implemented |
| FR-026 | **Thickness U/M** shall be selectable independently of Measurement Units, per the source ruleset. | Implemented |

### 5.4 Material and construction

| ID | Requirement | Status |
|---|---|---|
| FR-030 | The operator shall select a **Frame Species** (mandatory) and **Panel Species**. | Implemented |
| FR-031 | Species lists shall be filterable by group (Frame, Miter, MDF, CornerPegs), reproducing the source `OptionListGroup` behaviour. | Implemented |
| FR-032 | The operator shall select a **Door Type** of Door or Drawer Front, as a radio group. | Implemented |
| FR-033 | The operator shall select a **Thickness** from a constrained list (3/4", 13/16" imperial; 19, 20.6 metric). | Implemented |
| FR-034 | The operator shall select a **Panel Type** (Raised, Recessed, Open Panel, Slab). | Implemented |
| FR-035 | The operator shall select **Corner Pegs**, defaulting to the explicit value `None`. | Implemented |

### 5.5 Profiles

| ID | Requirement | Status |
|---|---|---|
| FR-040 | The operator shall select an **Inside Frame Profile** and an **Outside Profile**, both mandatory. | Implemented |
| FR-041 | Profile selection shall be available through a **visual picker** presenting each profile's machined cross-section in a grid. | Implemented |
| FR-042 | The profile list shall be filtered by the selected Product, reproducing the source `OptionListGroup` expressions. | Implemented |
| FR-043 | A **Same Inside Profile on all sides** flag (default on) shall, when set, apply the primary inside profile to right, top and bottom, hiding the per-side fields. | Implemented |
| FR-044 | An equivalent **Same Outside Profile on all sides** flag shall behave identically for outside profiles. | Implemented |
| FR-045 | Profile records shall carry the joined attributes the rules consume — `collapse`, `reveal`, `width`, `plateau`, `frame_width`, `product` — reproducing the source `.Value.<Column>` lookups. | Implemented |
| FR-046 | The operator shall select an **Applied Moulding**, defaulting to `(None)`. | Implemented (list only) |
| FR-047 | Applied moulding options shall be filtered by the selected inside profile, per source `OptionListGroup="=LeftInsideProfile"`. | Deferred |

### 5.6 Dimensions and frame widths

| ID | Requirement | Status |
|---|---|---|
| FR-050 | The operator shall enter overall **Width** and **Height**. | Implemented |
| FR-051 | Width and Height shall be constrained to 3"–200" in 1/16" increments (source range `PanelImperial`). | Implemented |
| FR-052 | Frame member widths shall be constrained to 1"–6" imperial in 1/16" increments, 25–114.5 mm metric in 0.1 increments. | Implemented |
| FR-053 | A single master **Frame Width** shall apply to all four members by default. | Implemented |
| FR-054 | A **Custom Frame Widths** flag shall reveal independent Left Stile, Right Stile, Top Rail and Bottom Rail fields, seeded from the master value. | Implemented |
| FR-055 | The system shall display derived **Inside Width** and **Inside Height** read-only, in the operator's units. | Implemented |
| FR-056 | An **Inverted Joints** flag shall be captured and carried to output. | Implemented (captured) |
| FR-057 | Inverted joints shall alter the drawn construction and the cut list. | Deferred |

### 5.7 Dividers and panel grid

| ID | Requirement | Status |
|---|---|---|
| FR-060 | The operator shall specify 0–3 **Rail Dividers** and 0–3 **Stile Dividers**. | Implemented |
| FR-061 | Changing a divider count shall resize the corresponding table and **re-space every row evenly**, reproducing the source `RailResetFlag` behaviour. | Implemented |
| FR-062 | Default rail spacing shall follow the source formula: `spacing = Height / (Total + 1)`; `centre[i] = spacing × Total − spacing × (i − 1)`. | Implemented |
| FR-063 | Divider positions entered by the operator shall be preserved across saves that do not change the divider count. | Implemented |
| FR-064 | Each divider row shall record centre position and bar width, in both units. | Implemented |
| FR-065 | The system shall compute the panel grid: `horizontal = stiles + 1`, `vertical = rails + 1`, `total = horizontal × vertical` (maximum 16). | Implemented |
| FR-066 | Each panel's position and finished size shall be computed and reported. | Implemented |
| FR-067 | Per-panel overrides of type, profile and beading shall be supported. | Deferred |

### 5.8 Hinges

| ID | Requirement | Status |
|---|---|---|
| FR-070 | The operator shall specify **Hinge Quantity** (2–4), **Hinge Side** (Left/Right) and **Distance from Edge** (5"–20"). | Implemented |
| FR-071 | Hinge fields shall be hidden when Door Type is Drawer Front. | Implemented |
| FR-072 | Hinge positions shall be drawn on the preview on the selected side. | Implemented |

### 5.9 Validation and messaging

| ID | Requirement | Status |
|---|---|---|
| FR-080 | The system shall reproduce the source ruleset's message severity model: **level 1 and 2 block** the configuration; **level 4 is advisory** and does not block. | Implemented |
| FR-081 | Blocking messages shall prevent the configuration being saved and shall state the specific member or divider index at fault. | Implemented |
| FR-082 | Advisory messages shall be displayed without obstructing progress. | Implemented |
| FR-083 | Messages shall appear both inline against the drawing and on save. | Implemented |
| FR-084 | Messages that announce an automatic adjustment shall fire only on the transition into that state, not on every subsequent save (source `.PreviousValue` semantics). | Implemented |

### 5.10 Part number resolution

| ID | Requirement | Status |
|---|---|---|
| FR-090 | The system shall resolve a **Configured Part Number** from a part-number matrix keyed on product and panel signature. | Implemented (against a stand-in matrix) |
| FR-091 | Where no matrix entry matches, the system shall fall back to `CUSTOM-<Product>`, as the source ruleset does. | Implemented |
| FR-092 | Where any panel differs from panel 1 in type, profile or beading, the configuration shall be forced to a custom part number regardless of matrix match (source `Exception` check). | Implemented |
| FR-093 | The system shall resolve against the client's live `X-IPNResolution` matrix. | **Blocked** — see §10.1 |

### 5.11 Live preview

| ID | Requirement | Status |
|---|---|---|
| FR-100 | The system shall render a **scale drawing** of the configured door showing the frame, all dividers, every panel, hinge positions and overall dimension callouts. | Implemented |
| FR-101 | The drawing shall update as the operator works, **without requiring a save**. | Implemented |
| FR-102 | Updates shall be debounced so that typing does not generate a request per keystroke. | Implemented (300 ms) |
| FR-103 | Panels shall be labelled with their numbers, ordered top-left to bottom-right. | Implemented |
| FR-104 | Recalculation shall not mark the form as modified. | Implemented |
| FR-105 | The drawing shall follow the desk theme in both light and dark mode. | Implemented |

### 5.12 Specification output

| ID | Requirement | Status |
|---|---|---|
| FR-110 | The system shall assemble a sequenced specification sheet reproducing the source `OrderDetails` / `DetailSeq` protocol: a cursor starting at 0, each block emitting at `seq`, `seq+10`, `seq+20`, then advancing by the block's span. | Implemented |
| FR-111 | Specification lines with no value shall suppress themselves. | Implemented |
| FR-112 | Per-divider and per-panel blocks shall be emitted once per item, numbered. | Implemented |
| FR-113 | Per-side profile lines shall be emitted only where a side differs from the primary. | Implemented |
| FR-114 | The Configured Part Number shall be the final line. | Implemented |
| FR-115 | The specification shall be printable through a dedicated print format. | Implemented |
| FR-116 | Debug values shall **not** appear in customer-facing output. See §11.3. | Implemented |

### 5.13 Commercial output

| ID | Requirement | Status |
|---|---|---|
| FR-120 | The operator shall create an ERPNext **Quotation** from a saved configuration. | Implemented |
| FR-121 | The system shall find or create an **Item** keyed on the configured part number, as a non-stock (made to order) item. | Implemented |
| FR-122 | The item description shall carry the full specification sheet. | Implemented |
| FR-123 | The quotation shall be created as a **draft** for commercial review. | Implemented |
| FR-124 | A line rate shall be calculated. POC uses area × species rate as an explicit placeholder. | Implemented (placeholder) |
| FR-125 | Rates shall derive from the client's real price book / cost model. | **Blocked** — see §10.1 |
| FR-126 | The configuration shall record the quotation it produced. | Implemented |

---

## 6. Business rules

Business rules are traced to the source ruleset by line reference so the two can be read side by side.

| ID | Rule | Source | Status |
|---|---|---|---|
| BR-001 | **Minimum panel size is 3.0".** The test is strictly `<`; a panel measuring exactly 3.0" is valid. | Rule captions "Minimum Height not Met…" | Implemented |
| BR-002 | **Collapse.** Where inside height or inside width falls below the minimum panel size, all four frame widths are overwritten with a computed `Collapse` value and an advisory (level 4) message is raised. The adjustment is applied *before* the operator is told. | XML ~1937–2010 | Implemented |
| BR-003 | **Collapse accumulator.** `Collapse` is computed by sequential read-modify-write, in this order: base `1.75` for a Door or `1.50` for a Drawer Front; `+0.25` if left frame `> 2.75` **and** type is Drawer Front; `+0.25` if top frame `> 3.75`; `+0.25` if top frame `> 4.75`. Order is significant. | XML 1955–1962 | Implemented |
| BR-004 | **Hinge frame minimum.** Where panel type is `Open Panel`, the frame on the hinge side may not be less than 1 3/4". Blocking, severity 2. Solid panels are exempt — an open frame has no panel bracing the hinge screw. | XML 1693–1696 | Implemented |
| BR-005 | **Divider containment.** A divider bar must lie wholly within the opening: `centre − width/2 ≥ near frame` and `centre + width/2 ≤ span − far frame`. A bar touching the frame exactly is permitted. Blocking. | XML 4223 | Implemented |
| BR-006 | **Divider overlap.** A divider must not overlap its neighbour: for rails, `centre[i] + width[i]/2 ≤ centre[i−1] − width[i−1]/2`. Bars exactly touching are permitted. Blocking. | XML 4227 | Implemented |
| BR-007 | **Divider default spacing.** `spacing = span / (total + 1)`; row *i* defaults to `spacing × total − spacing × (i − 1)`. Applied on creation and whenever the count changes. | XML 4155, 4171 | Implemented |
| BR-008 | **Panel grid.** `horizontal = stiles + 1`; `vertical = rails + 1`; `total = horizontal × vertical`. Maximum 16 panels (3×3 dividers). | XML 4425–4434 | Implemented |
| BR-009 | **Panel uniqueness exception.** If any panel differs from panel 1 in type, profile or beading, `Exception` is set and the part number is forced to custom. | XML 5500+ | Implemented |
| BR-010 | **Part number fallback.** `CUSTOM-<Product>`, with product-specific overrides (`PART` → `CUSTOM-<PartType>`). | XML 5500–5597 | Implemented |
| BR-011 | **Canonical unit.** All rule arithmetic uses imperial values. Metric is a display mirror, converted at 25.4 mm/inch. | Throughout | Implemented |
| BR-012 | **Imperial precision.** Imperial dimensions snap to 1/16" and display as reduced fractions (`8/16` → `1/2`, zero numerator dropped). | `DisplayFormat="Fraction" DisplayPrecision="1/16"` | Implemented |
| BR-013 | **Transition-only warnings.** Advisory messages that announce an automatic adjustment compare against the previous evaluation and fire only on entry into the state. | `.PreviousValue` | Implemented |
| BR-014 | **Profile side propagation.** While "same on all sides" is set, the right, top and bottom profiles track the primary and their fields are hidden. | XML 1020–1022 | Implemented |
| BR-015 | **Ethos range regime.** A narrower dimensional envelope (frame 0.25"–5", panel 0.75"–5") applies to the Ethos line. | `Range Name="Ethos"` | **Blocked** — §10.1 |

---

## 7. Data model

Seven doctypes in the `poc` application.

### 7.1 Transaction

| Doctype | Purpose | Notes |
|---|---|---|
| **Door Configuration** | The configurator itself. 79 fields — 47 operator inputs, 9 derived read-only, the remainder layout and tables. | Named by Configuration Name. Change-tracked. |
| **Door Rail Divider** (child) | Horizontal dividers. Row `idx` is the array index, replacing the source's `[RailNumber]` subscript. | Centre from bottom + bar width, both units. |
| **Door Stile Divider** (child) | Vertical dividers. | Centre from left + bar width, both units. |
| **Door Configuration Detail** (child) | Assembled specification lines. | Print sequence, description, value, visibility. |

### 7.2 Masters

| Doctype | Purpose | Seeded |
|---|---|---|
| **Door Species** | Timber species with group and placeholder rate. Stands in for the source `Species` option list. | 9 |
| **Door Profile** | Inside and outside profiles carrying the joined columns the rules consume, plus a section shape driving the drawn cross-section. | 22 |
| **Door Part Number Matrix** | Stand-in for `X-IPNResolution`. Product + panel signature → part number. | 3 |

Three catalogue items are seeded for demonstration (`104 Shaker`, `212 Two Rail Pantry`, `330 Mitre Drawer Front`).

### 7.3 Rule engine structure

Rule logic is held in framework-independent Python modules so that the arithmetic is directly testable without a database:

| Module | Responsibility |
|---|---|
| `units` | Imperial/metric conversion and fractional formatting. Replaces the source `Usr.Convert` user function. |
| `ranges` | Per-unit min/max/increment tables transcribed from the `<Range>` nodes. |
| `rules` | The ported rules, in source document order. Function names echo the source rule captions. |
| `geometry` | Panel grid computation. |
| `details` | `OrderDetails` assembly. |
| `preview` | Scale drawing generation. |
| `artwork` | Product tiles and profile cross-sections. |
| `quotation` | ERPNext item and quotation creation. |

---

## 8. User interface requirements

| ID | Requirement | Status |
|---|---|---|
| UI-001 | The configurator shall present as a single scrolling form, sectioned in the order the source screens present them: order line, product selection, material, profiles, dimensions, frame widths, dividers, hinges, preview, specification. | Implemented |
| UI-002 | Selection of Product shall use large image tiles, not a dropdown. | Implemented |
| UI-003 | Profile selection shall offer a visual grid of cross-sections. | Implemented |
| UI-004 | Two- to four-option choices (units, door type, thickness, hinge side) shall render as radio groups, not dropdowns. | Implemented |
| UI-005 | Frame member fields shall use trade terminology — Left Stile, Right Stile, Top Rail, Bottom Rail. | Implemented |
| UI-006 | Fields shall show and hide in response to the flags that govern them, rather than being disabled. | Implemented |
| UI-007 | All interactive imagery shall be keyboard operable with a visible focus indicator. | Implemented |
| UI-008 | The interface shall be legible in both light and dark desk themes. | Implemented |
| UI-009 | Imagery shall be replaced by the client's own product photography and profile artwork. | Deferred — POC artwork is drawn procedurally; see §9.3 |

---

## 9. Non-functional requirements

### 9.1 Performance

| ID | Requirement | Status |
|---|---|---|
| NFR-001 | Preview recalculation shall complete within 500 ms for a maximum configuration (16 panels). | Implemented |
| NFR-002 | Keystroke input shall be debounced to at most one recalculation per 300 ms. | Implemented |

### 9.2 Maintainability

| ID | Requirement | Status |
|---|---|---|
| NFR-010 | Rule logic shall be separable from the framework and unit-testable without a site or database. | Implemented |
| NFR-011 | Ported rules shall be traceable to the source ruleset by caption and line reference. | Implemented |
| NFR-012 | Behaviour reproduced deliberately from the source — including its quirks — shall be documented as such in code. | Implemented |

### 9.3 Assets and licensing

| ID | Requirement | Status |
|---|---|---|
| NFR-020 | No client-owned imagery shall be reproduced without supply. POC product tiles and profile cross-sections are generated procedurally and carry no third-party rights. | Implemented |

### 9.4 Data integrity

| ID | Requirement | Status |
|---|---|---|
| NFR-030 | A configuration that violates a blocking rule shall not be persistable. | Implemented |
| NFR-031 | Unit conversion shall be lossless to the 1/16" display precision across any number of round trips. | Implemented |
| NFR-032 | Seed and setup routines shall be idempotent. | Implemented |

---

## 10. Assumptions, dependencies and open items

### 10.1 Missing artifacts — **blocking for a full build**

The supplied ruleset export references, but does not contain, the following. Each blocks specific requirements. **Obtaining these is the gate on a full-build estimate.**

| # | Missing artifact | Blocks | Impact |
|---|---|---|---|
| 1 | **Option lists with their joined columns** — every `OptionListID` (`Product`, `Species`, `MouldingProfileA`, `OutsideProfileA`, `Catalogue-A`, `AppliedMoulding`, `ThicknessImperial`, …) together with the columns the rules read off them: `Collapse`, `Reveal`, `Width`, `Plateau`, `Slab`, `FrameWidth`, `Product`, `ImageLink`, `ReducedReveal`. | BR-002, BR-015, FR-042, FR-047 | The POC substitutes representative values. Real collapse and reveal arithmetic cannot be validated without these. |
| 2 | **`X-IPNResolution` part-number matrix.** | FR-090, FR-093 | Part numbers currently fall back to `CUSTOM-`. No configuration can resolve to a real catalogue part. |
| 3 | **`Usr.Convert` definition.** | FR-023 | Reimplemented from first principles. Rounding behaviour at boundaries may differ from the live system. |
| 4 | **Seven sub-rulesets** across two namespaces — `Arvin/Ethos`, `Arvin/WrapMoulding`, `Arvin/Drilling Dowel`, `Arvin/EdgeTapedSlab`, `JSTEST/Panel.A`, `JSTEST/Panel2.A`, `JSTEST/Door-Flex2D`. | BR-015, Ethos/Wrap/Slab product lines | All Ethos behaviour lives in `Arvin/Ethos`. The declared Ethos ranges in the export are never selected by any screen option, confirming the logic is external. |
| 5 | **`JSLayout` layout definition.** | UI-001 | Screen ordering inferred from the export and the supplied screen recordings. |
| 6 | **Product photography and profile artwork.** | UI-009 | POC artwork generated procedurally. |
| 7 | **Price book / cost model.** | FR-125 | POC pricing is a labelled placeholder. |

### 10.2 Assumptions

| # | Assumption |
|---|---|
| A-1 | Imperial is the system of record; metric is a presentation mirror. Confirmed by the source ruleset's arithmetic. |
| A-2 | A maximum of 3 rail and 3 stile dividers (16 panels) is sufficient. Taken from the source `0-3` range. |
| A-3 | Configured doors are made to order and therefore non-stock items in ERPNext. |
| A-4 | Quotations are created as drafts for commercial review rather than submitted automatically. |
| A-5 | The screen ordering in §5 reflects the current production flow. To be confirmed against the full screen recording. |

### 10.3 Open questions for the client

| # | Question |
|---|---|
| Q-1 | Can the seven artifacts in §10.1 be supplied? |
| Q-2 | 109 of 530 rules in the export are disabled. Are these dead, or toggled off pending a release? |
| Q-3 | The MITRE part-number rule is captioned "TEMPORARY". What is the intended behaviour? |
| Q-4 | Should the collapse behaviour (silently adjust, then warn) be preserved, or should it warn before adjusting? |
| Q-5 | Are per-panel overrides (FR-067) used in practice, or is the uniqueness exception effectively always false? |
| Q-6 | Which product lines are commercially in scope for phase 1? |

---

## 11. Observations on the source ruleset

Recorded because they affect estimation and because several are likely defects the client may wish to address during migration.

### 11.1 Maintenance state

- **109 of 530 rules (21%) are disabled.** They must still be read to understand intent, and several contain the only surviving description of superseded behaviour.
- Three of the seven included sub-rulesets live in a namespace named **`JSTEST`**.
- The first screen's title is `"Product Selection _ TEST WITH VIWEQ"`.

### 11.2 Probable defects

| # | Observation |
|---|---|
| D-1 | An attribute is named literally `0` (caption "Advanced Configuration?"). |
| D-2 | Several `Panel[...]` collection keys carry trailing spaces inside the attribute name. |
| D-3 | `FrameWidthBottomImperial` carries a metric increment of 0.1 where its three siblings use 1.0. |
| D-4 | The `Ethos` ranges are declared with inconsistent `Selected` flags and are never chosen by any screen option. |
| D-5 | One `Detail` description is written `"sys.PartNumber"` without a leading `=`, so it prints the token rather than the value. |
| D-6 | Several `Detail` blocks advance `DetailSeq` by a stride that does not match the number of lines emitted. |

### 11.3 Customer-facing debug output

A rule captioned **"Debug Screen Detail"** is **enabled** and writes `sys.ImagePath`, `sys.ImageLink`, `sys.PartNumber` and `root.imagelink` into the `OrderDetails` category — the same category that produces the customer specification sheet. A second enabled rule assigns a live debug variable `TESTMatrixPartNumber`.

These are not reproduced in the POC (FR-116), and the client may wish to review them in the live system.

---

## 12. Acceptance criteria

### 12.1 Verification approach

| Layer | Method | Coverage |
|---|---|---|
| Rule arithmetic | Unit tests, no database required | 40 tests |
| End-to-end behaviour | Scripted walkthrough against a live site | 45 assertions |
| Interface | Browser verification at each milestone | Manual |

Commands:

```
bench --site <site> migrate
bench --site <site> execute poc.setup.install.execute      # idempotent seed
bench --site <site> execute poc.tests.demo_walkthrough.run # 45 assertions
python -m unittest poc.tests.test_configurator             # 40 unit tests
```

### 12.2 Acceptance scenarios

| # | Scenario | Expected | Traces |
|---|---|---|---|
| AC-01 | Open a catalogue item. | Every option preloads; the drawing renders; the form is not marked modified. | FR-011, FR-104 |
| AC-02 | Select each product tile in turn. | Selection moves; the drawing updates; the tile is visibly selected. | FR-012 |
| AC-03 | Configure a 24" × 30" Square door with 2 1/4" frames. | Single panel; inside 19 1/2" × 25 1/2"; part number resolves from the matrix. | FR-050, FR-065, FR-090 |
| AC-04 | Set rail dividers to 2. | Two rows seed at 20" and 10"; three panels; drawing shows three fields. | FR-061, BR-007 |
| AC-05 | Move a divider by hand, then save twice. | The entered position is preserved on both saves. | FR-063 |
| AC-06 | Position a divider inside the bottom frame. | Blocking message naming the divider index; save prevented. | BR-005, FR-081 |
| AC-07 | Position two dividers so their bars overlap. | Blocking message naming both indices. | BR-006 |
| AC-08 | Reduce height until the panel falls below 3". | Frame widths are rewritten; an advisory message explains; save succeeds. | BR-002, BR-003 |
| AC-09 | Re-save the collapsed configuration. | No repeat advisory. | BR-013 |
| AC-10 | Set panel type to Open Panel with a 1 1/2" hinge-side frame. | Blocking message. | BR-004 |
| AC-11 | Set panel type to Raised with the same frame. | No message — solid panels are exempt. | BR-004 |
| AC-12 | Switch units to Metric and back. | 24" → 609.6 mm → 24"; no drift in any dimension. | FR-024, NFR-031 |
| AC-13 | Open the profile picker. | Cross-sections render; the list excludes profiles for other products. | FR-041, FR-042 |
| AC-14 | Print the specification. | Lines in ascending sequence; part number last; no debug values. | FR-110, FR-114, FR-116 |
| AC-15 | Create a quotation. | Draft quotation; item named by part number; specification in the description; a rate present. | FR-120–FR-124 |
| AC-16 | Save a configuration as a catalogue item and load it into a new document. | Options transfer; the new document keeps its own name, line number and quantity. | FR-011, FR-014 |

**Current status: 45/45 walkthrough assertions and 40/40 unit tests passing.**

---

## 13. Indicative phasing

| Phase | Content | Depends on |
|---|---|---|
| **0 — Proof of concept** | Delivered. Vertical slice as specified above. | — |
| **1 — Data foundation** | Import the real option lists, part-number matrix and profile artwork. Validate collapse and reveal arithmetic against live outputs. | §10.1 items 1, 2, 6 |
| **2 — Attribute completion** | Remaining ~65 attributes: finishing, paint, stain, glaze, lacquer, sheen, edge wrap, applied moulding, arches, mullion arrangements. | Phase 1 |
| **3 — Product lines** | Ethos, MDF, Slab, Wrap, DD — requires the sub-rulesets. | §10.1 item 4 |
| **4 — Manufacturing output** | BOM and cut-list explosion; per-panel overrides; inverted joints. | Phase 2 |
| **5 — Commercial** | Real pricing, discount structures, order conversion. | §10.1 item 7 |

---

*End of document.*
