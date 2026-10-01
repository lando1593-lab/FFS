# Open Domain Questions (answer or defer; each one changes code)

These are the questions where my software judgment is not a substitute for yours. Numbered so
answers can be referenced in commits. The ones marked **M1** block Milestone 1 design decisions.

## Takeoff conventions (M1)
1. **M1** Column length: do you take columns floor-to-floor, top-of-slab to underside-of-deck, or
   to the actual splice elevation? Does the answer differ for estimating vs. shop drawings?
2. **M1** Beam length: centerline grid-to-grid, or face-to-face of supporting members? For a
   W18x35 framing into a W24 girder, do you deduct half the girder flange width?
3. **M1** Do you count the portion of a beam inside a column cap/plate connection, or stop short?
4. **M1** Existing steel: on renovation sets, do you want (E) members in the database as excluded,
   or only new/altered members? (Excluded-but-present supports revision comparison later.)
5. **M1** Joists (K/LH/DLH) and joist girders: take off by LF, by each, or by weight? Do you
   fireproof joists at all in your market, or is that a membrane-ceiling conversation?
6. **M1** Metal deck: do you want deck areas captured in M1 so the member database already knows
   which beams carry fluted deck (affects design selection and flute-fill later)?
7. How do you name levels when the structural set says "LEVEL 2 FRAMING PLAN" but the
   architectural set says "SECOND FLOOR"? Structural wins, or do you want a mapping table?
8. Do you take off miscellaneous steel (lintels, kickers, bracing, stair stringers) in the same
   pass or as a separate category with its own rules?

## Conditions and spray charts
9. Would your field superintendent rather have thickness by **member size** (W8x10 = X") or by
   **condition color** (RED = FP-01, see chart)? Or both on the same sheet?
10. How do you represent a condition today in The EDGE: by rating + member type + product, or
    finer (e.g. separate conditions for restrained vs unrestrained, or for beams under fluted
    deck vs flat)?
11. When one beam carries two ratings (e.g. supports a 2-hr floor on one side and a roof on the
    other), what do you do today?

## Design assignment
12. Would you normally treat a composite floor beam assembly as **restrained** for design
    selection, or do you default to unrestrained unless the engineer states otherwise?
13. Column protection: do you typically carry the column design full height including above the
    ceiling, and how do you treat the column within a rated wall?
14. For members whose W/D falls below the smallest listed in a design, what is your practice:
    upsize thickness to the minimum listed member, pick a different design, or flag to the
    engineer?

## Exposure
15. Would exposed lobby/atrium framing normally go intumescent in your market, or do you see
    exposed SFRM accepted? What signals on architectural drawings tell you "this is exposed"?
16. Exterior exposed steel (canopies, exposed columns): is that usually excluded from your scope
    or priced as an intumescent alternate?

## Materials
17. What waste/application factor do you use today for low-density SFRM, medium-density, and
    intumescent, and does it vary by member size or by building type?
18. Packaging: do your suppliers quote bags, pallets, or truckloads, and should releases round
    up to pallets?

## Shop drawings and submittals
19. Which historical shop-drawing style on the LaCie do you consider the best model, and why?
    (I will use it to define our standard, not copy it.)
20. Does your typical spec require shop drawings for SFRM at all, or mostly product data +
    UL designs? How often are spray charts requested by the engineer vs. internal-only?
21. Sheet numbering preference: FP1.01 style (as in your brief) or matching the structural set
    numbering (FP-201 for S-201)?

## Workflow
22. What single thing in The EDGE takes you five clicks that should take one?
23. What does an estimator at your company do between "takeoff done" and "bid submitted" that
    the software should know about (e.g., alternates, scope letters, exclusions)?

## Added after the first design validation (2026-10-01)
24. **M3** For HSS and pipe columns, do you compute A/P with the nominal wall thickness or AISC's
    design wall thickness (0.93 × nominal)? On X790 the two give 9/16 in. and 5/8 in. for an
    HSS5X5X3/8 at 1 hour. Your sample bid matches the nominal-wall result. Is that The EDGE's
    default, and does Isolatek's technical staff agree with it?
25. **M3** X790 allows a tested table (ST 5x5x3/8 → 7/16 in. at 1 hr on Isolatek's chart) and an
    alternate equation (→ 9/16 in.). Your bid used 9/16. Is that a deliberate conservative
    choice, an EDGE default, or a mistake you would want flagged? Which route should the
    software present first?
26. **M3** For angles under a roof or floor beam design (3-sided), do you use the
    miscellaneous-shapes chart (4-sided contour W/D) or a beam-substitution calculation? Your bid
    is 1/16 in. thinner than the chart on both angles.
