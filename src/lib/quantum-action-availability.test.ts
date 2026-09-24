import { describe, expect, test } from "bun:test";

import { quantumActionAvailability } from "./quantum-action-availability";

describe("quantum search action availability", () => {
  test("Estimate stays available before inputs and resources are known", () => {
    expect(
      quantumActionAvailability({
        busy: false,
        hardwareBusy: false,
        estimate: null,
      }),
    ).toEqual({
      canEstimate: true,
      canRunSearch: false,
      canRequestHardware: true,
    });
  });

  test("a successful resource estimate enables simulator execution", () => {
    expect(
      quantumActionAvailability({
        busy: false,
        hardwareBusy: false,
        estimate: { exceedsSimulatorLimits: false },
      }).canRunSearch,
    ).toBe(true);
  });

  test("an oversized resource estimate keeps simulator execution disabled", () => {
    const availability = quantumActionAvailability({
      busy: false,
      hardwareBusy: false,
      estimate: { exceedsSimulatorLimits: true },
    });

    expect(availability.canEstimate).toBe(true);
    expect(availability.canRunSearch).toBe(false);
    expect(availability.canRequestHardware).toBe(true);
  });

  test("active work temporarily disables all actions", () => {
    expect(
      quantumActionAvailability({
        busy: true,
        hardwareBusy: false,
        estimate: { exceedsSimulatorLimits: false },
      }),
    ).toEqual({
      canEstimate: false,
      canRunSearch: false,
      canRequestHardware: false,
    });
  });
});
