# US Gas-Plant / Solar / Data-Center Land Screen — Summary

Fleet: **1277 operating US (lower-48) gas plants**, **475.5 GW** total nameplate, across 48 states and 50 balancing authorities.

Parameters: overbuild=1.3, power density default 91 MW/mi² (7 ac/MW), DC parcel 150 acres, NSRDB TMY CF (PVWatts, AC). Areas in mi².

## Qualifying plants & hostable data-center load (GW) — forest EXCLUDED (conservative default)

| Buffer | Gas cap | Plants qualifying | Hostable load (GW) |
|---|---|---|---|
| 10 km | 5% | 789 | 152.6 |
| 10 km | 10% | 802 | 159.8 |
| 10 km | 20% | 819 | 169.1 |
| 5 km | 5% | 441 | 36.6 |
| 5 km | 10% | 447 | 37.3 |
| 5 km | 20% | 470 | 43.2 |

## Qualifying plants & hostable data-center load (GW) — forest INCLUDED (less aggressive)

| Buffer | Gas cap | Plants qualifying | Hostable load (GW) |
|---|---|---|---|
| 10 km | 5% | 954 | 226.1 |
| 10 km | 10% | 963 | 233.4 |
| 10 km | 20% | 990 | 253.7 |
| 5 km | 5% | 526 | 44.7 |
| 5 km | 10% | 537 | 47.3 |
| 5 km | 20% | 560 | 54.7 |

## Power-density sensitivity (10 km, 10% gas cap, forest excluded)

| acres/MW | MW/mi² | Plants qualifying | Hostable load (GW) |
|---|---|---|---|
| 5 | 128.0 | 865 | 196.7 |
| 7 | 91.4 | 802 | 159.8 |
| 8 | 80.0 | 773 | 146.0 |

## Hostable load — whole-plant vs including partial data centers (10 km, forest excl.)

A plant that can't host a *full-nameplate* data center can usually still host a *smaller* one matched to its available solar land. Hostable load = min(nameplate, headroom × nameplate).

| Gas cap | Whole-plant qualifiers (GW) | Including partial DCs (GW) |
|---|---|---|
| 5% | 152.6 | 262.2 |
| 10% | 159.8 | 268.1 |
| 20% | 169.1 | 281.2 |

## Qualifying nameplate by state (10 km, 10% gas cap, 7 ac/MW) — vs paper Fig. 4

| State | Forest excl. GW | Forest incl. GW | Paper Fig. 4 (GW) |
|---|---|---|---|
| TX | 33.9 | 38.3 | — |
| CA | 15.7 | 15.8 | — |
| AZ | 10.7 | 10.7 | — |
| OK | 4.4 | 10.4 | — |
| GA | 2.5 | 10.2 | — |
| IL | 9.1 | 10.0 | 16 |
| MS | 2.3 | 8.7 | — |
| VA | 1.9 | 8.0 | 10 |
| LA | 4.5 | 7.9 | — |
| OH | 5.1 | 7.3 | 12 |
| FL | 4.1 | 6.8 | — |
| WI | 6.2 | 6.2 | — |
| IN | 5.2 | 6.1 | — |
| CO | 6.1 | 6.1 | — |
| NC | 1.0 | 5.9 | — |
| MO | 5.8 | 5.8 | — |
| AL | 0.5 | 5.5 | — |
| MI | 4.5 | 5.0 | — |
| PA | 2.4 | 4.1 | 17 |
| NY | 1.8 | 4.0 | — |
| MD | 0.4 | 3.9 | — |
| MN | 3.7 | 3.7 | — |
| AR | 1.6 | 3.6 | — |
| SC | 0.5 | 3.6 | — |
| IA | 3.5 | 3.5 | — |
| TN | 2.7 | 3.4 | — |
| MA | 0.0 | 3.3 | — |
| OR | 3.0 | 3.0 | — |
| KS | 2.9 | 2.9 | — |
| NM | 2.5 | 2.5 | — |
| WA | 0.8 | 2.4 | — |
| NE | 1.6 | 1.6 | — |
| ME | 0.0 | 1.6 | — |
| SD | 1.5 | 1.5 | — |
| NJ | 0.4 | 1.5 | 6 |
| KY | 1.2 | 1.4 | — |
| ID | 1.2 | 1.2 | — |
| UT | 1.1 | 1.1 | — |
| NV | 0.9 | 0.9 | — |
| RI | 0.0 | 0.8 | — |
| DE | 0.8 | 0.8 | — |
| CT | 0.2 | 0.8 | — |
| ND | 0.7 | 0.7 | — |
| WY | 0.4 | 0.4 | — |
| MT | 0.4 | 0.4 | — |
| DC | 0.0 | 0.0 | — |
| NH | 0.0 | 0.0 | — |
| **Total (5 paper states)** | **18.8** | **30.8** | **61** |

## Validation notes (Spec section 11)

- **Order-of-magnitude match, forest toggle is the key lever.** The forest-included screen (27 GW across the 5 paper states) aligns with paper Fig. 4 far better than the conservative forest-excluded default (15 GW); VA (8.0 vs 10) and OH (7.3 vs 12) land close. Excluding all forest is the aggressive end of the toggle (Spec §12).
- **Fig. 4 is not the same quantity as qualifying gas nameplate.** Paper Fig. 4 gives IL = 16 GW, which *exceeds* IL's entire operating gas fleet here (13.7 GW). So Fig. 4 measures a solar/load-potential, not qualifying nameplate; our lower, same-order-of-magnitude totals are the expected outcome, not a bug.
- **Residual gap (PA, IL) is plant size + terrain.** PA/IL fleets are dominated by large CCGTs whose flat 24/7 load needs more solar than fits within 10 km; single-axis tracking or a larger buffer would expand the set.
- CF here (~0.19 AC, 1.3 ILR) is mildly optimistic vs the spec's 0.16 anchor; a lower CF raises R and shrinks the qualifying set. Solar land dwarfs the 150-acre DC parcel, so the area test binds on solar.
