# SimuCell3D: three-dimensional simulation of tissue mechanics with cell polarization

Received: 4 April 2023

Accepted: 8 March 2024

Published online: 9 April 2024

![](Jk2Mb6Ry4S_SimuCell3D组织力学_assets/images/eb564a74ca2ea9836d8657ac90655bbf3763b6a2c1856b1273ad52fa9bc63035.jpg)

Check for updates

Steve Runser  1,2, Roman Vetter1,2 & Dagmar Iber  1,2

The three-dimensional (3D) organization of cells determines tissue function and integrity, and changes markedly in development and disease. Cell-based simulations have long been used to defne the underlying mechanical principles. However, high computational costs have so far limited simulations to either simplifed cell geometries or small tissue patches. Here, we present SimuCell3D, an efcient open-source program to simulate large tissues in three dimensions with subcellular resolution, growth, proliferation, extracellular matrix, fuid cavities, nuclei and non-uniform mechanical properties, as found in polarized epithelia. Spheroids, vesicles, sheets, tubes and other tissue geometries can readily be imported from microscopy images and simulated to infer biomechanical parameters. Doing so, we show that 3D cell shapes in layered and pseudostratifed epithelia are largely governed by a competition between surface tension and intercellular adhesion. SimuCell3D enables the large-scale in silico study of 3D tissue organization in development and disease at a great level of detail.

The acquisition and maintenance of proper morphology are crucial for the normal physiological functioning of a biological tissue. Their disruptions are associated with a range of pathological conditions, including cancer and birth defects. The shape of tissues is determined by the dynamic positioning of their constituent cells, which can collectively deform or migrate to induce macroscopic changes in the tissue morphologies1,2 . These cellular behaviors are regulated by the mechanical properties of both cells and extracellular matrix (ECM)3 , along with the distribution of stresses within tissues4 . Therefore, understanding how tissues acquire and maintain their shapes requires a deep comprehension of the interplay between the stress distribution within them and the mechanical properties of their cells and ECM.

Various experimental methods have been developed to contribute to this understanding5–7 —for example, micropipette aspiration8 , atomic force microscopy9 , optical stretcher10 and laser ablation11. Nonetheless, these experimental techniques are generally limited to the rare tissues directly accessible to probing, or to small tissue portions. In addition, even when all the factors influencing a tissue morphology have been experimentally identified, their synergy might remain unclear.

Recent advances in the fields of fluorescent microscopy, image processing and computation power now allow us to complement these direct measurements with in silico models, and thus to gain a more global understanding of the cellular dynamics underlying tissue morphogenesis and homeostasis12–17. Among these numerical methods, cell-based models have become widely used in the fields of developmental and cancer biology due to their high spatiotemporal resolution and accurate predictions. Cell-based models recreate virtual versions of tissues by representing cells as individual agents with their own mechanical properties and behavior. These models offer an in silico environment where the stress distribution and the mechanical properties of cells can be modulated to study their impact on tissue morphology and function. Cell-based models can thus predict the tissue shape arising from experimentally measured cell properties or, conversely, in conjunction with parameter estimation methods, they can allow us to infer the cell properties that led to an imaged tissue morphology. The high level of spatiotemporal details of cell-based models, however, entails a substantial computational cost, which forces a trade-off between the number of cells they can simulate and the spatial resolution of their representation18. For this reason, cell-based models with varying levels of resolution have been developed to address different types of biological problem. For instance, center-based models are a class of cell-based models that represent cells as simple spheres, making

1 Department of Biosystems Science and Engineering (D-BSSE), ETH Zürich, Basel, Switzerland. 2 Swiss Institute of Bioinformatics (SIB), Basel, Switzerland. e-mail: dagmar.iber@bsse.ethz.ch

Table 1 | Comparison of SimuCell3D with existing 3D DCM models 

<table><tr><td>Program name</td><td>Pub. year</td><td>No. of cells after 1d of computation</td><td>Adjustable spatial resolution</td><td>Automatic mesh remodeling</td><td>Cell divisions</td><td>Cell polarization</td><td>Nuclei</td><td>ECM</td><td>Lumen</td><td>OS</td><td>Lic.</td><td>Ref.</td></tr><tr><td>SimuCell3D</td><td>2024</td><td>125,000</td><td>√</td><td>√</td><td>√</td><td>√</td><td>√</td><td>√</td><td>√</td><td>√</td><td>BSD-3</td><td>—</td></tr><tr><td></td><td>2023</td><td>unknown</td><td>√</td><td>√</td><td>√</td><td>✗</td><td>✗</td><td>✗</td><td>✗</td><td>✗</td><td>—</td><td>51</td></tr><tr><td></td><td>2023</td><td>unknown</td><td>√</td><td>√</td><td>√</td><td>√</td><td>✗</td><td>✗</td><td>✗</td><td>✗</td><td>—</td><td>52</td></tr><tr><td>IAS</td><td>2022</td><td>4</td><td>√</td><td>√</td><td>√</td><td>✗</td><td>✗</td><td>✗</td><td>✗</td><td>√</td><td>CC</td><td>47</td></tr><tr><td></td><td>2020</td><td>&lt;1,000</td><td>√</td><td>✗</td><td>√</td><td>√</td><td>√</td><td>✗</td><td>✗</td><td>✗</td><td>—</td><td>45</td></tr><tr><td>CellSim3D</td><td>2018</td><td>75,000</td><td>✗</td><td>✗</td><td>√</td><td>✗</td><td>✗</td><td>✗</td><td>✗</td><td>√</td><td>GPLv2</td><td>50</td></tr><tr><td></td><td>2014</td><td>starting number</td><td>√</td><td>√</td><td>✗</td><td>✗</td><td>✗</td><td>✗</td><td>✗</td><td>√</td><td>BSD-2</td><td>44</td></tr><tr><td></td><td>2013</td><td>starting number</td><td>√</td><td>√</td><td>✗</td><td>✗</td><td>✗</td><td>✗</td><td>✗</td><td>✗</td><td>—</td><td>53</td></tr><tr><td>The Surface Evolver</td><td>1992</td><td>starting number</td><td>√</td><td>✗</td><td>✗</td><td>✗</td><td>✗</td><td>✗</td><td>✗</td><td>√</td><td>—</td><td>49</td></tr></table>

Cell numbers are approximate. Pub., publication. Lic., license. OS, open source. Ref., reference. CC, Creative Commons. GPL, GNU General Public License. BSD, Berkeley Software Distribution.

them suitable for phenomena where the abundance of cells is more crucial than their shape. These models have been used to gain deeper understanding of a wide range of phenomena, including, for instance, the development of tumors19 or the inflammation of tissues20.

Vertex models are another class of cell-based model that have been developed to study tissues in which cell shapes can be approximated by polygons in two dimensions21–25 or polyhedra in three dimensions26. This simplification allows them to represent each cell with only a few points, enabling them to simulate large tissues. Vertex models have been employed to study a wide range of phenomena, including the transition between solid-like and fluid-like tissue states27, as well as various morphogenetic processes such as the polarization of early embryos28, the formation of branched structures29 and the biased elongation of tissues30,31. However, their simplistic representation of tissues comes with the drawback that they cannot adequately represent cells with complex shapes. Furthermore, the highly restricted topology permissible for the mesh in vertex models substantially complicates the simulation of phenomena such as cell extrusion or tissue fusion. The mechanisms underlying these developmental events are among the fundamental open problems in morphogenesis.

To address the limitations of vertex models, a family of cell-based models sometimes referred to as deformable cell models (DCMs) has been developed. These models provide a more geometrically realistic representation of tissues by discretizing each cell membrane separately into a closed loop of connected points in two dimensions32–43 or a closed triangulated surface in three dimensions44–53. The complex shapes that cells can adopt in DCMs make these models particularly suited to simulate phenomena such as the development of early embryos5 -54 or the cellular movements during wound healing45. However, the accuracy offered by these models comes at a staggering computational cost. To mitigate this computational cost, one 3D DCM implementation named CellSim3D50 constrains the cell geometries to spheroidal shapes. This approach is however not suited for the study of tissues with complex (non-polyhedral) cell shapes. The remaining 3D DCMs preserve a high geometrical resolution of the cell membranes but are limited by their computational efficiency. At best, they can simulate the growth of a tissue from one to a thousand cells in a week of computation time45, precluding their use for large-scale computational studies. Additionally, the numerical stability of these models may be compromised when the simulated cells undergo large deformations. We review the features of available 3D DCMs in Table 1.

Here we present SimuCell3D, an efficient open-source DCM in three dimensions. Thanks to its efficient design, SimuCell3D can simulate tissues composed of dozens of thousands of cells with high spatial resolution. SimuCell3D overcomes the classical trade-off that has so far constrained cell-based models between their resolutions and the number of cells they can simulate. In addition, our program natively allows us to represent intra- and extracellular entities such as nuclei, lumens, ECM and non-uniform mechanical cell membrane properties, as found in polarized cells (Fig. 1a). By combining speed and versatility, SimuCell3D can simulate processes that had not been amenable to existing numerical methods.

# Results

# Biophysical model

SimuCell3D aims to simulate the morphodynamics of cellular tissues at a high spatial resolution with full account of complex cell shapes. The shapes and motion of the simulated cells are not constrained by the model representation, and their mechanical properties are based on the physical principles governing the dynamics of their biological counterparts. This unconstrained representation of the cells is achieved by modeling their surfaces with disjoint closed triangulated surfaces (Fig. 1b). The spatial resolution of these surfaces can be tuned by adjusting the size of their triangles. To ensure that the simulations are initialized at the desired resolution, a custom triangulation algorithm has been incorporated into SimuCell3D (Supplementary Fig. 1), allowing the use of geometries obtained from microscopy images as the starting point of the simulations. A local remeshing algorithm (Supplementary Fig. 2) preserves the mesh resolution and quality even under large cell deformations. Apart from viscous damping as well as repulsive and adhesive cell–cell contacts, the biomechanical state of each cell membrane is defined by the following energy potential (Fig. 1c):

$$
U = K V \left(\ln \frac {V}{V _ {0}} - 1\right) + \frac {k _ {\mathrm{a}}}{2} \left(\frac {A}{A _ {0}} - 1\right) ^ {2} + \int_ {\partial \Omega} \left(\gamma + \frac {k _ {\mathrm{b}}}{2} (2 H) ^ {2}\right) \mathrm{d} S. \tag {1}
$$

The first term is the energy associated with a net internal pressure, $p { = } \mathrm { d } W / \mathrm { d } V { = } { - } K \ln ( V / V _ { 0 } )$ , which arises from the volumetric strain of the cell cytoplasm, modeled as a slightly compressible fluid. W denotes work, V and $V _ { 0 }$ are the current and target cell volumes and K the cytoplasmic bulk modulus. Shrinkage or growth of cells can be achieved by evolving their target volumes in time. The second energy term allows each cell to actively regulate its membrane area A by penalizing deviations from a target value $A _ { 0 }$ with an effective isotropic membrane elasticity parameter $k _ { \mathrm { a } } .$ . The first term in the surface integral, which runs over the cell surface ∂Ω, models the tension generated by the cell actomyosin cortex. γ is the isotropic cortical tension, analogous to the surface tension of fluid interfaces. The second integrand models the resistance of the cell cortex to bending55, with H denoting the local mean curvature of the cell membrane and $k _ { \mathrm { b } }$ its bending rigidity. γ and $k _ { \mathrm { b } }$ are field parameters that can vary along the cell surface according to cell polarity (Fig. 1b).

![](Jk2Mb6Ry4S_SimuCell3D组织力学_assets/images/33ba7c59a463dfc018097238534411bffb1dfb28463e7d6499e31b6cb57b51f5.jpg)  
Fig. 1 | Representation of cellular tissues in SimuCell3D. a Schematics of the features that cell-based models must possess to be applicable to a broad range of morphogenetic problems. b, Representation of cell membranes as closed triangulated surfaces with non-uniform material properties on the basis of cell polarity (colors). c, Summary of different forces acting on the triangulated cell membranes. d, Illustration of cell division perpendicular to a division plane   
(purple). e, Computational efficiency of different 3D cell-based models in an exponential-growth scenario. The dashed black line is a fitted power law T = aNα with coefficients a = 0.013 s and α = 1.33. f, Illustration of different tissue topologies and intra- or extracellular features that can be simulated with SimuCell3D. All surfaces can be non-convex.

