# EFE Node 1 N1-1A ECM footprint audit contract v01

## Question

当前 ECM 横向边界与细胞 `x-z` 投影完全齐平。N1-1A 检查峰值响应是否
受到这一人工侧边界的控制，并选择进入 N1-2 的生产候选足迹。

## Frozen comparison

| Case | Footprint scale | ECM span `(x,y,z)` | Divisions `(nx,ny,nz)` | Role |
|---|---:|---:|---:|---|
| `F100` | `1.0` | `(1.00,0.30,0.56)` | `(5,4,4)` | narrow-domain control |
| `F150` | `1.5` | `(1.50,0.30,0.84)` | `(8,4,6)` | production candidate |
| `F200` | `2.0` | `(2.00,0.30,1.12)` | `(10,4,8)` | far-boundary check |

The footprint is enlarged about the original `x-z` centre. Myocardial and
endocardial DCM geometry, both material-point registries, jelly thickness,
material parameters, support law and active command remain unchanged. Extra
ECM area is not tethered to a nonexistent cell.

## Evidence path

1. reference-state geometry and zero-force audit for all three cases;
2. active-only continuation to the registered development peak `a=0.20`;
3. compare axial shortening, maximum discrete interface traction, ECM energy,
   minimum `J`, minimum gap, surface quality and normalized KKT;
4. compare the full ECM displacement field in the common physical overlap and
   the response changes `F100→F150` and `F150→F200`.

## Gates

- normalized KKT `<=1e-5`;
- exact-volume residual `<=1e-8`;
- minimum ECM `J>0`;
- minimum interface gap `>=-1e-12`;
- minimum DCM face-area ratio `>0.2`;
- M3 pair force/moment residuals `<=1e-10`;
- no raw optimizer success flag may replace the contractual gates.

The production footprint may be selected as `1.5×` only if `F150→F200` changes
global peak metrics by `<=2%` and interface-traction metrics by `<=10%`.
Otherwise `2.0×` remains the production candidate or a larger far-boundary
check must be proposed. These are development boundary gates, not formal
D1/E1 spatial-convergence claims.

## Stop condition

After the comparison figure and evidence package are generated, stop at the
human figure gate. N1-2 remains unauthorized.

