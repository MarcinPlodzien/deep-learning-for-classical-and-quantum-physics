#!/usr/bin/env python3
"""Prepare the website sources from the lecture folders of the course.

Everything about the lectures lives in LECTURES below. Only the lectures whose
number is in READY are published; to publish a lecture, add its number to READY
and run ./build.sh. For each published lecture this script writes

* slides:    ./slides/lecture-NN.pdf (lectures with a deck), compressed for the web (Ghostscript, 150 dpi):
               "pdf"    decks are taken as they are;
               "odp"    decks are converted with LibreOffice from a temporary copy in
                        which the dates (title page text and date fields) are removed;
               "beamer" decks are compiled once more with an empty date, with all
                        output in a temporary folder;
* notebooks: ./notebooks/lecture-NN/<name>.ipynb, copied with their stored outputs,
             with a Quarto title, an "Open in Colab" badge, dates removed, and figure
             paths that work outside the course folder. Notebooks listed in
             LECTURES[n]["notebooks"] are used; if it is None, every
             Lab_*.ipynb in <folder>/Notebooks is taken, titled from its "# Lab NNN — ..."
             heading;
* pages:     ./lectures/lecture-NN.qmd (summary, slides, notebook list);
* menus:     ./_lectures.yml (navbar menu and sidebar, merged into _quarto.yml) and
             ./_lectures_table.md (the table of lectures on the start page).

The lecture folders are never modified.
"""
import os, re, glob, shutil, subprocess, tempfile, sys, zipfile
import nbformat
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
COURSE = os.path.dirname(HERE)
REPO = "MarcinPlodzien/deep-learning-for-classical-and-quantum-physics"

# lectures that are published
READY = {1, 2, 3, 4, 5, 6}