SimuCell3D offers two distinct contact models to simulate intercellular interactions. The first model mediates interactions through local elastic contact forces, taking into account cell–cell adhesion and volumetric exclusion (Methods, equation (2), and Supplementary Fig. 3). Its two constitutive parameters, the adhesion strength ω and the repulsion strength ξ, are field quantities that can vary among cells or membrane regions. This contact model is somewhat dependent on mesh resolution (Supplementary Fig. 4), just as adhesion in biology will depend on the adhesion protein density. The second contact model mechanically couples the nodes of adjacent cells and directly transfers forces generated on one cell surface to that of the neighboring cell. We validated this second model by reproducing the Young–Dupré relationship in cell doublets and triplets (Supplementary Fig. 5a,c). The resulting contact mechanics are independent of mesh resolution (Supplementary Fig. 5a). All parameters related to intercellular interactions are summarized in Table 2.

SimuCell3D can simulate entities such as nuclei, lumens and ECMs by also representing them with closed triangulated surfaces similarly to the cell membranes. To model cell death, cells can be removed from the tissue if their volume drops below a minimum threshold $V _ { \mathrm { m i n } } .$ Conversely, if cell volumes exceed the maximal value $V _ { \mathrm { m a x } } ,$ they undergo cytokinesis (Fig. 1d). The division plane can be randomly oriented or perpendicular to the longest cell axis (Hertwig’s rule). A cell division only takes a few microseconds of computation time, allowing the simulation of tissues with high cell division rates. To demonstrate the computational efficiency and stability of our program, we simulated the exponential growth of a tissue in an out-of-equilibrium regime with the growth rate pushed to the limit, starting from a single cell (Fig. 1e and Supplementary Video 1). The cells in this test are simulated without nuclei. Only one day of computation time is required to grow the tissue to 125,000 cells on an Intel Xeon W-2245 CPU (eight cores, 3.9 GHz) using 16 threads, for cells that possess 121 nodes and 238 triangular faces on average. The total time complexity of such a simulation is $\mathcal { O } ( N _ { \mathrm { c } } ^ { 4 / 3 } )$ ), where $N _ { \mathrm { c } }$ is the number of cells in the tissue, which is equivalent to the scaling observed in two-dimensional simulations43. Under similar settings, we tested the performance of CellSim3D50 and Interacting Active Surfaces (IAS)47, two other cell-based 3D models offering low and high spatial resolution, respectively. CellSim3D generated a tissue of 75,000 cells in a day of computation time while IAS produced a tissue of 4 cells in the same amount of time. CellSim3D achieves performance comparable to that of our program by constraining the cell geometries to simple spherical shapes with a fixed number of nodes. SimuCell3D thus offers the performance of low-resolution models such as Cell-Sim3D while possessing the flexibility and accuracy of high-resolution models such as IAS. SimuCell3D is parallelized with OpenMP. The parallelization efficiency follows Amdahl’s law (Supplementary Fig. 6). To showcase the versatility of our program, we simulated various tissue topologies such as a vesicle, a bulk spheroid, a sheet and a tube, alongside several intra- or extracellular built-in features such as lumens, nuclei and ECM (Fig. 1f and Supplementary Video 2).

Table 2 | Model parameters 

<table><tr><td>Symbol</td><td>Default dynamic</td><td>Default overdamped</td><td>Measured</td><td>Unit</td><td>Dimension</td><td>Description</td><td>Ref.</td></tr><tr><td colspan="8">Cell volume parameters</td></tr><tr><td> $\rho$ </td><td>1,000</td><td>1,000</td><td>1,045–1,099</td><td>kgm $^{-3}$ </td><td>M/L $^{3}$ </td><td>Mass density</td><td>77</td></tr><tr><td>K</td><td>2,500</td><td>2,500</td><td>2,250</td><td>Pa</td><td>M/LT $^{2}$ </td><td>Bulk modulus</td><td>78</td></tr><tr><td> $p_{max}$ </td><td>2,500</td><td>2,500</td><td>300–2,200</td><td>Pa</td><td>M/LT $^{2}$ </td><td>Max. internal net pressure</td><td>79–81</td></tr><tr><td> $V_{min}$ </td><td> $3.7×10^{-16}$ </td><td> $3.7×10^{-16}$ </td><td> $2.5–3.7×10^{-16}$ </td><td>m $^{3}$ </td><td>L $^{3}$ </td><td>Min. volume (apoptosis)</td><td>64,82</td></tr><tr><td> $V_{max}$ </td><td> $1.4×10^{-15}$ </td><td> $1.4×10^{-15}$ </td><td> $0.9–1.3×10^{-15}$ </td><td>m $^{3}$ </td><td>L $^{3}$ </td><td>Max. volume (cell division)</td><td>64,82</td></tr><tr><td>g</td><td> $10^{-11}$ </td><td> $10^{-11}$ </td><td> $0.1–1.8×10^{-20}$ </td><td>m $^{3}$ s $^{-1}$ </td><td>L $^{3}$ /T</td><td>Volumetric growth rate</td><td>83,84</td></tr><tr><td colspan="8">Cell surface parameters</td></tr><tr><td> $\gamma$ </td><td>0.001</td><td>0.001</td><td>0.0005–0.0025</td><td>Nm $^{-1}$ </td><td>M/T $^{2}$ </td><td>Surface tension</td><td>81,85,86</td></tr><tr><td> $k_{b}$ </td><td> $2×10^{-18}$ </td><td> $2×10^{-18}$ </td><td> $1–2×10^{-18}$ </td><td>J</td><td>ML $^{2}$ /T $^{2}$ </td><td>Bending stiffness</td><td>87</td></tr><tr><td> $k_{a}$ </td><td> $10^{-15}$ </td><td> $10^{-15}$ </td><td>—</td><td>J</td><td>ML $^{2}$ /T $^{2}$ </td><td>Area elasticity modulus</td><td>—</td></tr><tr><td> $Q_{o}$ </td><td>250</td><td>250</td><td>300</td><td>—</td><td>—</td><td>Target isoparametric ratio</td><td>64</td></tr><tr><td> $\xi$ </td><td> $10^{9}$ </td><td> $10^{9}$ </td><td>—</td><td>Pam $^{-1}$ </td><td>M/L $^{2}$ T $^{2}$ </td><td>Repulsion strength</td><td>—</td></tr><tr><td> $\omega$ </td><td> $10^{9}$ </td><td> $10^{9}$ </td><td>—</td><td>Pam $^{-1}$ </td><td>M/L $^{2}$ T $^{2}$ </td><td>Adhesion strength</td><td>—</td></tr><tr><td> $H_{max}$ </td><td> $5×10^{6}$ </td><td> $5×10^{6}$ </td><td>—</td><td>m $^{-1}$ </td><td>1/L</td><td>Max. coupling curvature</td><td>—</td></tr><tr><td colspan="8">Numerical parameters</td></tr><tr><td> $l_{min}$ </td><td> $2×10^{-7}$ </td><td> $2×10^{-7}$ </td><td>—</td><td>m</td><td>L</td><td>Minimum edge length</td><td>—</td></tr><tr><td>c</td><td> $2×10^{-7}$ </td><td> $2×10^{-7}$ </td><td>—</td><td>m</td><td>L</td><td>Contact cutoff distance</td><td>—</td></tr><tr><td> $\zeta$ </td><td> $2.5×10^{-10}$ </td><td> $3×10^{-9}$ </td><td>—</td><td>kgs $^{-1}$ </td><td>M/T</td><td>Viscous damping coefficient</td><td>—</td></tr><tr><td> $\Delta t$ </td><td> $10^{-7}$ </td><td> $10^{-7}$ </td><td>—</td><td>s</td><td>T</td><td>Time step</td><td>—</td></tr></table>

Default parameter values are given for the two types of equation of motion implemented in SimuCell3D (dynamic versus overdamped). In the parameter dimension, M represents mass, L length and T time. Default values produce a typical tissue growth scenario.

# Cell membrane polarization

Cells form regions with distinct biochemical and mechanical properties along their cytoplasmic membranes. Correct establishment of this cell polarity is crucial to numerous developmental processes56. Its impairment has also been linked to the onset of tumor formation57. SimuCell3D takes cell polarity into account by allowing the triangular faces to be of different types with distinct mechanical parameters γ, $k _ { \mathrm { b } } ,$ ω and ξ. Two mechanisms are implemented to automatically identify different regions on the cell surfaces. In the first, lateral sides are inferred from the face contact information, leaving regions that are not in contact as either apical or basal. The second, more robust and versatile, algorithm is based on a spatial partitioning of the simulation domain into voxels representing one of four possible regions: cell boundaries, luminal, cytoplasmic and external (Fig. 2a–c). Voxels containing mesh nodes are marked as boundary voxels. The remaining unmarked voxels are clustered with the Hoshen–Kopelman algorithm58. The different voxel clusters thus created are then labeled as cytoplasmic, luminal or external on the basis of their positions in the discretized simulation space. Then, each surface triangle probes its environment by casting a ray in the direction of its outward normal to detect which type of region it faces (Fig. 2d). The type of voxel the ray first passes through determines whether the mesh triangle is lateral (facing another cell), apical (facing an enclosed volume such as a lumen) or basal (facing the surrounding medium or ECM). Iteration over all mesh triangles thus tags the entire surface (Fig. 2e). We demonstrate the capabilities of this approach by reproducing in silico a monolayer prostate organoid whose cells exhibit apicobasal polarity (Fig. 2f). The cell surfaces were extracted from 3D microscopy images with Cellpose59 (Fig. 2g). SimuCell3D then reproduced the organoid with correct tissue polarity (Fig. 2h) without requiring any input on tissue orientation or topology by the user.

# Application 1. Transition from monolayer to multilayer tissue

We now demonstrate how SimuCell3D can be used to gain insight into the cellular dynamics of biological tissues. As a first showcase, we investigate the relationship between biomechanical cell parameters and the internal structure of a tissue as a mono- or multilayer. Such a difference in cellular organization is particularly striking between different types of epithelial tissue60. Strong evidence suggests that this variability is the result of an interplay between intracellular surface tension and intercellular adhesion61,62. In a tug of war with cortical tension, in which the actomyosin cortex tends to minimize the cell surface area, adhesion molecules between adjacent cells tend to increase it. We investigated this competition by numerically exploring the parameter space spanned by adhesion strength and surface tension. The simulations were initialized with a spherical monolayer vesicle consisting of 432 columnar cells generated from a Voronoi tessellation of the sphere (Fig. 3a). All cells were initially in contact on their apical sides with a luminal region and on their basal sides with an ECM encasing the tissue. Note that no ECM located at the apical side of the cells nor any adhesion belt was considered in these simulations. The cells were grown at a uniform volumetric rate without division until they had doubled in size, while the luminal target volume was preserved. Despite cellular rearrangements caused by growth, we observed the maintenance of the monolayer structure in simulations with low surface tension (Fig. 3b). Strong cortical tension, on the other hand, leads to stratification (Fig. 3c). We quantified the resulting number of cell layers by converting the tissue into a graph representing cell connectivity and computing the shortest path percolating from the lumen to the ECM (Fig. 3d). Parameter values were non-dimensionalized with l = 〈V(t = 0)〉 1/3 as a characteristic length scale, and K as a characteristic energy density. Our exploration of the parameter space revealed that, under the prescribed conditions, the layering of the tissue is essentially regulated by the tension of the actomyosin cortex alone (Fig. 3e). An increase in the normalized surface tension γ̃ = γ/Kl from 0.02 to 0.10 was sufficient to break the monolayer arrangement and force the tissue into a stratified structure. Conversely, an increase by two orders of magnitude in the normalized adhesion strength ω˜ = ωl/K between the cells did not disrupt the monolayer integrity. As the cells lose their apicobasal connectivity at stronger surface tension, they adopt a more spherical shape that minimizes their surface area, as measured by their sphericity $\pmb { \psi } = \pi ^ { 1 / 3 } ( 6 V ) ^ { 2 / 3 } / A \left( \mathrm { F i g . } 3 \mathbf { f } \right)$ . These simulations highlight the potential of SimuCell3D to quantitatively address open questions in tissue development and cancer progression, the latter being linked to a loss of structural tissue integrity on the cellular level63.

