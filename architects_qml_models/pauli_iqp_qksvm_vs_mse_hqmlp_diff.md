# Pauli QKSVM, IQP QKSVM, and MSE HQMLP: what is different?

## First, a terminology correction

There is no **MSE QKSVM** in this portal. The three models being compared are:

1. **Pauli QKSVM** — a quantum-kernel support vector machine.
2. **IQP QKSVM** — another quantum-kernel support vector machine with a different data-encoding circuit.
3. **MSE HQMLP** — a trainable hybrid quantum/classical neural model optimized with mean-squared error.

MSE is a training loss, not a type of quantum kernel. The MSE model is therefore not a QKSVM.

## Common experiment setup

The comparison was designed so the architecture—not the input data—was the main difference.

- Dataset: audited Framingham teaching cohort for a 10-year coronary-heart-disease research label.
- Input to each quantum model: four values produced by PCA from the prepared health variables.
- Qubits: 4.
- Training rows per seed: 256.
- Held-out test rows per seed: 597, including 57 positive outcomes.
- Seeds: 11, 42, and 73.
- Calibration and the final threshold were fitted without using the test outcomes.
- Execution: exact local simulator; no QPU result and no demonstrated quantum speedup.

## Difference in one view

| Question | Pauli QKSVM | IQP QKSVM | MSE HQMLP |
| --- | --- | --- | --- |
| Model family | Quantum kernel + classical SVM | Quantum kernel + classical SVM | Hybrid quantum/classical neural model |
| Main job of circuit | Create a Pauli Z/ZZ similarity space | Create an IQP phase-interaction similarity space | Produce trainable measurements for a direct score |
| Quantum weights learned | None | None | 12 |
| Quantum training epochs | None | None | Up to 12 |
| What is learned | Classical SVM boundary | Classical SVM boundary | Classical projection, quantum rotations, and output layer |
| Total learned values | SVM support-vector coefficients and bias | SVM support-vector coefficients and bias | 37 model values |
| Main tuned setting | SVM `C`: 0.1, 1.0, or 10.0 | SVM `C`: 0.1, 1.0, or 10.0 | Adam learning with MSE, learning rate 0.01, weight decay 0.0001 |
| Output idea | Similarity to important training records | Similarity to important training records | Direct score from one record |

## Pauli QKSVM

```mermaid
flowchart LR
    A["4 PCA values"] --> B["Hadamard + RZ gates"]
    B --> C["Neighboring Z/ZZ links"]
    C --> D["Repeat twice"]
    D --> E["Compare state overlap"]
    E --> F["Classical SVM"]
    F --> G["Calibrated research score"]
```

The Pauli feature map writes each input into a phase and then connects neighboring qubits: `q0-q1`, `q1-q2`, and `q2-q3`. Each connection uses a CNOT–RZ–CNOT block. Repeating this twice creates a structured representation containing individual values and selected local relationships.

For two records `x` and `z`, the quantum part returns a similarity:

```text
K(x, z) = |<phi(z) | phi(x)>|^2
```

The classical SVM uses these similarities to learn the decision boundary. The quantum circuit itself is fixed.

### Practical scope

Pauli kernels are useful for research into whether a deliberately structured feature map exposes relationships that an ordinary linear boundary misses. This version is especially suited to testing local or neighboring interactions between four compressed inputs. It is not automatically better because the chosen circuit may create an unhelpful similarity space.

## IQP QKSVM

```mermaid
flowchart LR
    A["4 PCA values"] --> B["Hadamard gates"]
    B --> C["Individual phase gates"]
    C --> D["Pairwise IQP phase interactions"]
    D --> E["Compare state overlap"]
    E --> F["Classical SVM"]
    F --> G["Calibrated research score"]
```

IQP means **Instantaneous Quantum Polynomial-time**. Here it names the style of feature map; it does not mean the complete prediction runs instantly.

The IQP circuit places the qubits in superposition, adds phases from individual inputs, and adds phase interactions between input pairs. It therefore creates a different geometry from the Pauli map before the same state-overlap calculation and classical SVM are used.

