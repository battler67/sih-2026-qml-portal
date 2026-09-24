export type ResourceEstimateAvailability = {
  exceedsSimulatorLimits: boolean;
};

export function quantumActionAvailability({
  busy,
  hardwareBusy,
  estimate,
}: {
  busy: boolean;
  hardwareBusy: boolean;
  estimate: ResourceEstimateAvailability | null;
}) {
  return {
    canEstimate: !busy,
    canRunSearch: !busy && !hardwareBusy && estimate !== null && !estimate.exceedsSimulatorLimits,
    canRequestHardware: !busy && !hardwareBusy,
  };
}