![](Jk2Mb6Ry4S_SimuCell3D组织力学_assets/images/cc5f4bb2475992a9a098bf088a4fb1a0172f5ae6cfedfe9cf125ec606f8c786d.jpg)  
Fig. 2 | Automatic cell surface polarization algorithm. For visual clarity, the process is shown in two dimensions. a, The simulation space is discretized with uniformly sized cubic voxels. All voxels that intersect with the cell surfaces are marked as boundary voxels. b, All remaining voxels are clustered with the Hoshen--Kopelman algorithm. c, Voxel clusters are tagged as lumen, cytoplasm or exterior. d, A ray is cast from the center of each face in the outward normal direction. The first voxel (other than a boundary) that it intersects with indicates   
with which region the face is in contact. e, Facial types are assigned on the basis of the regions with which they are in contact. f, Cross-sectional light-sheet microscopy image of a mouse prostate organoid. Cell polarity is visualized by Ezrin staining (blue, apical side). g, 3D cell segmentation of the organoid. h, Simulated organoid with automatically polarized epithelial surfaces (blue, red). The different membrane regions can possess different surface tensions, bending rigidities, adhesion strengths and repulsion strengths. Scale bars, 15 μm.

# Application 2. Formation and maintenance of pseudostratification in epithelia

Pseudostratified epithelia are single-layered epithelia that are easily mistaken as stratified when analyzed in two-dimensional sections because of the dispersion of their nuclei along the apical–basal axis64. Their ubiquity across different species during development65 suggests that the pseudostratified structure can confer an advantage over simpler cellular arrangements, possibly linked to patterning precision66. How this structure is acquired and maintained under growth and morphogenetic deformation is still largely unknown. In this second case study, we demonstrate how SimuCell3D may be used to gain mechanistic insight into the elusive pseudostratification process. We initialized simulations with a patch of 70 cells segmented from light-sheet

microscopy images of the developing pseudostratified mouse lung epithelium64 (Fig. 4a). Among these 70 cells, the 21 interior cells were allowed to move freely while the rest on the periphery of the patch acted as static boundaries. The simulated cells all contained a nucleus (Fig. 4b, blue) and neither grew nor divided during the simulations, but deformed to minimize their potential energy, until static equilibrium was reached. We again examined the interplay between cell surface tension $( \tilde { \gamma } _ { \mathrm { c } } = \gamma _ { \mathrm { c } } / l _ { \mathrm { c } } K _ { \mathrm { c } }$ , subscript ‘c’ for cell) and adhesion strength $( \widetilde { \omega } _ { \mathrm { c } } = \omega _ { \mathrm { c } } l _ { \mathrm { c } } / K _ { \mathrm { c } } ) \left( \mathrm { F i g . 4 c , d } \right)$ . The normalized surface tension of the nuclei $( \tilde { \gamma } _ { \mathfrak { n } } = \gamma _ { \mathfrak { n } } / l _ { \mathfrak { n } } K _ { \mathfrak { n } }$ , subscript ‘n’ for nucleus) was kept constant at 0.24 in these simulations, and they were non-adhesive $\scriptstyle ( \omega _ { \mathrm { n } } = 0 )$ . In the explored region of the parameter space, we observed two unphysiological morphological cell regimes (I and II) with a continuous transition in between, along which an intermediate physiological range can be identified (Fig. 4c). In regime I, the cell shape is dominated by the effect of surface tension. Some of the cells segregated in response to the strong surface-area minimization tendency (Fig. 4c, left), facilitated by weak lateral adhesion. Cells in this regime reduced their lateral cell– cell contact area fraction ϕ (Fig. 4d) and also possessed fewer neighbors, as measured by their coordination number z (Fig. 4e). In regime II, the effect of adhesion dominates over surface tension, allowing neighboring cells to maximize their mutual contact areas (Fig. 4c, right; Fig. 4d) as well as their coordination number (Fig. 4e). In between these extremes, a balance between adhesion strength and cortical tension yields physiological cell shapes corresponding to those imaged (Fig. 4c, middle). This morphological similarity can be exploited to infer the mechanical properties of in vivo pseudostratified cells (Fig. 4d,e). Moreover, besides informing on the mechanical state of cells, Simu-Cell3D unveiled in this second case study the possibility that pseudostratified tissues could be formed from cells with identical mechanical properties.

![](Jk2Mb6Ry4S_SimuCell3D组织力学_assets/images/287ab500c3f86674b5115c49f2aba12c227292281b58ed534319b32e3bea22e0.jpg)

<details>
<summary>text_image</summary>

Initial geometry
ECM Lumen
432 cells
2× tissue volume growth
Final geometry (γ̃ = 0.16)
c
432 cells
b
432 cells
Final geometry (γ̃ = 0.02)
d
Lumen
N = 4
N = 3
Exterior
</details>

![](Jk2Mb6Ry4S_SimuCell3D组织力学_assets/images/561fe00b846fe71fa2fdc6663014e92e715d7056a026b3e95e351b59fb57d631.jpg)

![](Jk2Mb6Ry4S_SimuCell3D组织力学_assets/images/e87b9dc51fa27adefc4a68fa05f547bc749ac04f54860d3d1df49ceb2e358214.jpg)

<details>
<summary>scatter</summary>

| Surface tension (γ̃ = γ/kl) | Average cell sphericity (ψ) |
| -------------------------- | -------------------------- |
| 0.00                       | 0.75                       |
| 0.05                       | 0.78                       |
| 0.10                       | 0.85                       |
| 0.15                       | 0.90                       |
| 0.20                       | 0.92                       |
</details>

Fig. 3 | Impact of biomechanical cell properties on tissue structure. a, Initial tissue geometry: a hollow spherical vesicle made up of 432 columnar epithelial cells. The central luminal region (turquoise) was represented by a non-growing volume. On its basal side, the tissue was encased by a surface representing the ECM (red). b, Final monolayer conformation after epithelial volume doubling with weak cortical tension. c, Final multilayer conformation at strong cortical tension. d, Schematic cross-section through the epithelium with a cell   
connectivity graph on which the layer number N was determined. e, Impact of cell surface tension and adhesion strength on the average number of cell layers. Isolines represent support vector machine discriminants. Each data point corresponds to the final state of one numerical simulation. Simulations in which the whole tissue remained a monolayer (N ≡ 1) are shown as squares. f, Effect of cortical tension on cell shape, as measured by sphericity, and on the number of layers (colors). The dashed black curve is a fitted logistic function.

Subsequently, we used SimuCell3D to investigate the effect of mechanical properties of the nuclei on the pseudostratified cell organization (Fig. 4f,g). In these simulations, the cell surface tension $\tilde { \gamma } _ { \mathrm { c } } = 0 . 0 1$ and adhesion strength $\widetilde { \omega } _ { \mathrm { c } } = 0 . 9 7$ were fixed. By varying the nuclear surface tension $\tilde { \gamma } _ { \mathsf { n } } ,$ we were able to create nuclei rigid enough to deform the cell membranes (Fig. 4f). Cell deformation was measured by comparing the equilibrium cell shape in the presence of a nucleus versus that in its absence, quantified by the intersection over union: $\chi { = } 1 { - } \mathsf { l o } \mathsf { U } ( \varOmega$ with nucleus, Ω without nucleus). We observe an increase of the average cell deformation 〈χ〉 with the nucleus surface tension $\tilde { \gamma } _ { \mathfrak { n } }$ until the nuclei obtain spherical shapes at $\tilde { \gamma } _ { \mathfrak { n } } \approx 0 . 3 5$ . It then saturates at $\langle \chi \rangle \approx 0 . 1 3$ as nuclear tension increases further. The average sphericity of the nuclei has been measured in the segmented geometries at 0.89, suggesting a low cortical stiffness of the nuclear envelopes relative to the cytoplasmic membranes.

SimuCell3D also allows us to directly modulate the shapes of nuclei or cells by concurrently varying their target isoperimetric ratios $Q _ { 0 , \mathfrak { n } } = A _ { 0 , \mathfrak { n } } ^ { 3 } / V _ { 0 , \mathfrak { n } } ^ { 2 }$ , and area elasticity modul $\lvert k _ { \mathrm { a , r } }$ (Fig. 4g). Simultaneously increasing $Q _ { 0 , \mathfrak { n } }$ and $k _ { \mathrm { a , n } }$ drives the equilibrium shapes of nuclei away from a sphere. Conversely, nuclei with small values of $\scriptstyle \mathbf { \dot { Q } } _ { 0 , \mathfrak { n } }$ and $k _ { \mathrm { a , n } }$ possess more spherical shapes. The ability to thus change the stiffness or shape of the nuclei opens up opportunities to study the dynamics of interkinetic nuclear migration67.

# Discussion

SimuCell3D now permits the in-depth in silico investigation of the mechanical properties and behavior of cells to understand the mechanisms that regulate tissue homeostasis and morphogenesis. While the current simulations were carried out with linear mechanical models, nonlinear material behavior (viscoelasticity, hyperelasticity) could readily be implemented to study its effect on morphogenesis. Moreover, besides nuclei, organelles and endocytosis could be easily represented. As such, processes such as interkinetic nuclear migration in pseudostratified epithelia could be simulated at unprecedented resolution to address open questions regarding the driving forces.

As we showed, SimuCell3D can be used to predict the global tissue morphologies that emerge from individual mechanical cell properties. Specifically, when the morphological features of the tissues are known, SimuCell3D can be used to infer the region of the mechanical parameter space in which the cells are located. Our exploration of the cellular parameter space in this study was mainly limited to the subspace spanned by cell cortical tension and adhesion strength. This subspace is insufficient to reproduce the wealth of morphogenetic events observed in vivo. In other contexts, exploration of higher-dimensional parameter spaces will undoubtedly be necessary. In these circumstances, SimuCell3D can be coupled with gradient-free parameter estimation techniques to accurately infer the cell properties that lead to the measured morphological tissue features.

SimuCell3D is readily extendable to accommodate more features in the future. Relevant possible extensions include subcellular components such as adhesion belts, frictional forces, (which play an important role in the morphogenesis of some tissues68) as implemented in pre-existing models45,5 2, tension fluctuations69 and reaction–diffusion models to couple the biomechanical tissue model with chemical signaling. In this way, chemical and mechanical symmetry-breaking mechanisms could be combined and their effects could be simulated at cellular resolution. Finally, the cell-based simulations could be combined with continuum models to simulate the behavior of larger tissues at varying resolution, and to derive adequate material models for the continuum description from cell-based simulations.

![](Jk2Mb6Ry4S_SimuCell3D组织力学_assets/images/e94f9a4269c8bb13a07f1cfc008c3b545faa09b3e9494881eb46d42b6030ba37.jpg)

<details>
<summary>text_image</summary>

a
Apical side
Basal side
Simulated cells
Static cells
</details>

![](Jk2Mb6Ry4S_SimuCell3D组织力学_assets/images/58afd63dc8ae38280ac8fa9d8a66678c24e6262dddb1fcea29d4adecf438f66e.jpg)

<details>
<summary>scatter</summary>

| Cell surface tension (γc = γc/lc Kc) | Cell adhesion strength (ω̃c = ωc/lc / Kc) | Average contact area ⟨φ⟩ |
| ------------------------------------- | ---------------------------------------- | ------------------------ |
| 10⁻³                                  | ~10⁰                                     | ~0.7                     |
| 10⁻²                                  | ~10¹                                     | ~0.8                     |
| 10⁻²                                  | ~10²                                     | ~0.9                     |
</details>

![](Jk2Mb6Ry4S_SimuCell3D组织力学_assets/images/eb6e3c22bcdbbed6c254441fa19d64aa055822570f681cc5a7b33fd535f8a3ef.jpg)

<details>
<summary>scatter</summary>

| Cell surface tension (Ṽc = Vc/Lc Kc) | Cell adhesion strength (ω̃c = ωc/Lc / Kc) | Average coordination number ⟨z⟩ |
| ------------------------------------- | ---------------------------------------- | ------------------------------- |
| 10⁻³                                  | 10⁰                                      | 9                               |
| 10⁻²                                  | 10¹                                      | 10                              |
| 10⁻²                                  | 10²                                      | 11                              |
</details>

![](Jk2Mb6Ry4S_SimuCell3D组织力学_assets/images/5b2abe390919f0b50fbd3e0f72c181afdbf05832b164e7e8e4a33d7db9fa4bd3.jpg)

<details>
<summary>text_image</summary>

