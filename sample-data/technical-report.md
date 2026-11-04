# ADR-1 Technical Report — Communication Module & Integration

**Document ID:** ADR-TR-014
**Author:** Elena Rodriguez
**Date:** 28 September 2026
**Classification:** Internal

## 1. Scope

This report covers the state of the communication module and the integration
test programme for the ADR-1 delivery robot as of 28 September 2026.

## 2. Communication module

The communication module provides two links:

- **LoRa telemetry** (915 MHz) — periodic position, battery and fault telemetry
  to the dispatch server. Frame rate 1 Hz.
- **Cellular fallback** — dispatch commands and remote-stop when LoRa is
  unavailable.

The module runs vendor firmware **v2.2** on the v1 prototype. The vendor has
announced firmware **v2.3**, which fixes a known keep-alive defect, but it is
not yet released.

### 2.1 Known issue: communication timeout (ADR-142)

Intermittent timeouts occur on the LoRa link when the robot passes through the
industrial zone near the depot. Observed in 6 of 40 route runs. The team applied
a workaround on 20 September: the retry window was raised from 1 second to
3 seconds, which has stopped the timeouts in lab re-runs. The root cause is
suspected to be RF interference from the depot's industrial equipment, but this
has not been confirmed. A spectrum survey is planned but not yet scheduled.

## 3. Integration test programme

The integration test programme comprises 14 test cases covering perception,
navigation, motor control, communication and power management interactions.

**Status as of this report: integration testing is pending.** Test cases 1–9
have been executed and passed. Test cases 10–14 (power management under load,
remote-stop over cellular, and the two failover cases) have not yet been
executed because the load bank required for them is on loan from the lab and
will not be available until early October.

## 4. Thermal findings

The 29 September thermal run (full load, 30 minutes, ambient 31 degrees
Celsius) recorded a maximum pack temperature of 58 degrees Celsius at the rear
cell. This exceeds the 55 degree limit in the requirements document. The front
cell peaked at 49 degrees Celsius. The motor controller (Controller A) reached
61 degrees Celsius on its heat sink, within its 85 degree specification.

A passive cooling plate for the rear of the battery compartment is being
evaluated. Results with the plate fitted are expected before 31 October 2026.

## 5. Architecture note

This report confirms the move to the distributed architecture adopted in
August 2026. Motor control now runs on the dedicated motor controller rather
than the central compute unit. The central compute unit retains perception and
navigation. This change was made because the centralised design could not meet
the 50 ms motor control loop latency under full perception load.

## 6. Open items

- Confirm root cause of the ADR-142 communication timeouts (spectrum survey).
- Execute integration test cases 10–14 once the load bank is available.
- Validate battery temperature with the cooling plate fitted.
- Obtain vendor firmware v2.3 and assess the keep-alive fix.
- The latest architecture document (ADR-ARCH-007) has not been marked final;
  the version in the shared drive is still labelled "draft".