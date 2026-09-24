# Cached demo results

This folder stores user-supplied, previously completed quantum hardware
results for reproducible demonstrations.

## Layout

```text
cacheResults/
  index.json
  hybrid/
    ibm_marrakesh-d9lhj7bjf64c739ji30g.json
  frqi/
  grover/
```

Each result file contains:

- provenance and a stable cache key;
- algorithm, provider, device, and remote job details;
- bounded query and representative hardware window;
- logical and ISA circuit metrics;
- raw measurement counts;
- the scientific limitations displayed with the result.

## Adding another result

Create a JSON file inside the matching algorithm folder and add a catalog
entry to `index.json`. Preserve the values returned by the hardware page.
Never include provider credentials.

Cached results must be visibly identified as cached if they are later exposed
through the portal. They must not be presented as a newly submitted hardware
job.