b
Initial cell shape
Energy minimization
Nucleus
c
Final cell shapes
I
II
\(\tilde{Y}_c = 0.05 \quad \tilde{Y}_c = 0.03 \quad \tilde{Y}_c = 0.01\)
\(\tilde{\omega}_c = 0.35 \quad \tilde{\omega}_c = 10.0 \quad \tilde{\omega}_c = 16.3\)
</details>

![](Jk2Mb6Ry4S_SimuCell3D组织力学_assets/images/215ec91416669113431c08ba939fe846e9f77423b6ae76d22f2da16d217af87b.jpg)

<details>
<summary>line</summary>

| Nucleus surface tension (ν̃ₙ = γₙ/ℓₙ Kₙ) | Cell deformation ⟨x⟩ |
| ---------------------------------------- | --------------------- |
| 0.0                                      | 0.04                  |
| 0.2                                      | 0.12                  |
| 0.4                                      | 0.16                  |
| 0.6                                      | 0.16                  |
</details>

![](Jk2Mb6Ry4S_SimuCell3D组织力学_assets/images/8e02860d84224541994c299784425992f609a6624fe60a46f7359ab728a122b5.jpg)

<details>
<summary>scatter</summary>

| Nucleus target isoperimetric ratio (Qo,n) | Nucleus area elasticity modulus (k̃a,n = kₐ,n / tᵢₙ³Kₙ) | Nucleus sphericity ⟨ψ⟩ |
| ------------------------------------------ | -------------------------------------------------- | --------------------- |
| 0                                          | 10⁸                                                | 0.900                 |
| 250                                        | 10⁷                                                | 0.925                 |
| 500                                        | 10⁷                                                | 0.950                 |
| 750                                        | 10⁷                                                | 0.900                 |
| 1000                                       | 10⁷                                                | 0.925                 |
</details>

Fig. 4 | Simulation of 3D cell organization pseudostratified epithelia. a, Initial geometry imported into SimuCell3D: a patch of 70 cells from the developing pseudostratified mouse lung epithelium, segmented and triangulated from light-sheet imaging64. 49 gray cells act as rigid boundaries for the 21 simulated pink cells. b, All cells contain a nucleus (blue). c, On the basis of the cell surface tension and adhesion strength, the cells adopt different shapes (regimes I and II). d, Mean fraction of cell surface area in contact with other cells (red line in illustration), as a function of the adhesion strength and cortical tension. e, Mean   
cell coordination number in the same parameter space. f, Mean cell deformation as a function of the nuclear surface tension. Error bars represent the s.e.m., n = 21 nuclei. g, Average nuclear sphericity as a function of the nucleus area elasticity modulus and target isoperimetric ratio. Isolines in d,e,g represent support vector machine discriminants. Dashed curves in d–g represent the physiological values measured from the segmented geometries. Each data point corresponds to the equilibrium state obtained from one numerical simulation.

# Methods

# Mesh operations

Local mesh adaptation. SimuCell3D geometrically represents cells by closed triangulated surfaces whose edge lengths l are maintained within the range $[ l _ { \mathrm { m i n } } , l _ { \mathrm { m a x } } ]$ with a local mesh adaptation method. The minimum edge length $l _ { \mathrm { m i n } }$ is a model parameter, whereas $l _ { \mathrm { m a x } } = 3 l _ { \mathrm { m i n } } ,$ a value that works well in most practical applications, is automatically set. When the length of an edge exceeds $l _ { \mathrm { m a x } } ,$ the local mesh adaptation method splits it in two (Supplementary Fig. 2a), adding one node and two faces to the mesh. The two nodes constituting the divided edge transfer a third of their momentum to the newly created middle node to ensure momentum continuity. When an edge shrinks to a length below $l _ { \mathrm { m i n } } ,$ it is collapsed into a node whose new momentum is the sum of the merged nodes (Supplementary Fig. 2b). This merging process eliminates one node and two faces from the cell mesh. To prevent triangles with vanishing area, this operation is allowed only when the two nodes to be merged share exactly two other nodes among those connected to them through edges.

Triangular faces with high isoperimetric ratios can be a source of numerical instability. An edge swap operation prevents their formation. First, the quality score $S _ { f } = { 3 6 A _ { f } } / { \sqrt { 3 } P _ { f } ^ { 2 } }$ of each face f is computed, where $P _ { f }$ is its perimeter and $A _ { f }$ its area. Undesirable faces with high isoperimetric ratios have scores tending to zero, whereas $S _ { f } { = } 1$ for equilateral triangles. Faces with $S _ { f } { < } 0 . 3$ are eliminated by an edge swap operation (Supplementary Fig. 2c) that locally reconnects mesh nodes, but leaves them otherwise unaffected.

Initial triangulation. A flexible triangulation algorithm ensures that simulations are initialized with meshes that respect the edge length bounds (Supplementary Fig. 1a). The procedure takes an initial geometry of the tissue as input, with cell meshes that are not necessarily triangular yet, in the widely used VTK format70. The cell surfaces are then individually sampled with the Poisson disk sampling algorithm71 (Supplementary Fig. 1b) with a minimal point separation of $l _ { \mathrm { m i n } } .$ The ball pivoting algorithm72,73 then separately re-triangulates the surface of each cell on the basis of its Poisson point cloud (Supplementary Fig. 1c). The resulting meshes have l ≥ $l _ { \mathrm { m i n } } ,$ rarely exceeding $l _ { \mathrm { m a x } } .$ . Edges with $l > l _ { \mathrm { m a x } }$ are removed before the simulation starts with the edge division operation described above.

Cell division. Cells are divided on the basis of a volume threshold, that $\mathbf { i s } , \mathbf { i f } V > V _ { \operatorname* { m a x } } .$ They are bisected by a plane running through their centroid, whose orientation can depend on the cell type. The orientation is either random or perpendicular to the cell’s longest axis, as given by the eigenvector belonging to the smallest eigenvalue of its covariance matrix. During division, the cutting planes are re-triangulated in a manner respecting the edge length bounds. On the untriangulated region of the daughter cells, points are first sampled with the Poisson point cloud algorithm71, and are then connected with the two-dimensional Delaunay triangulation algorithm. This method avoids a retriangulation of the parts of the cell surface inherited from the mother cell.

# Cell volume and area calculation

The cell volume is calculated with a three-dimensional variant of the shoelace formula:

$$
V = \frac {1}{6} \left| \sum_ {f \in \mathcal {M}} \det \left[ \begin{array}{c c c} | & | & | \\ \mathbf {r} _ {i} & \mathbf {r} _ {j} & \mathbf {r} _ {k} \\ | & | & | \end{array} \right] \right|,
$$

where $\mathbf { r } _ { i } , \mathbf { r } _ { j }$ and $\mathbf { r } _ { k }$ are the nodal positions of face f (Fig. 1c). The summation runs over all the triangular faces of the cell mesh ℳ. The cell surface area is obtained by summing the areas of its faces:

$$
A = \sum_ {f \in \mathcal {M}} A _ {f} = \sum_ {f \in \mathcal {M}} \frac {1}{2} \left\| \mathbf {n} _ {f} \right\|,
$$

where $\boldsymbol { \mathsf { n } } _ { f } { = } \left( \boldsymbol { \mathsf { r } } _ { j } { - } \boldsymbol { \mathsf { r } } _ { i } \right) \times \left( \boldsymbol { \mathsf { r } } _ { k } { - } \boldsymbol { \mathsf { r } } _ { i } \right)$ is the unnormalized outward normal of face f.

# Time integration

SimuCell3D offers two modes of time propagation, solving either the dynamic or overdamped equations of motion for the nodal positions ri ,

$$
m \ddot {\mathbf {r}} _ {i} + \zeta \dot {\mathbf {r}} _ {i} = \mathbf {f} _ {i}.
$$

The nodal mass m is obtained from V and mass density $\rho \operatorname { a s } m = \rho V / N _ { \mathrm { n } } ,$ where $N _ { \mathfrak { n } }$ is the total number of nodes in the cell mesh. $\mathbf { f } _ { i }$ is the nodal force vector (specified below) and ζ the viscous damping coefficient. The first mode resolves elastic oscillations, making it suited for phenomena on short timescales. The nodal positions r and linear momenta $\mathbf { p } _ { i } = m \mathbf { r }$ i are integrated with the semi-implicit Euler scheme:

$$
\mathbf {p} _ {i} \leftarrow \mathbf {p} _ {i} + \Delta t \left(\mathbf {f} _ {i} - \zeta \mathbf {p} _ {i} / m\right),
$$

$$
\mathbf {r} _ {i} \leftarrow \mathbf {r} _ {i} + \Delta t \mathbf {p} _ {i} / m,
$$

where Δt is a fixed time increment. The second mode neglects inertial effects $( m { \ddot { \mathbf { r } } } _ { i } = 0 )$ and is therefore suitable for systems dominated by viscous relaxation toward a quasistatic equilibrium. The overdamped equations of motion are solved with the forward Euler scheme:

$$
\mathbf {r} _ {i} \leftarrow \mathbf {r} _ {i} + \Delta t \mathbf {f} _ {i} / \zeta .
$$

The simulations presented in Figs. 1, 3 and 4 were solved with the dynamic model. Simulation snapshots are written at regular time intervals in VTK format for post-processing and visualization in Para-View (Kitware).

# Nodal forces

The total conservative nodal forces $\mathbf { f } _ { i }$ derive from the cell potential energy (equation (1)) and the intercellular interaction model. They are given by the sum of the surface tension forces, $\mathbf { f } _ { s , i } ,$ the membrane area elasticity forces, $\mathbf { f } _ { \mathrm { m } , i } ,$ pressure forces exerted by the cytoplasm, $\mathbf { f } _ { \mathsf { p } , i } ,$ the bending forces, $\mathbf { f } _ { \mathrm { b } , i } ,$ and contact forces due to adhesion and steric repulsion, $\mathbf { f } _ { \mathrm { c } , i } \mathrm { : }$

$$
\mathbf {f} _ {i} = \mathbf {f} _ {\mathrm{s}, i} + \mathbf {f} _ {\mathrm{m}, i} + \mathbf {f} _ {\mathrm{p}, i} + \mathbf {f} _ {\mathrm{b}, i} + \mathbf {f} _ {\mathrm{c}, i}.
$$

Each of these contributions is detailed in the following paragraphs. Surface tension. The surface tension force is given by the negative gradient of the surface tension energy with respect to the nodal position. Since the position of node i affects the areas of only the set of faces ℱ sharing this node, it is given by

$$
\mathbf {f} _ {s, i} = - \sum_ {f \in \mathcal {F} _ {i}} \gamma_ {f} \nabla_ {i} A _ {f},
$$

where $\gamma _ { f }$ is the surface tension of face f. For triangles with nodes $i , j , k$ oriented clockwise (Fig. 1c), the area gradient reads

$$
\nabla_ {i} A _ {f} = \frac {1}{2} \hat {\mathbf {n}} _ {f} \times (\mathbf {r} _ {k} - \mathbf {r} _ {j}),
$$

where $\hat { \mathbf { n } } _ { f } = \mathbf { n } _ { f } / \left\| \mathbf { n } _ { f } \right\| ,$ is the normalized face normal vector.

Membrane area elasticity. Similarly, the membrane force is obtained by taking the gradient of the cell membrane area energy with respect to $\mathbf { r } _ { i } \mathbf { : }$

$$
\mathbf {f} _ {\mathrm{m}, i} = - \frac {k _ {\mathrm{a}}}{A _ {0}} \left(\frac {A}{A _ {0}} - 1\right) \sum_ {f \in \mathcal {F} _ {i}} \nabla_ {i} A _ {f}.
$$

$A _ { 0 }$ is coupled to $V _ { 0 }$ via $A _ { 0 } = \sqrt [ 3 ] { Q _ { 0 } V _ { 0 } ^ { 2 } } .$ , where $Q _ { 0 }$ is the target isoperimetric ratio of the cell, which can be set by the user. For a sphere, $Q _ { 0 } = 3 6 \pi \approx 1 1 3 .$ .

Pressure. The cell-internal net pressure generated by the cytoplasm reads

$$
p = \frac {\mathrm{d} W}{\mathrm{d} V} = - K \ln \frac {V}{V _ {0}},
$$

