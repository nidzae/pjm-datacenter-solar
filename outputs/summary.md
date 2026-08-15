# US Gas-Plant / Solar / Data-Center Land Screen — Summary

Fleet: **1277 operating US (lower-48) gas plants**, **475.5 GW** total nameplate, across 48 states and 50 balancing authorities.

Parameters: overbuild=1.3, power density default 91 MW/mi² (7 ac/MW), DC parcel 150 acres, NSRDB TMY capacity factor (PVWatts, AC). Areas in mi².

## Qualifying plants & hostable data-center load (GW) — forest EXCLUDED (conservative default)

| Buffer | Gas cap | Plants qualifying | Hostable load (GW) |
|---|---|---|---|
| 10 km | 5% | 734 | 126.7 |
| 10 km | 10% | 744 | 132.1 |
| 10 km | 20% | 773 | 146.0 |
| 5 km | 5% | 369 | 22.0 |
| 5 km | 10% | 379 | 23.7 |
| 5 km | 20% | 416 | 31.6 |

## Qualifying plants & hostable data-center load (GW) — forest INCLUDED (less aggressive)

| Buffer | Gas cap | Plants qualifying | Hostable load (GW) |
|---|---|---|---|
| 10 km | 5% | 873 | 178.1 |
| 10 km | 10% | 885 | 185.8 |
| 10 km | 20% | 922 | 205.9 |
| 5 km | 5% | 453 | 29.5 |
| 5 km | 10% | 460 | 31.1 |
| 5 km | 20% | 498 | 39.0 |

## Power-density sensitivity (10 km, 10% gas cap, forest excluded)

| acres/MW | MW/mi² | Plants qualifying | Hostable load (GW) |
|---|---|---|---|
| 5 | 128.0 | 809 | 163.1 |
| 7 | 91.4 | 744 | 132.1 |
| 8 | 80.0 | 719 | 117.8 |

## Hostable load — whole-plant vs including partial data centers (10 km, forest excl.)

A plant that can't host a *full-nameplate* data center can usually still host a *smaller* one matched to its available solar land. Hostable load = min(nameplate, headroom × nameplate).

| Gas cap | Whole-plant qualifiers (GW) | Including partial DCs (GW) |
|---|---|---|
| 5% | 126.7 | 233.9 |
| 10% | 132.1 | 239.7 |
| 20% | 146.0 | 252.4 |

## Qualifying nameplate by state (10 km, 10% gas cap, 7 ac/MW) — vs paper Fig. 4

| State | Forest excl. GW | Forest incl. GW | Paper Fig. 4 (GW) |
|---|---|---|---|
| TX | 25.9 | 33.6 | — |
| CA | 14.1 | 14.1 | — |
| AZ | 10.7 | 10.7 | — |
| IL | 8.3 | 9.1 | 16 |
| GA | 1.3 | 8.2 | — |
| MS | 0.9 | 6.3 | — |
| WI | 6.0 | 6.2 | — |
| IN | 5.2 | 6.1 | — |
| CO | 6.1 | 6.1 | — |
| MO | 5.1 | 5.8 | — |
| OK | 4.4 | 5.4 | — |
| OH | 4.0 | 5.2 | 12 |
| VA | 0.0 | 5.2 | 10 |
| MI | 3.1 | 3.9 | — |
| FL | 2.8 | 3.9 | — |
| MN | 3.0 | 3.7 | — |
| NC | 0.7 | 3.7 | — |
| IA | 2.9 | 3.5 | — |
| OR | 3.0 | 3.0 | — |
| PA | 1.4 | 2.9 | 17 |
| KS | 2.9 | 2.9 | — |
| AR | 1.6 | 2.9 | — |
| AL | 0.4 | 2.8 | — |
| LA | 1.9 | 2.7 | — |
| NY | 1.5 | 2.7 | — |
| NM | 2.5 | 2.5 | — |
| MA | 0.0 | 2.4 | — |
| TN | 1.1 | 1.8 | — |
| NE | 1.6 | 1.6 | — |
| WA | 0.6 | 1.6 | — |
| SD | 1.5 | 1.5 | — |
| MD | 0.4 | 1.5 | — |
| SC | 0.5 | 1.5 | — |
| KY | 0.5 | 1.4 | — |
| ID | 1.2 | 1.2 | — |
| NJ | 0.3 | 1.2 | 6 |
| UT | 1.1 | 1.1 | — |
| ME | 0.0 | 1.0 | — |
| RI | 0.0 | 0.8 | — |
| DE | 0.8 | 0.8 | — |
| CT | 0.2 | 0.8 | — |
| NV | 0.7 | 0.7 | — |
| ND | 0.7 | 0.7 | — |
| WY | 0.4 | 0.4 | — |
| MT | 0.4 | 0.4 | — |
| DC | 0.0 | 0.0 | — |
| NH | 0.0 | 0.0 | — |
| **Total (5 paper states)** | **14.1** | **23.6** | **61** |

## How to read the aggregate GW (important)

- **Per-plant verdicts are independent and valid**; each plant is screened against the developable land in its *own* 10 km buffer. But ~67% of US plants have a neighbor within 20 km, so buffers overlap and the same acreage can count toward two or more plants. The national roll-up totals above are therefore an **upper bound**, not a strictly additive potential — de-duplicating shared land would lower them.

## Validation notes (Spec section 11)

- **Order-of-magnitude match, forest toggle is the key lever.** Across the 5 paper states the forest-included screen (24 GW) aligns with paper Fig. 4 (61 GW) better than the forest-excluded default (14 GW). Excluding all forest is the aggressive end of the toggle (Spec §12).
- **Fig. 4 is not the same quantity as qualifying gas nameplate.** Paper Fig. 4 gives IL = 16 GW, which *exceeds* IL's entire operating gas fleet here (13.7 GW). So Fig. 4 measures a solar/load-potential, not qualifying nameplate; our lower, same-order-of-magnitude totals are the expected outcome, not a bug.
- **Residual gap (PA, IL) is plant size + terrain.** PA/IL fleets are dominated by large CCGTs whose flat 24/7 load needs more solar than fits within 10 km; single-axis tracking or a larger buffer would expand the set.
- Capacity factor here is 0.11–0.22 (mean 0.17), the PVWatts capacity_factor the spec uses in R directly (Spec §3 anchor ~0.16); NOT multiplied by the inverter ratio. For the national run it is snapped to a 0.25° grid (per-plant error ≲0.01). On small urban sites the 150-acre DC parcel can bind the verdict (usable = land − parcel).
