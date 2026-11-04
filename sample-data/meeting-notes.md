# ADR-1 Design Meeting Notes — October 2026

## Meeting 1 — 12 September 2026 (Motor controller selection)

**Present:** Priya Nair, Marcus Chen, David Okafor
**Absent:** Elena Rodriguez

The team compared three motor controllers for the drive system:

- **Controller A** (vendor: VoltDrive, model VD-480)
- **Controller B** (vendor: VoltDrive, model VD-360)
- **Controller C** (vendor: ApexMotors, model AM-500)

Controller B was cheaper by about $90 per unit, but in the back-to-back thermal
bench test it ran 11 degrees Celsius hotter than Controller A at the 48 V full
load point. Controller C passed the thermal test but its firmware API did not
expose the current-limit settings the safety team requires.

**Decision:** the team selected **Controller A** after testing all three
alternatives. Thermal performance was the key consideration, and the $90
premium per unit is within the budget ceiling.

Action items from this meeting:
- Marcus Chen to complete motor testing on the v1 prototype. (Status: in progress.)
- Priya Nair to write up the controller selection rationale for the handover.
- David Okafor to confirm the vendor lead time for Controller A stock.

## Meeting 2 — 26 September 2026 (Integration status)

**Present:** Priya Nair, Marcus Chen, Elena Rodriguez, David Okafor

Elena reported that integration testing of the communication module is complete:
all 14 test cases passed on the v1 prototype, and the LoRa telemetry link held
through the full 8 km route. The cellular fallback link was exercised in the lab
only.

**Decision:** integration testing is closed out and the team moves to thermal
validation (milestone M4) as the next gate.

Open items:
- The communication timeout issue (see GitHub issue ADR-142) was worked around
  by raising the retry window to 3 seconds. The root cause is not yet known.
- Elena is on leave from 8 October to 20 October.

## Meeting 3 — 10 October 2026 (Thermal review)

**Present:** Marcus Chen, David Okafor

Battery thermal test results from the 29 September run were reviewed. The pack
reached 58 degrees Celsius at the rear cell under sustained full load, which is
above the 55 degree limit set in the requirements. Marcus attributed this to the
rear cells being closer to the motor controller heat.

**Decision:** a passive cooling plate was approved for the rear of the battery
compartment. No redesign of the pack itself is planned.

Action items:
- Marcus Chen to validate battery temperature with the cooling plate fitted.
  (Status: in progress — results expected before 31 October.)
- David Okafor to raise the overheating issue with the vendor and ask for their
  assessment.

Unresolved question raised in this meeting: **who is responsible for the final
sign-off on motor testing?** Priya was going to do it, but with her departure on
15 November the owner is not yet assigned.