# Each lecture: deck (kind, path relative to the course folder; None = no slides on
# the site), optionally last_frame (publish the deck only up to the last page of the
# frame with this title), title,
# summary for the lecture page, a short note on the notebooks for the start page,
# and notebooks as (source relative to the course folder, web name, title, description);
# notebooks=None takes every Lab_*.ipynb of <folder>/Notebooks.
LECTURES = {
    1: dict(
        deck=("beamer", "Lecture_1/beamer/main.tex"),
        title="From Artificial Intelligence to Neural Networks",
        summary="Big goals of quantum physics that machine learning can serve. The approaches to artificial intelligence, the hierarchy of AI, machine learning and deep learning, and the step from algorithm-driven to data-driven programming, with features extracted by hand or learned automatically. The anatomy of a neural network as a non-linear parametrised function: without a non-linearity depth does nothing, ReLU pieces build any curve, a steep sigmoid becomes a step, and the universal approximation theorem. Regression and classification, and the literature of the course.",
        table_note="Labs 001–003d: Python, NumPy, PyTorch, JAX, trained networks, framework benchmark",
        notebooks=[
            ("Lecture_1/Notebooks/Lab_001_Python_Matplotlib_Pandas_warmup.ipynb", "lab-001-python-matplotlib-pandas", "Lab 001: Python, Matplotlib and Pandas", "A warm-up with the tools used in every later notebook."),
            ("Lecture_1/Notebooks/Lab_002_NumPy_basics.ipynb", "lab-002-numpy", "Lab 002: NumPy, thinking in arrays", "Vectorised computation instead of loops."),
            ("Lecture_1/Notebooks/Lab_003_PyTorch_basics.ipynb", "lab-003-pytorch", "Lab 003: PyTorch tensors, devices and layers", "The basic objects of PyTorch."),
            ("Lecture_1/Notebooks/Lab_003c_JAX_basics.ipynb", "lab-003c-jax", "Lab 003c: JAX, arrays, randomness, compilation, differentiation and vectorisation", "jit, grad and vmap, Flax NNX and Optax, and a Metropolis sampler checked against exact enumeration."),
            ("Lecture_1/Notebooks/Lab_003a_Trained_models_toolbox_PyTorch.ipynb", "lab-003a-trained-networks-pytorch", "Lab 003a: Working with trained networks in PyTorch", "Saving, inspecting, cutting, freezing and fine-tuning a trained CNN, and transfer learning with few labels."),
            ("Lecture_1/Notebooks/Lab_003b_Trained_models_toolbox_JAX.ipynb", "lab-003b-trained-networks-jax", "Lab 003b: Working with trained networks in JAX and Flax NNX", "The same toolbox in JAX, with a PyTorch–JAX cheat sheet."),
            ("Lecture_1/Notebooks/Lab_003d_Framework_benchmark.ipynb", "lab-003d-framework-benchmark", "Lab 003d: NumPy, JAX, PyTorch and Keras on the same tasks", "Speed, compilation cost and code of four tools on array operations, derivatives, Monte Carlo and training."),
            ("Lecture_1/Notebooks/Nonlinearity_and_universal_approximation.ipynb", "nonlinearity-and-universal-approximation", "Non-linear activations and universal approximation", "The figures of the lecture: depth without a non-linearity, ReLU pieces and sigmoid steps."),
        ],
    ),
    2: dict(
        deck=("beamer", "Lecture_2/beamer/main.tex"),
        title="Elements of Deep Learning",
        summary="Loss functions for regression and classification, the zoo of architectures, gradient descent with mini-batches, iterations and epochs, and what a well-trained network is. A neural network learns the probability distribution of its training data; the factors behind today's deep learning. The first example: MNIST digit classification as non-linear function fitting, with the categorical cross-entropy.",
        table_note="Labs 004–008: automatic differentiation, universal approximation, training",
        notebooks=[
            ("Lecture_2/Notebooks/Lab_004_Automatic_differentiation.ipynb", "lab-004-automatic-differentiation", "Lab 004: Automatic differentiation", "Derivatives computed by the machine, exactly."),
            ("Lecture_2/Notebooks/Lab_005_N_pendulum_SymPy_and_autodiff.ipynb", "lab-005-n-pendulum", "Lab 005: The N-link pendulum with SymPy and automatic differentiation", "Equations of motion obtained symbolically and by automatic differentiation."),
            ("Lecture_2/Notebooks/Lab_006_UAT_and_minimizers.ipynb", "lab-006-uat-and-minimisers", "Lab 006: Universal approximation and the choice of minimiser", "Fitting functions with networks, and the role of the optimiser."),
            ("Lecture_2/Notebooks/Lab_007_Building_and_training_networks.ipynb", "lab-007-building-and-training", "Lab 007: Building and training neural networks", "A complete training loop in PyTorch."),
            ("Lecture_2/Notebooks/Lab_008_Analysing_neural_networks.ipynb", "lab-008-analysing-networks", "Lab 008: Analysing a neural network", "Architecture, parameter counts and what a trained network does."),
        ],
    ),
    3: dict(
        deck=("beamer", "Lecture_3/beamer/main.tex"),
        title="MNIST: Training a Network by Hand",
        summary="MNIST digit classification step by step: the feed-forward pass, and the parameter update of the output and the hidden layer derived by hand and checked against automatic differentiation. A single output trained with the mean squared error against ten outputs trained with the categorical cross-entropy.",
        table_note="Lab 009: MNIST, regression versus cross-entropy",
        notebooks=[
            ("Lecture_2/Notebooks/Lab_009_MNIST_regression_vs_cross_entropy.ipynb", "lab-009-mnist", "Lab 009: MNIST, regression versus cross-entropy", "The same network trained with a single output and the mean squared error, and with ten outputs and the categorical cross-entropy."),
        ],
    ),
    4: dict(
        deck=("beamer", "Lecture_4/beamer/main.tex"),
        title="CNNs, Class Activation Maps, Adversarial Examples and the 2D Ising Model",
        summary="CIFAR-10 with dense and convolutional networks: convolution, kernels and Sobel filters, stride, padding, channels and pooling, and regularisation with L1/L2 penalties, dropout and batch normalisation. Class activation maps and Grad-CAM show where a CNN looks; adversarial examples show where it fails; the optimisers from stochastic gradient descent to Adam. The 2D Ising model: the partition function, the 1D chain and Onsager's solution in 2D, criticality, Metropolis sampling, and a CNN trained far from the transition whose prediction confidence drops at the critical temperature, for lattice sizes 10 to 50. The lecture closes with the Chinese Room thought experiment.",
        table_note="Labs 010–012: Ising Monte Carlo, $T_c$ from the confidence of a CNN, Onsager's solution",
        notebooks=[
            ("Lecture_4/Notebooks/Lab_010_Ising_Monte_Carlo_samples.ipynb", "lab-010-ising-monte-carlo", "Lab 010: Monte Carlo samples of the 2D Ising model", "The Metropolis algorithm, equilibration and decorrelation, and the data set of spin configurations, checked against Onsager's exact results."),
            ("Lecture_4/Notebooks/Lab_011_CNN_Tc_from_confidence.ipynb", "lab-011-cnn-tc", "Lab 011: T_c of the 2D Ising model from the confidence of a CNN", "A CNN trained only far from the transition, its confidence at all temperatures, and finite-size effects."),
            ("Lecture_4/Notebooks/Lab_012_Onsager_exact_solution.ipynb", "lab-012-onsager", "Lab 012: Onsager's exact solution of the 2D Ising model", "The transfer matrix, the high- and low-temperature expansions, Kramers–Wannier duality and an outline of the free-fermion solution, each checked by a computation."),
            ("Lecture_4/Notebooks/Ising_2D_Monte_Carlo_and_CNN.ipynb", "ising-2d-monte-carlo-and-cnn", "The 2D Ising model and a CNN", "The figures of the lecture: data sets for L = 10 to 50 and the CNN estimate of T_c for each size."),
        ],
    ),
    5: dict(
        deck=("beamer", "Lecture_5/beamer/main.tex"),
        title="Unsupervised Learning and Phase Diagrams without Labels",
        summary="Learning without labels: principal component analysis, t-SNE, k-means and DBSCAN clustering, and autoencoders whose reconstruction error detects anomalies. Anomaly detection for phase diagrams. The 2D Ising model: finite-size scaling, Swendsen–Wang cluster updates, the first principal component as the magnetisation, and autoencoders whose signal sharpens towards T_c with the lattice size, depending on the training region. The frustrated J1–J2 model: ground states, frustration and mean field, PCA finding both order parameters, and the phase diagram recovered by autoencoders trained on three corners, from a coarse scan.",
        table_note="Labs 016–020, 029–032: PCA, t-SNE, clustering, autoencoders, spin models in JAX, physics of the J1–J2 model, the 2D XY model, lattice gauge theory and spin glasses",
        notebooks=[
            ("Lecture_5/Notebooks/Lab_016_PCA_tSNE_and_clustering.ipynb", "lab-016-pca-tsne-clustering", "Lab 016: PCA, t-SNE and clustering in JAX", "Low-dimensional maps of MNIST and groups of samples found without labels."),
            ("Lecture_5/Notebooks/Lab_017_Autoencoders_and_anomaly_detection.ipynb", "lab-017-autoencoders-anomaly-detection", "Lab 017: Autoencoders and anomaly detection", "Images compressed through a narrow latent layer, and anomalies found from the reconstruction error."),
            ("Lecture_5/Notebooks/Lab_018_Spin_models_Monte_Carlo_in_JAX.ipynb", "lab-018-spin-models-monte-carlo", "Lab 018: Classical spin models in JAX, the 2D Ising and the J1–J2 model", "Metropolis and Swendsen–Wang samples of the 2D Ising model and of the frustrated J1–J2 model."),
            ("Lecture_5/Notebooks/Lab_019_Ising_phases_without_labels.ipynb", "lab-019-ising-without-labels", "Lab 019: The 2D Ising transition without labels", "PCA, autoencoders and finite-size scaling."),
            ("Lecture_5/Notebooks/Lab_020_J1J2_phase_diagram_without_labels.ipynb", "lab-020-j1j2-without-labels", "Lab 020: The J1–J2 phase diagram without labels", "PCA and autoencoders trained on one corner of the phase diagram."),
            ("Lecture_5/Notebooks/Lab_029_Physics_of_the_J1_J2_Ising_model.ipynb", "lab-029-physics-j1j2", "Lab 029: Physics of the frustrated J1–J2 Ising model", "Ground states, domain walls, exact limits, mean field, transfer matrices and Binder cumulants."),
            ("Lecture_5/Notebooks/Lab_030_Physics_of_the_2D_XY_model.ipynb", "lab-030-physics-2d-xy", "Lab 030: Physics of the 2D XY model and the Berezinskii–Kosterlitz–Thouless transition", "Spin waves and Mermin–Wagner, vortices, the helicity modulus and its universal jump, and three Monte Carlo samplers."),
            ("Lecture_5/Notebooks/Lab_031_Physics_of_the_Ising_lattice_gauge_theory.ipynb", "lab-031-physics-ising-gauge", "Lab 031: Physics of the Ising lattice gauge theory", "Gauge symmetry, Elitzur's theorem, the exact 2D solution, Wegner duality and Wilson loops."),
            ("Lecture_5/Notebooks/Lab_032_Physics_of_the_Sherrington_Kirkpatrick_spin_glass.ipynb", "lab-032-physics-sk-spin-glass", "Lab 032: Physics of the Sherrington–Kirkpatrick spin glass", "Frustration, replicas and overlaps, parallel tempering, the energy landscape and the Mattis model."),
        ],
    ),
    6: dict(
        deck=("beamer", "Lecture_6/beamer/main.tex"),
        title="Generative Models: Variational and Conditional Autoencoders",
        summary="Learning a probability distribution: likelihood and maximum likelihood, the variational autoencoder, the evidence lower bound as a variational free energy, and the reparametrisation trick. Synthetic data judged by classifiers trained on real data. The conditional VAE generates digits on demand. Generated spins and the Hamiltonian: conditional VAEs for the 2D Ising and the J1–J2 model reproduce the phase, the order parameter and the phase diagram at unseen parameters, but not the energy and its fluctuations.",
        table_note="Labs 024–025: VAE and cVAE, synthetic spin configurations tested against the Hamiltonian",
        notebooks=[
            ("Lecture_6/Notebooks/Lab_024_Generative_models_VAE_cVAE.ipynb", "lab-024-vae-cvae", "Lab 024: Variational and conditional autoencoders", "The ELBO derived step by step, VAE and cVAE on MNIST, and synthetic images judged by a classifier."),
            ("Lecture_6/Notebooks/Lab_025_cVAE_physics_synthetic_vs_real.ipynb", "lab-025-cvae-physics", "Lab 025: Synthetic spin configurations from a conditional VAE", "Generated Ising and J1–J2 configurations tested against Monte Carlo and the Hamiltonian."),
        ],
    ),
}

