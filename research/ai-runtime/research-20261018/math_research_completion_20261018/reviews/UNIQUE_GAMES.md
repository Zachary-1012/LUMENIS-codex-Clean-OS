# Family 102: Unique Games manuscript, full-text research completion

## Decision and version
The previously missing original manuscript is now accessible through the official GitHub connector at the original pin. All 58 PDF pages, including Appendix A and references, were read as extracted full text. Two truncated extraction outputs were repaired by rereading the affected folding/decoder passages. Nine key formula pages were visually checked: 10, 11, 12, 28, 34, 38, 44, 50, 53. This is manuscript review, not independent certification of all external theorems or a Lean replay.

[Official fixed PDF](https://github.com/openai/math/blob/1581d4cbdd69a0faf34b2089614fe2a814316a6a/preprints/The-Unique-Games-Theorem-September-23-2026/paper.pdf): 801214 bytes; SHA256 `04d0290a9cb7ee815060f82cf556cee893d32b5255613160ca8b8d02a5fe1289`; Git blob `aa63747a898023b70df64f3988fe7ad465c84c68`.

The main claim is a deterministic polynomial reduction from 3SAT to nonempty unweighted simple bipartite translation games over F2^s, with completeness at least 1-epsilon and soundness at most delta for each independently fixed epsilon,delta in (0,1/2). Alphabet, degree of the polynomial and very large constants depend on those errors. This is an inapproximability construction. It is not a fast Unique Games optimizer and supplies no automatic advantage to a business ranking system.

## Main argument, contracts and unresolved external dependencies
### 1. Latent nonlinear gadget, Sections 2–3
For prescribed p*>0 a rank threshold r* is fixed **before** the later alphabet dimension ell. The construction supplies V containing K=F2^ell, an equivariant map C(x+k)=C(x)+k and rational noise. Nonlinear change probability is <=p*, while each linear observation of rank >=r* detects the noise with probability >=1/8.

The quadratic block uses B=F_{2^d}^3, Q(x)=(x2*x3,x1*x3,x1*x2). For a field line A=Fv, D_A is the orthogonal plane and U_A consists of (a,Q(a)+w). U_A is a binary subspace of dimension 3d; these spaces span the ambient product. Theta=1/(q²+q+1). The kernel condition is A=Fz and z·g(z)=sqrt(z1*z2*z3). The trace identity is Tr(t²c)=Tr(t sqrt(c)); this is a characteristic-two square root, not a real radical.

Generic rank-r binary subspaces have no two proportional nonzero vectors and at most 3r aligned vectors **for every** linear g. Harmonic rank loss is <=3theta on generic subspaces, while arbitrary subspaces use 2^r theta. The genericity argument uses independence of square-root monomials over the rational function field L. It does not assert their independence over its algebraic closure. Annihilators over L force all degree-three evaluation vectors into the column span; closure under multiplication then contradicts dimension >3r. Squared minors have degree <=6r+3, allowing a finite-field polynomial-zero estimate.

The recursive gadget includes every pair (field line, isomorphism), not one sampled child as the entire map. Randomness selects the noisy branch. Conditional aggregate uniformity is needed for nonlinear change p_t=(1-q^-3)(1-theta)^t. Linear lifts can depend on earlier coordinates; they cannot depend on future choices. Uniformity over every g in genericity is what permits that adaptation. Expected harmonic rank loss <=4theta leads to detection >=1/4 before embedding all injections into K; the latter gives >=3/16 and hence >=1/8. The effective construction enumerates large finite objects, with constants chosen before the input formula.

### 2. Outer parity game and folded tables, Section 4
The first external input is Håstad's weighted positive rational 3Lin gap. One hundred clones per variable and distinct selected positions produce a NO bound <=4/5. Ordinary equation-variable projection has left/right alphabet sizes 4/2 and value <=14/15 in NO instances. This intermediate projection is not a permutation.

The construction takes k-tuples with replacement and keeps local positions distinct even when equation IDs repeat. Actual homogeneous answers have first coordinate 1. Independent projections retain an equation or select one of its three variable positions, preserving the position tag. The third bit contains the parity intercept b_e*t0. A shared table key includes the exact induced affine map, including the intercept and retained support. Rank-one slope patterns (v,0), (0,v), (v,v) encode different selected variables. Removing the intercept or merging repeated IDs changes the construction.

Folding uses free constant-K translation orbits and restores answers by their recorded constant offset. Equality of restored answers yields translation permutations. Row advice is not an extra consistency test. Completeness loss is bounded by k*xi+p*/2.

### 3. Inverse shortcode and soundness, Section 5
The external Grassmann input is Khot–Minzer–Safra's expansion result (specified revision/theorem and effective bounds), not the missing UG theorem itself. Fiber acceptance, nonzero rank-one updates and the chart-to-Grassmann conversion yield a bounded row/column slice with agreement. Excluding zero updates and fixing ell relative to the slice rank are essential.

The low-rank Fourier mass argument sets eta=2^-r*/16, then chooses alpha,r_s,ell before k. Acceptance >=.99 bounds high-rank mass by .08 and yields a positive fraction of useful row advice. The erasure argument overwrites bad fibers with independent values once per matrix; a Hoeffding union bound over all slice/target descriptions yields good-row mass. Folding forces the witness affine coset to contain an actual answer with first coordinate 1. A random preimage is chosen from a short list, not from an arbitrary ambient linear space.

The padded-law comparison is **conditional on U, with projection choices averaged out**. It does not hold after fixing the projection. For n=|V|, the singleton pair law has density n at (0,0), n/3 on the other 3(n-1) supported pairs, zero elsewhere. Its chi-square divergence from uniform is (n-1)/3. Product mixture divergence is (1+(n-1)*beta²/3)^k-1. Choosing cube k and beta=k^-2/3 gives k*beta² ->0 while k*beta ->infinity. A uniform independent intercept absorbs all parity shifts.

Projection can collapse a witness slice. Thus the proof first transfers a joint weighted agreement-minus-mass quantity under total variation, then conditions on shared advice. Assuming every projected slice is nonempty would be a false shortcut. The O-side decoder sees only its own question and shared advice. It Fourier-samples its own fiber with squared coefficient weights; it cannot see U's certificate or shortlist. The resulting positive gamma is fixed before k.

### 4. Clean-coordinate contradiction, Section 6
The second central external input is alphabet-independent Dinur–Steurer repetition: val<=1-g implies repeated value <=(1-g²/16)^n. Conditional on row matrix A, combine the visible advice in W plus im(A). A clean coordinate is a singleton projection with zero advice slope, with probability beta*2^(-dimW-rankA).

Conditioning fixes A, the clean mask, the original O intercept, and only nonclean occurrence/projection/slopes. It explicitly excludes the witness, decoder output, agreement event and response randomness. Clean question pairs then remain independent ordinary equation-variable questions. Each prover reconstructs its own input without learning the other prover's equation or selected position. Repeated IDs remain independent local copies. The agreement bound is at most exp(-2^(-dimW-r_s)*k^(1/3)/3600), eventually contradicting the earlier fixed gamma.

### 5. Explicit unweighted simple bipartite output, Section 7
Largest-remainder rounding with Q>=h/tau bounds total variation by tau. Each constraint occurrence becomes a length-four path with fresh inner vertices. This preserves translations and gives exact value 1-(1-val)/4. Loops become four-cycles and parallel occurrences receive separate inner vertices; thus the result is simple bipartite rather than merely a multigraph.

The repetition count t is fixed first using alphabet-independent repetition, then p*/tau, latent rank, shortcode dimensions, latent data, cube k, and **last** parity error xi. The paper explicitly provides rational inequalities that can be checked by enumeration. The final product preserves simplicity and has translation alphabet F2^(ell*t). Polynomial time means polynomial for fixed target errors. Enumerating N_E^k tuples and the fixed gadgets is not a practical input-independent constant-time preprocessing guarantee.

## Consequences and their actual scope, Section 8
- Max-Cut above the specified semidefinite threshold and Vertex Cover below factor 2 are hardness consequences, not provided approximation solvers.
- Raghavendra-style statements require a fixed finite predicate language and a fixed strict SDP/OPT witness gap, with rational nonnegative weights and correct dummy-variable treatment. Rationalizing local laws must preserve the same variable universe and a sufficiently small total-variation error.
- Ordering CSPs use a single global order, not a fixed-domain assignment. The random-order baseline is rho=|Pi|/k!, with conditional-expectation derandomization available. MAS and betweenness special baselines do not generalize to arbitrary hard scheduling constraints.
- Cut statements distinguish nonuniform selected unit demands, weighted edges and search reductions. They do not certify the uniform all-pairs version. Kernel clustering requires centered PSD rational input and ordered pair sums including diagonal entries; normalization or excluding empty clusters changes the problem.

## Appendix A read in full: two substantive dependency chains
**A.1 strong-left/simple normalization.** Copy counts floor(2|X|w_x), local-weight rounding, distinct tags and h-sequences yield high-degree simple instances with strong-left completeness. The choices satisfy sqrt(2*zeta0)<u, confirmed visually on page 44. Conditioning on tag distinctness costs a factor above 3/4. Copies may choose labels depending on the whole sequence; the collision/soundness bound is designed to handle this. Naive independent original-copy labels would not suffice.

**A.2 ordering CSP transfer.** A finite local gap instance is smoothed to a rational positive-atom law with uniform marginals and common Gram data for all constraints. Small-mean collision bounds and vector-valued invariance require separate hypotheses. The same simplex-valued function is used across every local constraint; the constraint is selected once, then coordinates are independently sampled. The influence identity and tail bound are explicit. Page 50 confirms Lipschitz constant sqrt(kq) and error C_kq*sqrt(kq)*u^{lambda/(18 log(1/alpha))}. Rank-interval influences decode a single global right labeling. Conditioning on distinct neighbors loses at most binom(k,2)/h. Ties are refined by one random global order within each rank fiber, not independently per constraint. Parameters are fixed before the outer alphabet. Appendix external invariance/local-gap/repetition results were identified but their original papers were not independently reread in this phase.

## Source Owner and actual implementation boundary
Recovered product file `lumenis/shared/evaluation/openai_math_papers/unique_games_102.py` was read in full. `check_instance` admits at most 128 vertices, alphabet <=256, 4096 nonempty constraint occurrences, same alphabet on both sides and bijective images. It evaluates exactly one supplied labeling, preserving occurrence multiplicity, and explicitly excludes the hardness reduction/approximation theorem.

The final translation instances of this manuscript are representable only when they fit these finite limits, but no 3SAT reduction, latent gadget, table/folding construction, decoder, repetition or optimizer is implemented. Intermediate equation-variable projections do not fit the same-q bijection schema. The four companion hardness manuscripts retain their independent ordinary-projection or 2-to-1 source dependencies; they were never blocked by this PDF's absence. This new review does not overturn that earlier correction.

Owner: Shared Evaluation/openai_math_papers; original G160 research and G161 adoption, with G143/159/162 evidence/workflow obligations. Actual business use is to explain approximation boundaries and reject unsupported solver promises. It does not justify removing existing CP-SAT or heuristic scheduling tools, nor predict hardness of a particular small instance.

## Concrete next independent experiments, no execution authorized here
1. Exact finite-field GF(2^d) block and trace/kernel checks at tiny d; enumerate binary subspaces, verify U_A linearity/spanning and compare kernel criterion. These validate local algebra, not the asymptotic genericity theorem.
2. Tiny rational padded-law enumeration: density, chi-square identity, product mixture and TV; a negative control fixing the projection must expose why that conditioning is invalid.
3. Tiny affine table/folding serializer: retain intercept, position tags, repeated occurrences; verify constant-shift restoration and deliberate wrong-key collisions.
4. Weighted occurrence rounding and four-edge path transform: exhaust tiny labelings to check exact optimum relation and simplicity including loops/parallel occurrences. Keep tiny exhaustive OPT distinct from the paper's polynomial reduction.
5. Optional ordering baseline only if a real task is an unconstrained weighted fixed-arity ordering CSP: verify rho baseline against exhaustive small orders and exact conditional expectations. Hard availability/cost constraints generally invalidate that guarantee.
6. General reduction remains a separate major project: first independently verify the exact external theorem contracts/effective constants, then parameter feasibility/resource estimates. No claim of practical construction should precede those checks.

Open: full external dependency certification; general reduction implementation; formal main-theorem replay; practical constants; task-specific business advantage. Full-text coverage closes the missing-reading item only.
