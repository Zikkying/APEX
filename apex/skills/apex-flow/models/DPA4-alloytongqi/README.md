# DPA4 alloytongqi

- File: `model.pt`
- Model type: DPA4 (`dpa4_ener` fitting)
- Task form: single/default task (`model_branch_alias=[]`)
- Branch provenance: `alloytongqi`, supplied by the user; not embedded in the checkpoint
- Size: 30,403,297 bytes
- SHA-256: `c84b268cc6191afc72bd2d5c001cbe526a0d2e04ebf6dbd7df021306e9abe9ad`
- Current dedicated runtime: `registry.dp.tech/dptech/dp/native/prod-397953/397637/dpa4-alloytongqi-l20:20261015-slim02`
- Image selection: [runtime-images.md](../../reference/runtime-images.md)

Generate with `--runtime-profile dpa4-alloytongqi-l20` and use its image-resident
`.pt2` contract. [Debug](../../reference/debug.md) covers runtime diagnostics
and environment troubleshooting.

## Elements

The checkpoint type map accepts these 118 elements:

```text
H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar
K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr
Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe
Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf
Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th
Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs
Mt Ds Rg Cn Nh Fl Mc Lv Ts Og
```

Fe, Mo and Ni are included. This list describes accepted atom types; choose
the model for the requested material and property.