# the Resources page: the literature tiles (\restile calls) of the starter deck,
# one group per frame, with these headings
RESOURCES = dict(
    tex="Lecture_0_starter/beamer/sections/03_literature.tex",
    figures="Lecture_0_starter/beamer/figures",
    groups=["Lecture notes, ML for physics and science",
            "Mathematics and the broader context of AI"],
)

MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
DATE_PATTERNS = [
    r"\s*(?:&nbsp;)?\s*·?\s*(?:&nbsp;)?\s*\*\*Date:\*\*\s*\d{4}-\d{2}-\d{2}",  # " &nbsp;·&nbsp; **Date:** 2026-10-06"
    r"\s*\(\d{1,2}\.\d{1,2}\.\d{4}\)",                 # " (14.10.2026)"
    r"\s*\b\d{1,2}\.\d{1,2}\.\d{4}\b",                 # "14.10.2026"
    r"\s*\b\d{4}\.\d{1,2}\.\d{1,2}\b",                 # "2026.10.06"
    r"\s*\b\d{4}-\d{2}-\d{2}\b",                       # "2026-10-14"
    rf"\s*\b\d{{1,2}} (?:{MONTHS}) \d{{4}}\b",         # "14 October 2026"
]
ODP_DATES = [r"\b\d{4}\.\d{1,2}\.\d{1,2}\b", r"\b\d{1,2}\.\d{1,2}\.\d{4}\b"]