where $W { = } { - } K U { \ l } \mathsf { l n } ( V / V _ { 0 } ) { - } \mathbf { 1 } ]$ is the work associated with a deviation of V from its reference value $V _ { 0 } .$ To model cell growth, $V _ { 0 }$ can evolve over time according to prescribed growth laws, such as the linear form d $V _ { 0 } / \mathrm { d } t = g ,$ where g is a constant volumetric growth rate that can vary from cell to cell. If desired, the pressure difference between the cell cytoplasm and the external medium can be capped at a predefined threshold $p _ { \mathrm { m a x } }$ , that is $p  \operatorname* { m i n } \{ p , p _ { \operatorname* { m a x } } \} .$ . The pressure force exerted on a subset of the cell surface ${ \mathcal { S } } \subset { \partial \Omega }$ (where Ω is the cell domain) is given by

$$
\mathbf {f} _ {\mathrm{p}, \mathcal {S}} = p \int_ {\mathcal {S}} \hat {\mathbf {n}} \mathrm{d} S.
$$

If the subset ? of the cell surface is planar, like the triangular faces f used to discretize the cell geometry, this simplifies to

$$
\mathbf {f} _ {\mathrm{p}, f} = p A _ {f} \hat {\mathbf {n}} _ {f}.
$$

The pressure force applied on each node of the cell mesh therefore follows as

$$
\mathbf {f} _ {\mathrm{p}, i} = \frac {1}{3} \sum_ {f \in \mathcal {F} _ {i}} \mathbf {f} _ {\mathrm{p}, f}.
$$

Membrane bending. The contribution of bending to the cell potential energy can be approximated with the discrete bending energy74

$$
U _ {\mathrm{b}} \approx \sum_ {(i, j)} \bar {k} _ {\mathrm{b}} \frac {\left\| \mathbf {e} _ {i j} \right\| ^ {2}}{A _ {i j}} \left(2 \cos \frac {\theta_ {i j}}{2}\right) ^ {2}
$$

in which the sum runs over all pairs of nodes $( i , j )$ of the surface mesh connected by an edge. Each edge connects two faces a, b that form a diamond region composed of four nodes $i , j , k , l \left( \mathsf { F i g . 1 c } \right)$ .

$\overline { { k } } _ { \mathrm { b } } = ( k _ { \mathrm { b } , a } + k _ { \mathrm { b } , b } ) / 2$ is the average bending stiffness of the faces a and b, $\mathbf { e } _ { i j } = \mathbf { r } _ { j } - \mathbf { r } _ { i }$ i the vector pointing from node i to j, ${ \cal A } _ { i j } = { \cal A } _ { a } + { \cal A } _ { b }$ the sum of the two face areas and $\theta _ { i j }$ the dihedral angle between the two faces:

$$
\theta_ {i j} = - \operatorname{sgn} \left(\hat {\mathbf {n}} _ {a} \cdot \mathbf {e} _ {i l}\right) \arccos \left(- \hat {\mathbf {n}} _ {a} \cdot \hat {\mathbf {n}} _ {b}\right).
$$

The sign of the dot product between the normal of face a $( \hat { \bf n } _ { a } )$ and the vector $\mathbf { e } _ { i l }$ is used to distinguish between concave and convex hinges. The bending forces resulting from this discrete bending energy can be calculated independently for each of the four nodes, $q \in \{ i , j , k , l \} ,$ , as

$$
\mathbf {f} _ {\mathrm{b}, q} = 2 k _ {\mathrm{b}} \left[ \frac {\left\| \mathbf {e} _ {i j} \right\| ^ {2}}{A _ {i j}} \sin \theta_ {i j} \nabla_ {q} \theta_ {i j} - (1 + \cos \theta_ {i j}) \nabla_ {q} \left(\frac {\left\| \mathbf {e} _ {i j} \right\| ^ {2}}{A _ {i j}}\right) \right].
$$

For the gradients $\nabla _ { q } \theta _ { i j }$ and $\nabla _ { q } ( \| \mathbf e _ { i j } \| ^ { 2 } / A _ { i j } )$ we refer the interested reader to ref. 74. The total bending force at node i $\mathbf { \Delta } , \mathbf { f } _ { \mathrm { b } , i } ,$ then follows as the sum of bending forces over all diamond regions involving that node.

Intercellular contacts. SimuCell3D offers two different contact models that vary in their methods of exchanging contact forces between adjacent cells, but in the current version it does not take friction into account. (For possible ways to include frictional effects, see for example refs. 43,45.) The first model connects adjacent pairs of faces $\{ f _ { a } , f _ { b } \}$ with elastic springs, while the second tightly couples pairs of adjacent nodes $\{ n _ { a } , n _ { b } \}$ .

The spring-based model applies contact forces on pairs of adjacent faces with a magnitude based on the signed distance $d _ { a b } = \mathrm { s g n } \left( \mathbf { z } \cdot \hat { \mathbf { n } } _ { a } \right)$ ‖z‖ between the two mesh elements, where $\hat { \mathbf { n } } _ { a }$ is the unit normal of face a and z is the shortest vector between the two mesh elements. A contact stress is then calculated with the piecewise expression

$$
\sigma_ {a b} = \left\{ \begin{array}{l l} \xi d _ {a b} & \text { if } d _ {a b} \in [ - c, 0) \\ \omega d _ {a b} & \text { if } d _ {a b} \in [ 0, c / 2) \\ \omega (c - d _ {a b}) & \text { if } d _ {a b} \in [ c / 2, c ] \\ 0 & \text { otherwise } \end{array} . \right. \tag {2}
$$

When two neighboring cells interpenetrate, $\mathcal { A } _ { a b }$ is negative, and the contact stress is repulsive. On the other hand, when $d _ { a b } \mathbf { i }$ s positive, the contact stress is adhesive. In this regime, the contact model follows a bilinear traction–separation law (Supplementary Fig. 1). The contact stress $\sigma _ { a b }$ thus obtained is translated into a force by integrating the contact stress over the contact surface area $A _ { a b } \mathrm { : }$

$$
\mathbf {f} _ {a b} = \operatorname{sgn} (\mathbf {z} \cdot \hat {\mathbf {n}} _ {a}) A _ {a b} \sigma_ {a b} \frac {\mathbf {z}}{\| \mathbf {z} \|}.
$$

$A _ { a b } = \mathsf { m i n } \{ A _ { a } , A _ { b } \}$ if the contact forces are computed between pairs of faces $\{ f _ { a } , f _ { b } \} _ { i }$ , whereas $A _ { a b } = A _ { a }$ if the contact forces are calculated between pairs of faces and vertices $\{ f _ { a } , v _ { b } \}$ . In the first case, the force is linearly distributed to the nodes of face $a , \{ i , j , k \}$ , and the nodes of face b, {l, m, n}:

$$
\mathbf {f} _ {\mathrm{c}, i} = \alpha_ {a} \mathbf {f} _ {a b}, \mathbf {f} _ {\mathrm{c}, j} = \beta_ {a} \mathbf {f} _ {a b}, \mathbf {f} _ {\mathrm{c}, k} = \lambda_ {a} \mathbf {f} _ {a b},
$$

$$
\mathbf {f} _ {\mathrm{c}, l} = - \alpha_ {b} \mathbf {f} _ {a b}, \mathbf {f} _ {\mathrm{c}, m} = - \beta_ {b} \mathbf {f} _ {a b}, \mathbf {f} _ {\mathrm{c}, n} = - \lambda_ {b} \mathbf {f} _ {a b}.
$$

$( \alpha _ { a } , \beta _ { a } , \lambda _ { a } )$ ) and $( \alpha _ { b } , \beta _ { b } , \lambda _ { b } )$ are the barycentric coordinates of the closest points of approach on faces a and b, respectively.

The second contact model eliminates the need for a finite ω by establishing a tight coupling between node pairs $\{ \boldsymbol { n } _ { a } , \boldsymbol { n } _ { b } \}$ whose distance is smaller than the contact cutoff c. The two nodes are relocated to their average location $( { \pmb { \mathrm { r } } } _ { a } + { \pmb { \mathrm { r } } } _ { b } ) / 2$ , and the forces and momenta acting on each node are transmitted to its partner such that both nodes subsequently follow the same dynamics: $\mathbf { f } _ { i } \gets ( \mathbf { f } _ { a } + \mathbf { f } _ { b } ) / 2$ and $\pmb { \mathsf { p } } _ { i } \gets ( \pmb { \mathsf { p } } _ { a } + \pmb { \mathsf { p } } _ { b } ) / 2 , i = a , b .$ . To allow two adjacent cells to detach from each other, node pairs are coupled only if the local mean curvature of both cell surfaces lies below the threshold $H _ { \mathrm { m a x } }$ (Table 2). Coupled node pairs are redetermined in each time step, and each node is allowed to be coupled to no more than one other node.

# Reporting summary

Further information on research design is available in the Nature Portfolio Reporting Summary linked to this article.

# Data availability

The raw data generated as part of this study are publicly available and can be downloaded at https://u.ethz.ch/7Taih (ref. 75). Source data are provided with this paper.

# Code availability

SimuCell3D is open source and freely available as a public git repository at https://git.bsse.ethz.ch/iber/Publications/2024\_runser\_simucell3d under the three-clause BSD license76.

# References

1. Sehring, I. et al. An equatorial contractile mechanism drives cell elongation but not cell division. PLoS Biol. 12, e1001781 (2014).   
2. Friedl, P. & Gilmour, D. Collective cell migration in morphogenesis, regeneration and cancer. Nat. Rev. Mol. Cell Biol. 10, 445–457 (2009).   
3. Cruz Walma, A. & Yamada, K. M. The extracellular matrix in development. Development 147, 2418–2423 (2020).   
4. Heisenberg, C. & Bellaïche, Y. Forces in tissue morphogenesis and patterning. Cell 153, 948–962 (2013).   
5. Gómez-González, M., Latorre, E., Arroyo, M. & Trepat, X. Measuring mechanical stress in living tissues. Nat. Rev. Phys. 2, 300–317 (2020).   
6. Sugimura, K., Lenne, P.-F. & Graner, F. Measuring forces and stresses in situ in living tissues. Development 143, 186–196 (2016).   
7. Zhang, J., Chada, N. C. & Reinhart-King, C.-A. Microscale interrogation of 3D tissue mechanics. Front. Bioeng. Biotechnol. 7, 412 (2023).   
8. Mitchison, J. M. & Swann, M. M. The mechanical properties of the cell surface: III. The sea-urchin egg from fertilization to cleavage. J. Exp. Biol. 32, 734–750 (1955).   
9. Radmacher, M., Tillmann, R., Fritz, M. & Gaub, H. E. From molecules to cells: imaging soft samples with the atomic force microscope. Science 257, 1900–1905 (1992).   
10. Guck, J. et al. The optical stretcher: a novel laser tool to micromanipulate cells. Biophys. J. 81, 767–784 (2001).   
11. Vogel, A. & Venugopalan, V. Mechanisms of pulsed laser ablation of biological tissues. Biophys. J. 103, 577–644 (2003).   
12. Dillon, R. & Othmer, H. G. A mathematical model for outgrowth and spatial patterning of the vertebrate limb bud. J. Theor. Biol. 197, 295–330 (1999).   
13. Brodland, G. W. et al. Video force microscopy reveals the mechanics of ventral furrow invagination in Drosophila. Proc. Natl Acad. Sci. USA 107, 22111–22116 (2010).   
14. Ogita, G. et al. Image-based parameter inference for epithelial mechanics. PLOS Comput. Biol. 18, e1010209 (2022).   
15. Rodriguez, M. L., McGarry, P. J. & Sniadecki, N. J. Review on cell mechanics: experimental and modeling approaches. Appl. Mech. Rev. 65, 060801 (2013).   
16. Vaziri, A. & Gopinath, A. Cell and biomolecular mechanics in silico. Nat. Mater. 7, 15–23 (2008).   
17. Schamberger, B. et al. Curvature in biological systems: its quantification, emergence, and implications across the scales. Adv. Mater. 35, 2206110 (2023).

