# Acquisition data

**This directory is empty of data because the experiment has not been run.**

Acquisition files go here, as pairs:

```
<run_id>.csv          the samples
<run_id>.meta.yaml    the metadata sidecar, without which the CSV cannot be loaded
```

Start from `../acquisition_template.csv` and `../metadata_template.meta.yaml`. The
format, the units and the reason for each required field are in `../data_schema.md`.

## Do not put synthetic data here

`../analysis/synthetic.py` writes into whatever `--out` directory you give it. Give it a
scratch directory (`/tmp/m8_synthetic`), not this one. Synthetic files are already
labelled three ways — `synthetic` in the filename, a `# SYNTHETIC DATA … NOT A
MEASUREMENT` header line, and `synthetic: true` in the sidecar — but the strongest
labelling available is for the directory that holds real measurements to hold nothing
else.

`tests/test_thermal_coupon.py` generates its synthetic files into a pytest temporary
directory for exactly this reason.

## Aborted runs stay

A run stopped by a hard-stop condition (`../protocol.md` §2) is kept, with
`run_type: aborted` and the reason in `notes`. Spec §31: failures are recorded, not
deleted.