def run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"command failed: {' '.join(cmd)}\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
    return r.stdout


def published():
    return sorted(n for n in LECTURES if n in READY)


# ------------------------------------------------------------------ slides
def odp_to_pdf(src, tmp):
    """Convert an .odp deck to PDF from a temporary copy without dates."""
    copy = os.path.join(tmp, "deck.odp")
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(copy, "w") as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename in ("content.xml", "styles.xml"):
                xml = data.decode("utf-8")
                xml = re.sub(r'\s*presentation:use-date-time-name="[^"]*"', "", xml)  # date fields
                for p in ODP_DATES:
                    xml = re.sub(p, "", xml)
                data = xml.encode("utf-8")
            comp = zipfile.ZIP_STORED if item.filename == "mimetype" else zipfile.ZIP_DEFLATED
            zout.writestr(item, data, compress_type=comp)
    profile = "file://" + os.path.join(tmp, "lo_profile")
    run(["libreoffice", f"-env:UserInstallation={profile}", "--headless",
         "--convert-to", "pdf", "--outdir", tmp, copy])
    return os.path.join(tmp, "deck.pdf")


def beamer_to_pdf(src, tmp):
    """Compile a beamer deck with an empty date; all output goes to the temporary folder."""
    web = re.sub(r"\\date\{[^}]*\}", r"\\date{}", open(src).read())
    texfile = os.path.join(tmp, "main_web.tex")
    open(texfile, "w").write(web)
    for _ in range(2):
        run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error",
             f"-output-directory={tmp}", texfile], cwd=os.path.dirname(src))
    return os.path.join(tmp, "main_web.pdf")