18. Osborne, J. M., Fletcher, A. G., Pitt-Francis, J. M., Maini, P. K. & Gavaghan, D. J. Comparing individual-based approaches to modelling the self-organization of multicellular tissues. PLoS Comput. Biol. 13, e1005387 (2017).   
19. Drasdo, D. & Höhme, S. A single-cell-based model of tumor growth in vitro: monolayers and spheroids. Phys. Biol. 2, 133 (2005).   
20. Dutta-Moscato, J. et al. A multiscale agent-based in silico model of liver fibrosis progression. Front. Bioeng. Biotechnol. 2, 18 (2014).   
21. Oster, G. & Weliky, M. The mechanical basis of cell rearrangement I. Epithelial morphogenesis during fundulus epiboly. Development 109, 373–386 (1990).   
22. Kawasaki, K., Nagai, T. & Nakashima, K. Vertex models for two-dimensional grain growth. Phil. Mag. B 60, 399–421 (1989).   
23. Nagai, T. & Honda, H. A dynamic cell model for the formation of epithelial tissues. Phil. Mag. B 81, 699–719 (2001).   
24. Farhadifar, R., Röper, J. C., Aigouy, B., Eaton, S. & Jülicher, F. The influence of cell mechanics, cell–cell interactions, and proliferation on epithelial packing. Curr. Biol. 17, 2095–2104 (2007).   
25. Fletcher, A. G., Osterfield, M., Baker, R. E. & Shvartsman, S. Y. Vertex models of epithelial morphogenesis. Biophys. J. 106, 2291–2304 (2014).   
26. Honda, H., Tanemura, M. & Nagai, T. A three-dimensional vertex dynamics cell model of space-filling polyhedra simulating cell behavior in a cell aggregate. J. Theor. Biol. 226, 439–453 (2004).   
27. Bi, D., Lopez, J. H., Schwarz, J. M. & Manning, M. L. A densityindependent rigidity transition in biological tissues. Nat. Phys. 11, 1074–1079 (2015).   
28. Honda, H., Motosugi, N., Nagai, T., Tanemura, M. & Hiiragi, T. Computer simulation of emerging asymmetry in the mouse blastocyst. Development 135, 1407–1414 (2008).   
29. Rozman, J., Krajnc, M. & Ziherl, P. Collective cell mechanics of epithelial shells with organoid-like morphologies. Nat. Commun. 11, 3805 (2020).   
30. Honda, H., Nagai, T. & Tanemura, M. Two diferent mechanisms of planar cell intercalation leading to tissue elongation. Dev. Dyn. 237, 1826–1836 (2008).   
31. Conrad, L. et al. The biomechanical basis of biased epithelial tube elongation in lung and kidney development. Development 148, dev194209 (2021).   
32. Rejniak, K. A. A single-cell approach in modeling the dynamics of tumor microregions. Math. Biosci. Eng. 2, 643–655 (2005).   
33. Tamulonis, C. et al. A cell-based model of Nematostella vectensis gastrulation including bottle cell formation, invagination and zippering. Dev. Biol. 351, 217–228 (2011).   
34. Merks, R. M. H., Guravage, M., Inzé, D. & Beemster, G. T. S. VirtualLeaf: an open-source framework for cell-based modeling of plant tissue growth and development. Plant Physiol. 155, 656–666 (2011).   
35. Ataeia, M. et al. LBfoam: an open-source software package for the simulation of foaming using the lattice Boltzmann method. Comput. Phys. Commun. 259, 107698 (2021).   
36. Kähärä, T., Tallinen, T. & Timonen, J. Numerical model for the shear rheology of two-dimensional wet foams with deformable bubbles. Phys. Rev. E 90, 032307 (2014).   
37. Mkrtchyan, A., Åström, J. & Karttunen, M. A new model for cell division and migration with spontaneous topology changes. Soft Matter 10, 4332–4339 (2014).   
38. Tanaka, S., Sichau, D. & Iber, D. LBIBCell: a cell-based simulation environment for morphogenetic problems. Bioinformatics 31, 2340–2347 (2015).   
39. Boromand, A., Signoriello, A., Ye, F., O’Hern, C. S. & Shattuck, M. D. Jamming of deformable polygons. Phys. Rev. Lett. 121, 248003 (2018).

40. Kim, S., Pochitalof, M., Stooke-Vaughan, G. & Campàs, O. Embryonic tissues as active foams. Nat. Phys. 17, 859–866 (2021).   
41. Brown, P. J., Green, G. E. F., Binder, B. J. & Osborne, J. M. A rigid body framework for multi-cellular modelling. Nat. Comput. Sci. 1, 754–766 (2021).   
42. Conradin, R., Coreixas, C., Latt, J. & Chopard, B. PalaCell2D: a framework for detailed tissue morphogenesis. J. Comput. Sci. 53, 101353 (2021).   
43. Vetter, R., Runser, S. V. M. & Iber, D. PolyHoop: soft particle and tissue dynamics with topological transitions. Comput. Phys. Commun. 299, 109128 (2024).   
44. Da, F., Barry, C. & Grinspun, E. Multimaterial mesh-based surface tracking. ACM Trans. Graphics 33, 112 (2014).   
45. Van Liedekerke, P. et al. A quantitative high-resolution computational mechanics cell model for growing and regenerating tissues. Biomech. Model. Mechanobiol. 19, 189–220 (2020).   
46. Wang, D. et al. The structural, vibrational, and mechanical properties of jammed packings of deformable particles in three dimensions. Soft Matter 17, 9901–9915 (2021).   
47. Torres-Sánchez, A., Kerr Winter, M. & Salbreux, G. Interacting Active Surfaces: a model for three-dimensional cell aggregates. PLoS Comput. Biol. 18, e1010762 (2022).   
48. Liu, S., Lemaire, P., Munro, E. & Mani, M. A mechanical atlas for Ascidian gastrulation. Preprint at bioRxiv https://doi.org/ 10.1101/2022.11.05.515310 (2023).   
49. Brakke, K. A. The surface evolver. Exp. Math. 2, 141–165 (1992).   
50. Madhikar, P., Åström, J., Westerholm, J. & Karttunen, M. CellSim3D: GPU accelerated software for simulations of cellular growth and division in three dimensions. Comput. Phys. Commun. 232, 206–213 (2018).   
51. Okuda, H. & Hiraiwa, T. Modelling contractile ring formation and division to daughter cells for simulating proliferative multicellular dynamics. Eur Phys. J. E 46, 56 (2023).   
52. Cuvelier, M. et al. Stability of asymmetric cell division: a deformable cell model of cytokinesis applied to C. elegans. Biophys. J. 122, 1858–1867 (2023).   
53. Odenthal, T. et al. Analysis of initial cell spreading using mechanistic contact formulations for a deformable cell model. PLoS Comput. Biol. 9, e1003267 (2013).   
54. Maître, J.-L. et al. Asymmetric division of contractile domains couples cell positioning and fate specification. Nature 536, 344–348 (2016).   
55. Helfrich, W. Elastic properties of lipid bilayers: theory and possible experiments. Z. Naturforsch. C 28, 693–703 (1973).   
56. Nance, J. Getting to know your neighbor: cell polarization in early embryos. J. Cell Biol. 206, 823–832 (2014).   
57. Martin-Belmonte, F. & Perez-Moreno, M. Epithelial cell polarity, stem cells and cancer. Nat. Rev. Cancer 12, 23–38 (2012).   
58. Hoshen, J. & Kopelman, R. Percolation and cluster distribution. I. Cluster multiple labeling technique and critical concentration algorithm. Phys. Rev. B 14, 3438–3445 (1976).   
59. Carsen, S., Wang, T., Michalis, M. & Pachitariu, M. Cellpose: a generalist algorithm for cellular segmentation. Nat. Methods 18, 100–106 (2021).   
60. Marieb, E. N. Human Anatomy & Physiology 3rd edn, Ch. 4 (Benjamin/Cummings, 1995).   
61. Lecuit, T. & Lenne, P.-F. Cell surface mechanics and the control of cell shape, tissue patterns and morphogenesis. Nat. Rev. Mol. Cell Biol. 8, 633–644 (2007).   
62. Käfer, J., Hayashi, T., Maréeand, A. F. M., Carthew, R. W. & Graner, F. Cell adhesion and cortex contractility determine cell patterning in the Drosophila retina. Proc. Natl Acad. Sci. USA 104, 18549–18554 (2007).

63. Micalizzi, D. S., Farabaugh, S. M. & Ford, H. L. Epithelial– mesenchymal transition in cancer: parallels between normal development and tumor progression. J. Mammary Gland Biol. Neoplasia 15, 117–134 (2010).   
64. Gómez, H. F., Dumond, M. S., Hodel, L., Vetter, R. & Iber, D. 3D cell neighbour dynamics in growing pseudostratified epithelia. eLife 10, e68135 (2021).   
65. Strzyz, P. J., Matejcic, M. & Norden, C. Heterogeneity, cell biology and tissue mechanics of pseudostratified epithelia: coordination of cell divisions and growth in tightly packed tissues. Int. Rev. Cell Mol. Biol. 325, 89–118 (2016).   
66. Iber, D. & Vetter, R. Relationship between epithelial organization and morphogen interpretation. Curr. Opin. Genet. Dev. 75, 101916 (2022).   
67. Spear, P. C. & Erickson, C. A. Interkinetic nuclear migration: a mysterious process in search of a function. Dev. Growth Difer. 54, 306–316 (2012).   
68. Smutny, M. et al. Friction forces position the neural anlage. Nat. Cell Biol. 19, 306–317 (2017).   
69. Kim, S., Pochitalof, M., Stooke-Vaughan, G. & Campàs, O. Embryonic tissues as active foams. Nat. Phys. 17, 859–866 (2021).   
70. Kitware The VTK User’s Guide 11th edn, Section 19.3 (Kitware, 2010).   
71. Bowers, J., Wang, R., Wei, L. & Maletz, D. Parallel Poisson disk sampling with spectrum analysis on surfaces. ACM Trans. Graph. 29, 166 (2010).   
72. Bernardini, F., Mittleman, J., Rushmeier, H., Silva, C. & Taubin, G. The ball-pivoting algorithm for surface reconstruction. IEEE Trans. Vis. Comput. Graph. 5, 349–359 (1999).   
73. Digne, J. An analysis and implementation of a parallel ball pivoting algorithm. Image Process. Line 4, 149–168 (2014).   
74. Wardetzky, M., Bergou, M., Harmon, D., Zorin, D. & Grinspun, E. Discrete quadratic curvature energies. Comput. Aided Geom. Des. 24, 499–518 (2007).   
75. Runser, S. Raw data generated for the article: “SimuCell3D: 3D Simulation of Tissue Mechanics with Cell Polarization", Steve Runser, Roman Vetter, Dagmar Iber. Zenodo https://doi.org/ 10.5281/zenodo.10797576 (2024).   
76. Runser, S. Source code of SimuCell3D. Zenodo https://doi.org/ 10.5281/zenodo.10796908 (2024).   
77. Pertoft, H. & Torvard, L. C. Isopycnic Separation of Cells and Cell Organelles by Centrifugation in Modified Colloidal Silica Gradients (Springer, 1977).   
78. Tinevez, J.-Y. et al. Role of cortical tension in bleb growth. Proc. Natl Acad. Sci. USA 106, 18581–18586 (2009).   
79. Petrie, R. J. & Koo, H. Direct measurement of intracellular pressure. Curr. Protoc. Cell Biol. 63, 12.9.1–12.9.9 (2014).   
80. Stewart, M. P. et al. Hydrostatic pressure and the actomyosin cortex drive mitotic cell rounding. Nature 469, 1476–4687 (2011).   
81. Fischer-Friedrich, E., Hyman, A. A., Jülicher, F., Müller, D. J. & Helenius, J. Quantification of surface tension and internal pressure generated by single mitotic cells. Sci. Rep. 4, 6213 (2014).   
82. Nandakumar, V., Kelbauskas, L., Johnson, R. & Meldrum, D. Quantitative characterization of pre-neoplastic progression using single cell computed tomography and 3D karyometry. Cytometry A 79, 25–34 (2011).   
83. Kaneko, H. et al. The presence of G1 and G2 populations in normal epithelium of rat urinary bladder. Basic Appl. Histochem. 28, 41–57 (1984).   
84. Renato, B. The Biology of Cell Reproduction (Harvard Univ. Press, 1985).

85. Chugh, P. et al. Actin cortex architecture regulates cell surface tension. Nat. Cell Biol. 19, 689–697 (2017).   
86. Maître, J.-L., Niwayama, R., Turlier, H. & Nédélec, F. Pulsatile cell-autonomous contractility drives compaction in the mouse embryo. Nat. Cell Biol. 17, 849–855 (2015).   
87. Zhelev, D. V., Needham, D. & Hochmuth, R. M. Role of the membrane cortex in neutrophil deformation in small pipets. Proc. Natl Acad. Sci. USA 67, 696–705 (1994).

# Acknowledgements

