# PJM Gas-Plant / Solar / Data-Center Land Screen — Summary

Fleet: **199 operating PJM gas plants**, **94.4 GW** total nameplate.

Parameters: overbuild=1.3, power density default 35.3 MW/km² (7 ac/MW), DC parcel 150 acres, NSRDB TMY CF (PVWatts, AC).

## Qualifying plants & hostable data-center load (GW) — forest EXCLUDED (conservative default)

| Buffer | Gas cap | Plants qualifying | Hostable load (GW) |
|---|---|---|---|
| 10 km | 5% | 90 | 17.5 |
| 10 km | 10% | 91 | 17.8 |
| 10 km | 20% | 93 | 18.8 |
| 5 km | 5% | 40 | 1.5 |
| 5 km | 10% | 41 | 1.5 |
| 5 km | 20% | 45 | 2.1 |

## Qualifying plants & hostable data-center load (GW) — forest INCLUDED (less aggressive)

| Buffer | Gas cap | Plants qualifying | Hostable load (GW) |
|---|---|---|---|
| 10 km | 5% | 130 | 32.4 |
| 10 km | 10% | 131 | 33.4 |
| 10 km | 20% | 135 | 37.9 |
| 5 km | 5% | 55 | 2.3 |
| 5 km | 10% | 55 | 2.3 |
| 5 km | 20% | 59 | 3.1 |

## Power-density sensitivity (10 km, 10% gas cap, forest excluded)

| acres/MW | MW/km² | Plants qualifying | Hostable load (GW) |
|---|---|---|---|
| 5 | 49.4 | 101 | 23.0 |
| 7 | 35.3 | 91 | 17.8 |
| 8 | 30.9 | 84 | 14.7 |

## Hostable load — whole-plant vs including partial data centers (10 km, forest excl.)

A plant that can't host a *full-nameplate* data center can usually still host a *smaller* one matched to its available solar land. Hostable load = min(nameplate, headroom × nameplate).

| Gas cap | Whole-plant qualifiers (GW) | Including partial DCs (GW) |
|---|---|---|
| 5% | 17.5 | 42.8 |
| 10% | 17.8 | 44.2 |
| 20% | 18.8 | 47.5 |

## Qualifying nameplate by state (10 km, 10% gas cap, 7 ac/MW) — vs paper Fig. 4

| State | Forest excl. GW | Forest incl. GW | Paper Fig. 4 (GW) |
|---|---|---|---|
| VA | 1.9 | 8.0 | 10 |
| OH | 5.1 | 7.3 | 12 |
| IL | 5.2 | 6.2 | 16 |
| PA | 2.4 | 4.1 | 17 |
| MD | 0.4 | 3.9 | — |
| NJ | 0.4 | 1.5 | 6 |
| IN | 1.0 | 1.0 | — |
| DE | 0.8 | 0.8 | — |
| KY | 0.6 | 0.6 | — |
| DC | 0.0 | 0.0 | — |
| **Total (5 paper states)** | **15.0** | **27.0** | **61** |

## Validation notes (Spec section 11)

- **Order-of-magnitude match, forest toggle is the key lever.** The forest-included screen (27 GW across the 5 paper states) aligns with paper Fig. 4 far better than the conservative forest-excluded default (15 GW); VA (8.0 vs 10) and OH (7.3 vs 12) land close. Excluding all forest is the aggressive end of the toggle (Spec §12).
- **Fig. 4 is not the same quantity as qualifying gas nameplate.** Paper Fig. 4 gives IL = 16 GW, which *exceeds* IL's entire operating gas fleet here (13.7 GW). So Fig. 4 measures a solar/load-potential, not qualifying nameplate; our lower, same-order-of-magnitude totals are the expected outcome, not a bug.
- **Residual gap (PA, IL) is plant size + terrain.** PA/IL fleets are dominated by large CCGTs whose flat 24/7 load needs more solar than fits within 10 km; single-axis tracking or a larger buffer would expand the set.
- CF here (~0.19 AC, 1.3 ILR) is mildly optimistic vs the spec's 0.16 anchor; a lower CF raises R and shrinks the qualifying set. Solar land dwarfs the 150-acre DC parcel, so the area test binds on solar.