def cut_after_frame(pdf, title, tmp):
    """Keep the pages up to the last page of the (first) frame with this title."""
    n = int(re.search(r"Pages:\s+(\d+)", run(["pdfinfo", pdf])).group(1))
    norm = lambda t: " ".join(t.split())
    has = [norm(title) in norm(run(["pdftotext", "-f", str(i), "-l", str(i), pdf, "-"]))
           for i in range(1, n + 1)]
    if True not in has:
        sys.exit(f"frame not found in the deck: {title}")
    last = has.index(True)
    while last + 1 < n and has[last + 1]:      # overlays of the same frame
        last += 1
    cut = os.path.join(tmp, "cut.pdf")
    run(["gs", "-sDEVICE=pdfwrite", "-dNOPAUSE", "-dBATCH", "-dQUIET",
         "-dFirstPage=1", f"-dLastPage={last + 1}", f"-sOutputFile={cut}", pdf])
    print(f"slides  cut after page {last + 1} of {n} ({title})")
    return cut


def build_slides():
    out = os.path.join(HERE, "slides"); os.makedirs(out, exist_ok=True)
    for old in glob.glob(os.path.join(out, "lecture-*.pdf")):
        n = int(re.search(r"lecture-(\d+)", old).group(1))
        if n not in READY or not LECTURES.get(n, {}).get("deck"):
            os.remove(old)
    for lec in published():
        if not LECTURES[lec]["deck"]:
            continue
        kind, rel = LECTURES[lec]["deck"]
        src = os.path.join(COURSE, rel)
        if not os.path.exists(src):
            sys.exit(f"lecture {lec}: deck not found: {src}")
        tmp = tempfile.mkdtemp(prefix="dlcqp_")
        try:
            pdf = {"pdf": lambda s, t: s, "odp": odp_to_pdf, "beamer": beamer_to_pdf}[kind](src, tmp)
            if LECTURES[lec].get("last_frame"):
                pdf = cut_after_frame(pdf, LECTURES[lec]["last_frame"], tmp)
            target = os.path.join(out, f"lecture-{lec:02d}.pdf")
            run(["gs", "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.5", "-dPDFSETTINGS=/ebook",
                 "-dNOPAUSE", "-dBATCH", "-dQUIET", f"-sOutputFile={target}", pdf])
            if os.path.getsize(target) > os.path.getsize(pdf):   # already compact: keep it
                shutil.copyfile(pdf, target)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        print(f"slides  lecture {lec}: {os.path.getsize(target) / 1e6:.1f} MB")


# ------------------------------------------------------------------ notebooks
def strip_dates(text):
    lines = [l for l in text.split("\n") if not re.match(r"^\s*\*?Notebook for the lecture of .*$", l)]
    text = "\n".join(lines)
    for p in DATE_PATTERNS:
        text = re.sub(p, "", text)
    return text


def standalone_paths(code):
    """Figures of the slides go to ./figures next to the notebook."""
    def fix(m):
        ind, var, rest = m.groups()
        if "makedirs" in rest:
            return f'{ind}{var} = "figures"{rest}'
        return f'{ind}import os\n{ind}{var} = "figures"; os.makedirs({var}, exist_ok=True){rest}'
    return re.sub(r'(?m)^(\s*)(\w+)\s*=\s*"\.\./beamer/figures"(.*)$', fix, code)


def notebooks_of(lec):
    """(source, web name, title, description) of the notebooks of a lecture."""
    listed = LECTURES[lec]["notebooks"]
    if listed is not None:
        return [(os.path.join(COURSE, s), w, t, d) for s, w, t, d in listed]
    found = []
    for src in sorted(glob.glob(os.path.join(COURSE, f"Lecture_{lec}", "Notebooks", "Lab_*.ipynb"))):
        nb = nbformat.read(src, as_version=4)
        title = os.path.splitext(os.path.basename(src))[0].replace("_", " ")
        for c in nb.cells:
            m = re.search(r"(?m)^#\s+(Lab\s+\d+)\s*[—–-]\s*(.+)$", c.source) if c.cell_type == "markdown" else None
            if m:
                title = f"{m.group(1)}: {m.group(2).strip()}"
                break
        web = re.sub(r"[^a-z0-9]+", "-", os.path.splitext(os.path.basename(src))[0].lower()).strip("-")
        found.append((src, web, title, ""))
    return found