### Practical scope

IQP kernels are used to study rich nonlinear similarity functions that may be difficult to describe with a simple classical formula. Their realistic near-term use is controlled kernel research on small datasets. The kernel matrix grows with the number of record pairs, and real hardware would introduce shot noise, queue time, and circuit errors.

## Why Pauli and IQP were both run

Both models keep the downstream SVM nearly the same while changing the quantum feature map. This makes the experiment a useful architecture comparison:

- **Pauli QKSVM** asks whether a repeated, locally connected Z/ZZ map is useful.
- **IQP QKSVM** asks whether a broader phase-interaction map produces better similarities.
- Running both shows whether results depend on the choice of quantum encoding rather than simply using the word “quantum.”

In this benchmark, IQP produced the stronger quantum-kernel result. That does not prove IQP is universally better; it only shows that its similarity geometry matched this small prepared dataset better than the tested Pauli map.

## MSE HQMLP

```mermaid
flowchart LR
    A["4 PCA values"] --> B["Learned classical 4-to-4 layer"]
    B --> C["RY data encoding"]
    C --> D["12 learned quantum rotations"]
    D --> E["Linear CNOT chain"]
    E --> F["4 Pauli-Z measurements"]
    F --> G["Learned classical output"]
    G --> H["MSE-trained score"]
```

Unlike the QKSVMs, this model does not compare a new record with every training state. It processes one record directly through:

- a learned classical projection: 20 values;
- a four-qubit trainable circuit: 12 values;
- a learned output layer: 5 values.

The total is **37 trainable values**. Training minimizes:

```text
MSE = average((predicted score - known label)^2)
```

### Practical scope

The MSE HQMLP tests whether a small trainable quantum layer can participate inside a neural model. It can adapt its circuit to the data, unlike a fixed kernel map. The tradeoff is more optimization work, more circuit evaluations, sensitivity to initialization, and no guarantee that MSE is the best loss for an imbalanced binary outcome.

## Why the MSE architecture was run

It was an ablation: a controlled alternative to the preferred BCE-trained hybrid model. The purpose was to test how much the circuit style and training loss change the outcome—not to claim that MSE is clinically preferred.

Together, the three architectures answer two different research questions:

1. Can a fixed quantum representation provide a useful similarity function for an SVM?
2. Can a trainable quantum layer learn a useful direct scoring function?

## Recorded result in this repository

Mean held-out metrics across seeds 11, 42, and 73:

| Model | AUROC | AUPRC | Balanced accuracy | Interpretation |
| --- | ---: | ---: | ---: | --- |
| Pauli QKSVM | 0.506 | 0.100 | 0.509 | Close to chance-level separation in this run |
| IQP QKSVM | 0.616 | 0.139 | 0.572 | Best discrimination of the two tested QKSVM maps |
| MSE HQMLP | 0.583 | 0.149 | 0.543 | Slightly higher mean AUPRC, but unstable across seeds |

The positive prevalence in the held-out set was about **9.5%**, so AUPRC should be interpreted against that low baseline. These numbers are small-sample research evidence, not clinical performance claims. They do not establish quantum advantage, and stronger classical controls remain necessary.

## Real use today

The defensible present use of these models is:

- teaching how quantum kernels and trainable quantum layers differ;
- comparing quantum feature maps under the same data split;
- measuring resource cost, stability, and sensitivity to architecture choices;
- building reproducible research baselines for later simulator or hardware experiments.

They should not currently be used to diagnose coronary heart disease, determine treatment, or screen real patients. Before any clinical use, the complete pipeline would need substantially larger representative data, external validation, subgroup analysis, prospective evaluation, calibration monitoring, clinical governance, and comparison with accepted clinical tools.

## Short conclusion

Pauli and IQP QKSVMs are **fixed quantum similarity engines followed by a classical SVM**. Their difference is the circuit used to define similarity. The MSE HQMLP is a **trainable hybrid scoring model**, not a QKSVM. These architectures were run to compare fixed-kernel and trainable-quantum approaches under the same controlled Framingham experiment; their current value is research and education, not clinical deployment.