We thank F. Lampart for providing the prostate organoid images presented in Fig. 2f–h. This work was partially funded by SNF Sinergia grant CRSII5\_170930.

# Author contributions

Concept: R.V., D.I. Model and algorithm development: S.R., R.V. Implementation: S.R. Numerical simulations: S.R. Figures: S.R. Writing: S.R., R.V., D.I.

# Funding

Open access funding provided by Swiss Federal Institute of Technology Zurich.

# Competing interests

The authors declare no competing interests.

# Additional information

Supplementary information The online version contains supplementary material available at https://doi.org/10.1038/s43588-024-00620-9.

Correspondence and requests for materials should be addressed to Dagmar Iber.

Peer review information Nature Computational Science thanks James Osborne, Paul Van Liedekerke and the other, anonymous, reviewer(s) for their contribution to the peer review of this work. Primary Handling Editor: Fernando Chirigati, in collaboration with the Nature Computational Science team. Peer reviewer reports are available.

Reprints and permissions information is available at www.nature.com/reprints.

Publisher’s note Springer Nature remains neutral with regard to jurisdictional claims in published maps and institutional afiliations.

Open Access This article is licensed under a Creative Commons Attribution 4.0 International License, which permits use, sharing, adaptation, distribution and reproduction in any medium or format, as long as you give appropriate credit to the original author(s) and the source, provide a link to the Creative Commons licence, and indicate if changes were made. The images or other third party material in this article are included in the article’s Creative Commons licence, unless indicated otherwise in a credit line to the material. If material is not included in the article’s Creative Commons licence and your intended use is not permitted by statutory regulation or exceeds the permitted use, you will need to obtain permission directly from the copyright holder. To view a copy of this licence, visit http://creativecommons. org/licenses/by/4.0/.

© The Author(s) 2024, corrected publication 2024

# Reporting Summary

NaturePortfolioishstmprovetheeproducibitftheorkthatwepublisisformproidesstructurefosisteandtraspaenc inreporting.Forfurtherinformationon NaturePortfoliopolicies,seeour EditorialPoliciesandtheEditorialPolicyChecklist.

# Statistics

Foralltatisticallyfiattflowingitmsepreentintiurelegendtablged,intextesctio

n/a| Confirmed

区Theexactsample size (n)foreach experimentalgroup/condition,given asadiscrete number andunit of measurement   
□区Astatement onwhethermeasurements weretaken fromdistinctsamples orwhetherthesamesamplewas measuredrepeatedly   
区

A description of allcovariates tested

Adescription ofany assumptions orcorrectins,such as tests of normalityandadjustment formultiple comparisons

Afulldescriptioofthetatisticalparametersiudingcentraltendency(gmeans)ootherbasicestimates (egegressiocoficnt) At

区

For Bayesian analysis,information on the choice of priors and Markov chain Monte Carlo settings

区Forhierarchicalandcomplexdesigns,identificationof theappropriate levelfortestsandfullreportingof outcomes

区 Estimates of effect sizes (e.g. Cohen's d, Pearson’'s ),，indicating how they were calculated

# Software and code

Policy information about availability of computer code

Data collection Thecodeofourprogramispubliclyavailableunderthe3-clausesBDcenseintefolowingGitrepository:tps:/git.bseethzchiber/ Publications/24\_runser\_simucelldThepyhonscriptsusedtocollctesimulatonresultscanbefreelyacesdinthefolloing OpenBis repository: https://u.ethz.ch/7Taih

Data analysis Thepythonscriptsusedtoanalyzethe simulationresultscanalsobefreelyaccessedinthefollowing OpenBisrepository https:// u.ethz.ch/7Taih

# Data

Policy information about availability of data

Allmanuscriptsmustincludeadataavailabitystatement.Thisstatementshouldprovidethefollwinginformation,whereaplicable:

- Accession codes,unique identifiers,or web links for publicly available datasets   
- A description of any restrictions on data availability   
- For clinical datasets or third party data,please ensure that the statement adheres to our policy

Thedatasets generatedin this studyarepubliclyavailable in the folowing OpenBis repository: https://u.ethz.ch/7Taih

Policy information about studies involving human research participants and Sex and Genderin Research.

Reporting on sex and gender

Population characteristics N/A

Recruitment N/A

Ethics oversight N/A

# Field-specific reporting

Pleaseselectheonebelowthatisthebestfitforyourresearch.Ifyouarenotsurereadtheappropriatesectionsbeforemaingyourlection.

区Life sciences

Behavioural & social sciences

Ecological,evolutionary& environmental sciences

Forareference copy of the document with allsections,see nature.com/documents/nr-reporting-summary-flat.pdf

# Life sciences study design

<table><tr><td>Sample size</td><td>Sample sizes were not predetermined using any statistical method. The number of cells simulated in Figures 3 and 4 was deemed sufficient, as continuous morphological changes in their shapes, as well as in tissue architecture, were observable when varying the cellular parameters (Fig. 3e-f and Fig. 4d-g).</td></tr><tr><td>Data exclusions</td><td>No data was excluded from the analyses.</td></tr><tr><td>Replication</td><td>The simulations presented in this study are deterministic in nature. They are therefore fully reproducible and do not need to be replicated.</td></tr><tr><td>Randomization</td><td>Randomization is not relevant to this study since the simulations presented are deterministic in nature.</td></tr><tr><td>Blinding</td><td>Blinding is not relevant to this study since the simulations presented are deterministic in nature.</td></tr></table>

# Reporting for specific materials, systems and methods

Werequirefitatealriatdsa

Materials & experimental systems 

<table><tr><td>n/a</td><td>Involved in the study</td></tr><tr><td>☒</td><td>Antibodies</td></tr><tr><td>☒</td><td>Eukaryotic cell lines</td></tr><tr><td>☒</td><td>Palaeontology and archaeology</td></tr><tr><td>☒</td><td>Animals and other organisms</td></tr><tr><td>☒</td><td>Clinical data</td></tr><tr><td>☒</td><td>Dual use research of concern</td></tr></table>

Methods 

<table><tr><td>n/a</td><td>Involved in the study</td></tr><tr><td>☒</td><td>☐ ChIP-seq</td></tr><tr><td>☒</td><td>☐ Flow cytometry</td></tr><tr><td>☒</td><td>☐ MRI-based neuroimaging</td></tr></table>

# SimuCell3D: three-dimensional simulation of tissue mechanics with cell polarization

In the format provided by the authors and unedited

# List of Figures

Supplementary Figure 1 Initial surface triangulation . . 2

Supplementary Figure 2 Local mesh adaptation 2

Supplementary Figure 3 Spring-based contact model forces . 3

Supplementary Figure 4 Validation of the spring-based contact model in mechanical equilibrium . . 3

Supplementary Figure 5 Validation of the coupling-based contact model in mechanical equilibrium . . . . 4

Supplementary Figure 6 Parallel computational performance . . 5

a   
![](Jk2Mb6Ry4S_SimuCell3D组织力学_assets/images/a408b957ddaf194dc65be9b681c69a0051e69c7522e04c70e71e931240f7db03.jpg)

<details>
<summary>natural_image</summary>

Simple 3D gray cube illustration with no text or symbols
</details>

Initial geometry

b   
![](Jk2Mb6Ry4S_SimuCell3D组织力学_assets/images/0a9acfd9ee85b83e6383568c1e6bdb15a03802db4e11e96e4781754371141738.jpg)

<details>
<summary>natural_image</summary>

3D wireframe cube with scattered dots inside, no text or symbols present
</details>

Poisson Disc Sampling

c   
![](Jk2Mb6Ry4S_SimuCell3D组织力学_assets/images/129332c59e27f26f133809c8512b35b87208a36d8a6988ec5125e050a5d1b520.jpg)

<details>
<summary>natural_image</summary>

3D rendered sphere resting on a cube with grid overlay, no text or symbols present
</details>

Surface reconstruction with the Ball Pivoting Algorithm T   
d   
![](Jk2Mb6Ry4S_SimuCell3D组织力学_assets/images/cfd4d67a4f913e0038b2b58122ec717fa7d7f82d85ce46d5fd05062a9372360a.jpg)

<details>
<summary>natural_image</summary>

3D wireframe cube with triangular facets, no text or symbols visible
</details>

Triangulated geometry   
Supplementary Figure 1: Initial surface triangulation. A, Arbitrary surface meshes can be loaded by the program, here a cube for illustration. B, Point samples are generated on the surface with the Poisson disc sampling method, with a minimal distance of $l _ { \mathrm { m i n } }$ between points. C, The Poisson disc point cloud is then used by the Ball Pivoting Algorithm to reconstruct the surface of the initial geometry with triangles. The Ball Pivoting Algorithm connects triplets of points into triangular faces if a ball (red sphere) can simultaneously touch them without containing any other point. D, The procedure is terminated when the reconstructed surface is watertight, and the resulting triangulation(s) are used by SimuCell3D to simulate cellular components.

a   
Edge splitting   
![](Jk2Mb6Ry4S_SimuCell3D组织力学_assets/images/ee0834d26223fbaafeaffe1e2befb8db4ad2550658e5db30d9c7f252b17f8a7e.jpg)

<details>
<summary>natural_image</summary>

Geometric diagram showing a polyhedron with internal lines and a red horizontal line (no text or symbols)
</details>

![](Jk2Mb6Ry4S_SimuCell3D组织力学_assets/images/3cf9b64329065106423a9ac2c547c92f44ec31b1c4083c2970371bd28cd77789.jpg)

b   
Edge merger   
![](Jk2Mb6Ry4S_SimuCell3D组织力学_assets/images/e07be72f1483102513372c47109f3d9955625fac67ec161e688fc1df4dcc840e.jpg)

<details>
<summary>natural_image</summary>

Geometric diagram with green and red lines forming a star-like pattern within a triangular grid (no text or symbols)
</details>

![](Jk2Mb6Ry4S_SimuCell3D组织力学_assets/images/8491dec0aa4f04066ec3a7aef2c51329accb3f984576b721b060d2a4e574a4e1.jpg)

c   
Edge swap   
![](Jk2Mb6Ry4S_SimuCell3D组织力学_assets/images/89be2387c147132e0550eeb8cc505753cac3a0c48fe6ce65e47fd19e7e1d4656.jpg)

<details>
<summary>natural_image</summary>

Geometric diagram with a red triangle and shaded region, no text or symbols present
</details>

![](Jk2Mb6Ry4S_SimuCell3D组织力学_assets/images/00d11f15e588cae23504060eaf46359f9e5518a7f4f36aa3364862f3dbe952ea.jpg)

![](Jk2Mb6Ry4S_SimuCell3D组织力学_assets/images/2b527417813e4023ccbd290b4aaed26e0dec282899e5938a1f95314fff7efa7f.jpg)

<details>
<summary>natural_image</summary>

Geometric diagram showing a diamond shape inscribed within a polygonal grid, with no text or symbols present.
</details>

![](Jk2Mb6Ry4S_SimuCell3D组织力学_assets/images/6fae1df0d768330cdacb63704218821f86f804d59b9903ad3d0a491726cb8531.jpg)

<details>
<summary>natural_image</summary>

Geometric pattern with black and green lines forming a star-like design (no text or symbols)
</details>

![](Jk2Mb6Ry4S_SimuCell3D组织力学_assets/images/2ac341a911760235ce630e45474787a7c2be2d30e27535fa5e124b83594e879c.jpg)

<details>
<summary>natural_image</summary>

Geometric diagram with a green diagonal line and shaded triangle, no text or symbols present
</details>

Supplementary Figure 2: Local mesh adaptation. A, Edges whose length exceeds ${ l } _ { \mathrm { m a x } }$ (red) are split into two, generating two new triangles and a new node in the middle. B, Edges whose length subceeds $l _ { \mathrm { m i n } }$ (red) are collapsed into a node at the center, removing the two triangles sharing it. C, Triangles with high isoperimetric ratio (red) are prevented by swapping the orientation of their longest edge.

![](Jk2Mb6Ry4S_SimuCell3D组织力学_assets/images/c9d2b19e7a111f700e3b312b75af55e847573002e3846e94587b628bf69c6e55.jpg)