def is_slide_export(cell):
    """A code cell that only exports numbers for the lecture slides (JSON / LaTeX macros)."""
    if cell.cell_type != "code":
        return False
    src = cell.source
    if re.search(r"plt\.|savefig|\.plot\(|train", src):          # a cell that also computes or plots is kept
        return False
    return (re.search(r"numbers_\w*\.json|setnbnum|nb_numbers", src) is not None) and ("json.dump" in src or ".write(" in src)


def drop_slide_export(cells):
    """Remove slide-export cells and the short markdown cell that only introduces one of them."""
    keep = []
    for i, c in enumerate(cells):
        if is_slide_export(c):
            if keep and keep[-1].cell_type == "markdown" and len(keep[-1].source) < 400 \
                    and re.search(r"slide|lecture|numbers", keep[-1].source, re.I) and not keep[-1].source.lstrip().startswith("#"):
                keep.pop()
            continue
        keep.append(c)
    return keep


def build_notebooks():
    dst = os.path.join(HERE, "notebooks")
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    for lec in published():
        for src, web_name, title, _ in notebooks_of(lec):
            nb = nbformat.read(src, as_version=4)
            rel = f"notebooks/lecture-{lec:02d}/{web_name}.ipynb"
            nb.cells = drop_slide_export(nb.cells)
            for c in nb.cells:
                c.metadata.pop("execution", None)   # run timestamps
                if c.cell_type == "markdown":
                    c.source = strip_dates(c.source)
                    c.source = re.sub(r"(?m)^\s*---\s*$", "<hr/>", c.source)
                elif c.cell_type == "code":
                    c.source = standalone_paths(c.source)
            safe = title.replace("'", "''").replace("T_c", "Tc")
            front = nbformat.v4.new_raw_cell(f"---\ntitle: '{safe}'\n---")
            badge = nbformat.v4.new_markdown_cell(
                f'<a href="https://colab.research.google.com/github/{REPO}/blob/main/{rel}">'
                f'<img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab"></a>')
            front.id, badge.id = "web-title", "web-colab-badge"   # fixed ids: no churn between builds
            nb.cells = [front, badge] + nb.cells
            os.makedirs(os.path.dirname(os.path.join(HERE, rel)), exist_ok=True)
            nbformat.write(nb, os.path.join(HERE, rel))
            print(f"notebook lecture {lec}: {rel}")


