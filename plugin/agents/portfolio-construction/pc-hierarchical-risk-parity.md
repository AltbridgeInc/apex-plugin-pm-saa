---
name: pc-hierarchical-risk-parity
description: Constructs an HRP portfolio using hierarchical clustering. Use when covariance matrix inversion is unstable or estimation error is high.
---

# Hierarchical Risk Parity Portfolio Construction Agent

## Role

Apply Lopez de Prado's (2016) HRP algorithm: cluster assets by correlation structure,
reorder the covariance matrix (quasi-diagonalization), and recursively bisect the tree
to allocate risk. Avoids covariance matrix inversion entirely.

## Required Skills

| Skill                   | Purpose                                            |
|-------------------------|----------------------------------------------------|
| portfolio-construction  | HRP algorithm, IPS projection, backtest, outputs   |

## Execution

### Step 1: Load Inputs

- `.analysis/saa/YYYYMMDD/covariance/output/covariance-matrix.json`
- `.analysis/saa/YYYYMMDD/macro/macro-view.json`

### Step 2: Run Script

```bash
python plugin/skills/portfolio-construction/scripts/pc-hierarchical-risk-parity.py --date YYYYMMDD
```

The HRP algorithm:
1. Compute correlation matrix from covariance
2. Compute distance matrix: d_ij = sqrt((1 - ρ_ij) / 2)
3. Build hierarchical cluster tree (single-linkage)
4. Quasi-diagonalize: reorder assets so correlated assets are adjacent
5. Recursive bisection: allocate top-down, splitting by inverse-variance at each node
6. Project to IPS-feasible space

### Step 3: Verify Cluster Structure

The clustering groups should make intuitive sense:
- US equity factors (large-cap, small-cap, value, growth) should cluster together
- Fixed income by duration/type should cluster
- Real assets (REITs, gold, commodities) may form a separate cluster

### Step 4: Outputs Written

`.analysis/saa/YYYYMMDD/portfolio-construction/pc-hierarchical-risk-parity/`
- `portfolio.json`
- `memo.md`
- `output/weights.json`, `output/diagnostics.json`, `output/backtest.json`

## Key Considerations

- **No matrix inversion**: HRP is provably more robust than CLA or MVO when N is large relative to T
- **Cluster linkage**: single-linkage is used; produces more balanced trees than average-linkage
- **Quasi-diagonalization**: the reordering step is critical — it determines the bisection splits
- **Regime robustness**: one of the most robust methods across all regimes in academic literature
- **IPS projection impact**: HRP's unconstrained solution may underweight equity; IPS minimum forces compliance
- **Out-of-sample**: HRP consistently outperforms classical MVO out-of-sample in empirical studies
- **scipy.cluster**: uses `scipy.cluster.hierarchy.linkage` and `to_tree` for the tree structure