Supplementary Figure 3: Spring-based contact model forces. A, Schematic of two interpenetrating cells (negative distance $d _ { a b }$ , left) and two adhering cells (positive distance $d _ { a b } , \mathrm { r i g h t } )$ . B, A bilinear adhesive traction-separation law governs the contact mechanics between adjacent cells, symmetrically separated into a hardening regime (green) in which adhesion forces increase linearly with separation, and a softening regime (blue) in which forces decrease linearly, to ensure force continuity at a separation of $d _ { a b } = c$ . At negative separations, repulsive forces proportional to the penetration depth are exchanged (red). The slopes ω and ζ control the rigidity of the intercellular mechanical interactions.   
![](Jk2Mb6Ry4S_SimuCell3D组织力学_assets/images/1c679de5a1eddf75cc2449b005ef58a56a0839b4b19762ac2b04db553ca4924e.jpg)

<details>
<summary>line</summary>

| Mesh minimum edge length l_min [μm] | Contact angle α [deg] |
| ------------------------------------ | --------------------- |
| 0.6                                  | ~30                   |
| 0.9                                  | ~30                   |
| 1.2                                  | ~30                   |
| 1.5                                  | ~25                   |
| 1.8                                  | ~20                   |
</details>

![](Jk2Mb6Ry4S_SimuCell3D组织力学_assets/images/06e491eece86c3dcc632a7a0c745e806c2e10643dc28e890420ef019e1554186.jpg)

<details>
<summary>scatter</summary>

| Average number of nodes per cell ⟨Nₙ⟩ | α₀ − α [deg] |
| ------------------------------------- | ------------ |
| 200                                   | 10           |
| 500                                   | 5            |
| 1000                                  | 2            |
| 2000                                  | 1            |
| 5000                                  | 0.5          |
</details>

Supplementary Figure 4: Validation of the spring-based contact model in mechanical equilibrium. A, Contact angle α between a pair of cells as a function of the minimum mesh edge length $l _ { \mathrm { m i n } } . \ l _ { \mathrm { m i n } } = 0 . 6$ µm corresponds to a high mesh resolution with ≈ 3, 500 nodes per cell, while $l _ { \mathrm { m i n } } = 1 . 8$ µm corresponds to a low mesh resolution with ≈ 350 nodes per cell. The apical surface tensions of the cells $( \gamma _ { \mathrm { a } , 1 }$ and $\gamma _ { \mathrm { a , 2 } } )$ as well as their lateral surface tensions $( \gamma _ { 1 , 1 }$ and $\gamma _ { 1 , 2 } )$ were set to $2 . 5 \times 1 0 ^ { - 4 } ~ \mathrm { N / m }$ in all simulations. The adhesion strength between the cells was kept constant at $\omega = 2 . 5 \times 1 0 ^ { 8 }$ $\mathrm { P a } / \mathrm { m }$ in all simulations. The black dotted line represents the contact angle value $\alpha _ { 0 }$ obtained in a simulation with high mesh resolution $( l _ { \mathrm { m i n } } = 0 . 6 \mu \mathrm { m } )$ , while the grey dotted lines correspond to $\mathrm { ~ a ~ } \pm 1 0 \%$ variation of this value. B, Difference in contact angle with respect to a high resolution simulation as a function of the average number of nodes per cell. The dark blue dashed line shows the relationship $\alpha = \alpha _ { 0 } - a / \langle N _ { \mathrm { n } } \rangle$ with fitted coefficient $a = 3 . 6 \times 1 0 ^ { 3 }$ deg.

![](Jk2Mb6Ry4S_SimuCell3D组织力学_assets/images/df7166b751a9f613ff5704fce9f1bf1fc6dc6ba4ababf70d76153dd73483bdb6.jpg)

<details>
<summary>line</summary>

| α = γ₁,₂ / γₐ,₂ | Contact angle θ [deg] |
| --------------- | --------------------- |
| 0.00            | 90                    |
| 0.25            | ~60                   |
| 0.50            | ~30                   |
| 0.75            | ~10                   |
| 1.00            | 0                     |
</details>

![](Jk2Mb6Ry4S_SimuCell3D组织力学_assets/images/af1b41f2e81afcbaacaa118c1c5572aae2b4f29914556296836b5b778350a250.jpg)

<details>
<summary>line</summary>

| α = γ₁,₂ / γₐ,₂ | Contact angle θ [deg] (λ = 0.1) | Contact angle θ [deg] (λ = 0.2) | Contact angle θ [deg] (λ = 0.3) | Contact angle θ [deg] (λ = 0.4) | Contact angle θ [deg] (λ = 0.5) |
| --------------- | ------------------------------- | ------------------------------- | ------------------------------- | ------------------------------- | ------------------------------- |
| 0.00            | 90                              | 90                              | 90                              | 90                              | 90                              |
| 0.25            | ~85                             | ~85                             | ~85                             | ~85                             | ~85                             |
| 0.50            | ~70                             | ~70                             | ~70                             | ~70                             | ~70                             |
| 0.75            | ~50                             | ~50                             | ~50                             | ~50                             | ~50                             |
| 1.00            | 0                               | 0                               | 0                               | 0                               | 0                               |
</details>

![](Jk2Mb6Ry4S_SimuCell3D组织力学_assets/images/078b8275883c9c543f7bdb721d703a3f19c52083bccec04db47a20ba87574342.jpg)

<details>
<summary>scatter</summary>

| Cell   | η = (γ₁,₂ + γ₁,₃) / (γ₁,₁ + γ₁,₂) | Contact angle φ [deg] |
|--------|----------------------------------|------------------------|
| Cell 1 | ~0.75                            | ~145                   |
| Cell 1 | ~1.00                            | ~100                   |
| Cell 1 | ~1.25                            | ~85                    |
| Cell 1 | ~1.50                            | ~75                    |
| Cell 2 | ~0.75                            | ~145                   |
| Cell 2 | ~1.00                            | ~100                   |
| Cell 2 | ~1.25                            | ~85                    |
| Cell 2 | ~1.50                            | ~75                    |
| Cell 3 | ~0.75                            | ~145                   |
| Cell 3 | ~1.00                            | ~100                   |
| Cell 3 | ~1.25                            | ~85                    |
| Cell 3 | ~1.50                            | ~75                    |
</details>

![](Jk2Mb6Ry4S_SimuCell3D组织力学_assets/images/05dc528344a60cc7a976dec10186c2768f25d3664eee54a03878936d392fff1d.jpg)

<details>
<summary>line</summary>

| δ = γₐ,₁ / γₐ,₂ | Frac. of cell 1 surface internalized (α=0.25) | Frac. of cell 1 surface internalized (α=0.5) | Frac. of cell 1 surface internalized (α=0.75) |
| --------------- | ----------------------------------------------- | ----------------------------------------------- | ----------------------------------------------- |
| 1.00            | ~0.25                                           | ~0.20                                           | ~0.10                                           |
| 1.25            | ~0.35                                           | ~0.25                                           | ~0.15                                           |
| 1.50            | ~0.60                                           | ~0.40                                           | ~0.20                                           |
| 1.75            | ~0.85                                           | ~0.60                                           | ~0.25                                           |
| 2.00            | ~1.00                                           | ~0.80                                           | ~0.30                                           |
</details>

Supplementary Figure 5: Validation of the coupling-based contact model in mechanical equilibrium. A, Contact angle θ between a pair of cells as a function of their lateral $( \gamma _ { 1 , i } )$ to apical $( \gamma _ { \mathrm { a } , i } )$ surface tension ratio, and mesh resolution $( l _ { \mathrm { { m i n } } } ) . \gamma _ { \mathrm { { a , 1 } } } = \gamma _ { \mathrm { { a , 2 } } } $ , and $\gamma _ { 1 , 1 } = \gamma _ { 1 , 2 }$ . The theoretical black curve is given by the Young–Dupr´e equation as cos $\theta = \gamma _ { 1 , 2 } / \gamma _ { \mathrm { a , 2 } }$ . B, Contact angle θ between a pair of cells as a function of their lateral to apical surface tension ratio. $\gamma _ { \mathrm { a , 1 } } = \gamma _ { \mathrm { a , 2 } } .$ but $\gamma _ { 1 , 1 } \neq \gamma _ { 1 , 2 } .$ . λ is the deviation factor of each cell lateral surface tension from the mean lateral surface tension $i . e . \ \gamma _ { 1 , 1 } = \overline { { \gamma } } ( 1 - \lambda )$ , and $\gamma _ { 1 , 2 } = \overline { { \gamma } } ( 1 + \lambda )$ where $\overline { { \gamma } } = ( \gamma _ { 1 , 1 } + \gamma _ { 1 , 2 } ) / 2$ . The theoretical black curve is given by cos $\theta = \overline { { \gamma } } / \gamma _ { \mathrm { a , 2 } } . \mathrm { ~ C ~ }$ Contact angle ϕ at a tricellular junction as a function of the ratio $\eta = ( \gamma _ { 1 , 2 } + \gamma _ { 1 , 3 } ) / ( \gamma _ { 1 , 1 } + \gamma _ { 1 , 2 } ) . \ \gamma _ { \mathrm { a , 1 } } = \gamma _ { \mathrm { a , 2 } } = \gamma _ { \mathrm { a , 3 } } .$ , and $\gamma _ { 1 , 1 } \neq \gamma _ { 1 , 2 } = \gamma _ { 1 , 3 }$ . The theoretical line is obtained from the Young–Dupr´e law and follows $\cos ( \phi / 2 ) = \eta / 2$ . D, Proportion of cell 1 surface area internalized as a function of the apical surface tension ratio $\delta = \gamma _ { \mathrm { a , 1 } } / \gamma _ { \mathrm { a , 2 } } . \ \gamma _ { \mathrm { l , 1 } } = \gamma _ { \mathrm { l , 2 } }$ , and $\alpha = \gamma _ { 1 , 2 } / \gamma _ { \mathrm { a , 2 } }$ The theoretical curves were calculated based on the Lagrangian approach presented in [1].

![](Jk2Mb6Ry4S_SimuCell3D组织力学_assets/images/378f9a362092e5aa3529aaeb490eda33de3da9b3abeddd259313ec9489210590.jpg)

<details>
<summary>scatter</summary>

| Number of threads T | Spring model | Coupling model |
| ------------------- | ------------ | -------------- |
| 1                   | 2.0          | 3.5            |
| 2                   | 1.6          | 2.3            |
| 3                   | 1.3          | 1.8            |
| 4                   | 1.2          | 1.6            |
| 5                   | 1.1          | 1.5            |
| 6                   | 1.1          | 1.5            |
| 7                   | 1.0          | 1.4            |
</details>

![](Jk2Mb6Ry4S_SimuCell3D组织力学_assets/images/e86219d65aab02ebac6de5df59b56d57ef05fd6e36710cb870645413db97f6ba.jpg)

<details>
<summary>line</summary>

| Number of threads T | Amdahl's law P = 53% | Amdahl's law P = 66% |
| ------------------- | -------------------- | -------------------- |
| 1                   | 1.0                  | 1.0                  |
| 2                   | 1.3                  | 1.5                  |
| 3                   | 1.5                  | 1.8                  |
| 4                   | 1.6                  | 2.0                  |
| 5                   | 1.7                  | 2.2                  |
| 6                   | 1.8                  | 2.3                  |
| 7                   | 1.9                  | 2.4                  |
</details>

![](Jk2Mb6Ry4S_SimuCell3D组织力学_assets/images/574791cb7934af79773fa73e614a2864ff2a25950ffbe458151b166f779aaf12.jpg)

<details>
<summary>scatter</summary>

| Number of threads T | Time per iteration per node (s) ×10⁻⁵ |
| ------------------- | -------------------------------------- |
| 1                   | 1.3                                    |
| 2                   | 0.8                                    |
| 3                   | 0.65                                   |
| 4                   | 0.6                                    |
| 5                   | 0.55                                   |
| 6                   | 0.5                                    |
| 7                   | 0.45                                   |
</details>

Supplementary Figure 6: Parallel computational performance. A, Computation time required to simulate the development of a tissue from 1 to 500 cells with respect to the number of threads (T ). The computation time was recorded for both contact models available in SimuCell3D. The average number of nodes per cell in these simulations was approximately 700. B Speedup S as a function of the number of threads. Amdahl’s law: $S = 1 / ( 1 - P + P / T )$ , where P is the parallel fraction. C, Computation time per iteration per number of nodes as a function of the number of threads (T ) for both contact models available in SimuCell3D. All simulations were performed on an Intel Xeon W-2125 processor (8 cores, 4.5 GHz).

# References

[1] J. Maˆıtre et al., Nature 536, 344 (2016).