# ------------------------------------------------------------------ pages and menus
def yq(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def build_pages():
    os.makedirs(os.path.join(HERE, "lectures"), exist_ok=True)
    for old in glob.glob(os.path.join(HERE, "lectures", "lecture-*.qmd")):
        os.remove(old)
    nav, side, table = [], [], []
    for lec in published():
        L = LECTURES[lec]
        page = f"lectures/lecture-{lec:02d}.qmd"
        nbs = notebooks_of(lec)
        text = [f"---\ntitle: {yq(f'{lec} · ' + L['title'])}\ncode-tools: false\ntoc: false\n---\n"]
        if L["summary"]:
            text.append(L["summary"] + "\n")
        if L["deck"]:
            text.append(f"## Slides\n\n[Download the slides (PDF)](../slides/lecture-{lec:02d}.pdf){{.btn .btn-outline-primary}}\n\n"
                        f'<iframe src="../slides/lecture-{lec:02d}.pdf" width="100%" height="620" '
                        f'style="border:1px solid #dde6ef; border-radius:6px;"></iframe>\n')
        if nbs:
            text.append("## Notebooks\n")
            for _, web, title, desc in nbs:
                shown = title.replace("T_c", "$T_c$").replace("J1-J2", "$J_1$–$J_2$")
                item = f"::: {{.nb-item}}\n[{shown}](../notebooks/lecture-{lec:02d}/{web}.ipynb)\n"
                if desc:
                    item += f"\n{desc}\n"
                text.append(item + ":::\n")
        open(os.path.join(HERE, page), "w").write("\n".join(text))
        nav.append(f"          - text: {yq(f'{lec} · ' + L['title'])}\n            href: {page}")
        entry = f"      - section: {yq(f'{lec} · ' + L['title'])}\n        href: {page}"
        if nbs:
            entry += "\n        contents:\n" + "\n".join(
                f"          - notebooks/lecture-{lec:02d}/{web}.ipynb" for _, web, _, _ in nbs)
        side.append(entry)
        table.append(f"| {lec} | [{L['title']}]({page}) | {L['table_note']} |")
        print(f"page    lecture {lec}: {page}")
    yml = ["# Generated by prep_site.py from LECTURES and READY; do not edit by hand.",
           "website:", "  navbar:", "    left:",
           "      - text: \"Start here\"", "        href: index.qmd",
           "      - text: \"Lectures\"", "        menu:", *nav,
           "      - text: \"Resources\"", "        href: resources.qmd",
           "      - text: \"About\"", "        href: about.qmd",
           "  sidebar:", "    contents:",
           "      - text: \"Start here\"", "        href: index.qmd", *side,
           "      - text: \"Resources\"", "        href: resources.qmd",
           "      - text: \"About\"", "        href: about.qmd", ""]
    open(os.path.join(HERE, "_lectures.yml"), "w").write("\n".join(yml))
    md = ["| | Lecture | Notebooks |", "|---|---|---|", *table, ""]
    open(os.path.join(HERE, "_lectures_table.md"), "w").write("\n".join(md))


# ------------------------------------------------------------------ resources
def brace_args(text, pos, n):
    """The n brace-delimited arguments starting at text[pos:]; returns (args, end)."""
    args = []
    while len(args) < n:
        while text[pos] in " \t\n%":
            pos = text.index("\n", pos) + 1 if text[pos] == "%" else pos + 1
        assert text[pos] == "{", text[pos:pos + 40]
        depth, start = 0, pos
        while True:
            if text[pos] == "\\":
                pos += 2; continue
            depth += {"{": 1, "}": -1}.get(text[pos], 0)
            pos += 1
            if depth == 0:
                break
        args.append(text[start + 1:pos - 1])
    return args, pos


def latex_to_md(t):
    t = re.sub(r"\\href\{([^}]*)\}\{([^}]*)\}", r"[\2](\1)", t)
    for a, b in [(r"\(\cdot\)", "·"), ("\\l{}", "ł"), ("\\'n", "ń"), ("\\'e", "é"), ("\\ ", " "),
                 ("--", "–"), ("~", " ")]:
        t = t.replace(a, b)
    return " ".join(t.split())


def build_resources():
    tex = open(os.path.join(COURSE, RESOURCES["tex"])).read()
    frames = re.split(r"\\begin\{frame\}", tex)[1:]
    assert len(frames) == len(RESOURCES["groups"]), "one heading per literature frame"
    out = os.path.join(HERE, "assets", "resources")
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)
    md = ['---\ntitle: "Resources"\ntoc: false\ncode-tools: false\n---\n']
    for heading, frame in zip(RESOURCES["groups"], frames):
        md.append(f"## {heading}\n\n::: {{.res-grid}}")
        for m in re.finditer(r"\\restile(?=\{)", frame):
            (thumb, _, title, line, link), _ = brace_args(frame, m.end(), 5)
            src = os.path.join(COURSE, RESOURCES["figures"], thumb)
            img = Image.open(src)
            if img.height > 450:                       # covers: web size
                img.thumbnail((10000, 450))
            img.save(os.path.join(out, thumb))
            title, line, link = latex_to_md(title), latex_to_md(line), latex_to_md(link)
            card = [f"::: {{.res-card}}", f"::: {{.res-thumb}}",
                    f'![](assets/resources/{thumb}){{fig-alt="{title}"}}', ":::", "::: {.res-body}",
                    f"::: {{.res-title}}\n{title}\n:::", f"::: {{.res-line}}\n{line}\n:::"]
            if link:
                card.append(f"::: {{.res-link}}\n{link}\n:::")
            card += [":::", ":::"]
            md.append("\n".join(card))
        md.append(":::\n")
    open(os.path.join(HERE, "resources.qmd"), "w").write("\n\n".join(md))
    print(f"page    resources.qmd: {sum(len(re.findall(r'restile(?=\{)', f)) for f in frames)} items")


if __name__ == "__main__":
    what = sys.argv[1:] or ["slides", "notebooks", "pages"]
    if "slides" in what:
        build_slides()
    if "notebooks" in what:
        build_notebooks()
    if "pages" in what:
        build_pages()
        build_resources()
