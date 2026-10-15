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

HERE = os.path.dirname(os.path.abspath(__file__))
COURSE = os.path.dirname(HERE)
REPO = "MarcinPlodzien/deep-learning-for-classical-and-quantum-physics"

# lectures that are published
READY = {1, 2, 3, 4}

# Each lecture: deck (kind, path relative to the course folder; None = no slides on
# the site), optionally last_frame (publish the deck only up to the last page of the
# frame with this title), title,
# summary for the lecture page, a short note on the notebooks for the start page,
# and notebooks as (source relative to the course folder, web name, title, description);
# notebooks=None takes every Lab_*.ipynb of <folder>/Notebooks.
# Labs 001-009 also exist as identical copies in Lecture_4/Notebooks.
LECTURES = {
    1: dict(
        deck=None,   # later: ("beamer", "Lecture_1/beamer/main.tex")
        title="The Second Quantum Revolution",
        summary="The second quantum revolution: generating, storing, manipulating and detecting many-body entanglement, and machine learning for quantum technologies, from the variational quantum eigensolver and the optimisation of quantum circuits to quantum state tomography, error correction and error mitigation with neural networks. The lecture closes with the literature on machine learning for physics and for science.",
        table_note="",
        notebooks=[],
    ),
    2: dict(
        deck=None,   # later: ("beamer", "Lecture_2/beamer/main.tex")
        title="From Artificial Intelligence to Deep Learning",
        summary="Big goals of quantum physics that machine learning can serve, from the compilation of quantum circuits to neural-network quantum states. The approaches to artificial intelligence, the hierarchy of AI, machine learning and deep learning, the three paradigms of machine learning (unsupervised, supervised and reinforcement learning), and the step from algorithm-driven to data-driven programming, with features extracted by hand or learned automatically. Neural networks as non-linear parametrised functions with nested structure, the universal approximation theorem, and the elements of deep learning: the loss function, from the Kullback–Leibler divergence to the categorical cross-entropy, the architecture and gradient descent; a neural network learns the probability distribution of its training data.",
        table_note="Labs 001–003: Python, NumPy, PyTorch",
        notebooks=[
            ("Lecture_2/Notebooks/Lab_001_Python_Matplotlib_Pandas_warmup.ipynb", "lab-001-python-matplotlib-pandas", "Lab 001: Python, Matplotlib and Pandas", "A warm-up with the tools used in every later notebook."),
            ("Lecture_2/Notebooks/Lab_002_NumPy_basics.ipynb", "lab-002-numpy", "Lab 002: NumPy, thinking in arrays", "Vectorised computation instead of loops."),
            ("Lecture_2/Notebooks/Lab_003_PyTorch_basics.ipynb", "lab-003-pytorch", "Lab 003: PyTorch tensors, devices and layers", "The basic objects of PyTorch."),
        ],
    ),
    3: dict(
        deck=None,   # later: ("beamer", "Lecture_3/beamer/main.tex")
        title="Elements of Deep Learning: from MNIST to the 2D Ising Model",
        summary="The anatomy of a neural network, loss functions for regression and classification, the zoo of architectures and training by gradient descent. Two \"hello world\" examples: MNIST digits, classified by a feed-forward network with the categorical cross-entropy, and CIFAR-10 images, where convolutional networks capture spatial correlations and L1/L2 regularisation, dropout and batch normalisation fight overfitting; optimisers from stochastic gradient descent to Adam. A physics example: the 2D Ising model, Onsager's solution, Monte Carlo samples from the Gibbs distribution, and the prediction confidence of a network that locates the critical temperature; the lecture closes with the Chinese Room thought experiment and the Hopfield network.",
        table_note="Labs 004–009: automatic differentiation, universal approximation, training, MNIST",
        notebooks=[
            ("Lecture_2/Notebooks/Lab_004_Automatic_differentiation.ipynb", "lab-004-automatic-differentiation", "Lab 004: Automatic differentiation", "Derivatives computed by the machine, exactly."),
            ("Lecture_2/Notebooks/Lab_005_N_pendulum_SymPy_and_autodiff.ipynb", "lab-005-n-pendulum", "Lab 005: The N-link pendulum with SymPy and automatic differentiation", "Equations of motion obtained symbolically and by automatic differentiation."),
            ("Lecture_2/Notebooks/Lab_006_UAT_and_minimizers.ipynb", "lab-006-uat-and-minimisers", "Lab 006: Universal approximation and the choice of minimiser", "Fitting functions with networks, and the role of the optimiser."),
            ("Lecture_2/Notebooks/Lab_007_Building_and_training_networks.ipynb", "lab-007-building-and-training", "Lab 007: Building and training neural networks", "A complete training loop in PyTorch."),
            ("Lecture_2/Notebooks/Lab_008_Analysing_neural_networks.ipynb", "lab-008-analysing-networks", "Lab 008: Analysing a neural network", "Architecture, parameter counts and what a trained network does."),
            ("Lecture_2/Notebooks/Lab_009_MNIST_regression_vs_cross_entropy.ipynb", "lab-009-mnist", "Lab 009: MNIST, regression versus cross-entropy", "The same network trained with a single output and the mean squared error, and with ten outputs and the categorical cross-entropy."),
        ],
    ),
    4: dict(
        deck=("beamer", "Lecture_4/beamer/main.tex"),
        last_frame="Interpretation of the Result",   # the deck is published up to this frame
        title="CNNs, Class Activation Maps, Adversarial Examples and the 2D Ising Model",
        summary="CIFAR-10 with dense and convolutional networks: convolution, continuous and discrete, kernels and Sobel filters, stride, padding, channels and pooling, and regularisation with L1/L2 penalties, dropout and batch normalisation. Class activation maps and Grad-CAM show where a CNN looks; adversarial examples, from the fast gradient sign method to the one-pixel attack, show where it fails; the optimisers from stochastic gradient descent to Adam, under the hood. The 2D Ising model: the partition function, the 1D chain and Onsager's solution in 2D, criticality, Metropolis sampling of spin configurations, and a CNN trained far from the transition whose prediction confidence drops at the critical temperature.",
        table_note="Labs 010–012: Ising Monte Carlo, $T_c$ from the confidence of a CNN, Onsager's solution",
        notebooks=[
            ("Energy_Based_Models/Notebooks/Lab_010_Ising_Monte_Carlo_samples.ipynb", "lab-010-ising-monte-carlo", "Lab 010: Monte Carlo samples of the 2D Ising model", "The Metropolis algorithm, equilibration and decorrelation, and the data set of spin configurations, checked against Onsager's exact results."),
            ("Energy_Based_Models/Notebooks/Lab_011_CNN_Tc_from_confidence.ipynb", "lab-011-cnn-tc", "Lab 011: T_c of the 2D Ising model from the confidence of a CNN", "A CNN trained only far from the transition, its confidence at all temperatures, and finite-size effects."),
            ("Energy_Based_Models/Notebooks/Lab_012_Onsager_exact_solution.ipynb", "lab-012-onsager", "Lab 012: Onsager's exact solution of the 2D Ising model", "The transfer matrix, the high- and low-temperature expansions and Kramers–Wannier duality, each checked by a computation."),
        ],
    ),
    5: dict(
        deck=("beamer", "Lecture_5/beamer/main.tex"),
        title="Unsupervised Learning: PCA, t-SNE, Clustering and Autoencoders",
        summary="Learning without labels. Principal component analysis as a linear projection and t-SNE as a non-linear map of MNIST; k-means and DBSCAN clustering, with the silhouette score and the adjusted Rand index to choose and judge the clusters. Autoencoders compress images into a latent space, and their reconstruction error detects anomalies, scored by the ROC curve. The same tools on scientific data: blood cells without labels, and the 2D Ising model, where the first principal component is the magnetisation and an autoencoder detects the phase transition.",
        table_note="Labs 016–018: PCA, t-SNE, clustering, autoencoders, spin models in JAX",
        notebooks=[
            ("Lecture_5/Notebooks/Lab_016_PCA_tSNE_and_clustering.ipynb", "lab-016-pca-tsne-clustering", "Lab 016: PCA, t-SNE and clustering in JAX", "Low-dimensional maps of MNIST and groups of samples found without labels."),
            ("Lecture_5/Notebooks/Lab_017_Autoencoders_and_anomaly_detection.ipynb", "lab-017-autoencoders-anomaly-detection", "Lab 017: Autoencoders and anomaly detection", "Images compressed through a narrow latent layer, and anomalies found from the reconstruction error."),
            ("Lecture_5/Notebooks/Lab_018_Spin_models_Monte_Carlo_in_JAX.ipynb", "lab-018-spin-models-monte-carlo", "Lab 018: Classical spin models in JAX, the 2D Ising and the J1-J2 model", "Monte Carlo samples of the 2D Ising model and of the frustrated $J_1$–$J_2$ model."),
        ],
    ),
    6: dict(
        deck=("beamer", "Lecture_6/beamer/main.tex"),
        title="Generative Models",
        summary="",
        table_note="",
        notebooks=None,   # None: every Lab_*.ipynb in Lecture_6/Notebooks is taken
    ),
}

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


def build_notebooks():
    dst = os.path.join(HERE, "notebooks")
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    for lec in published():
        for src, web_name, title, _ in notebooks_of(lec):
            nb = nbformat.read(src, as_version=4)
            rel = f"notebooks/lecture-{lec:02d}/{web_name}.ipynb"
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
           "      - text: \"About\"", "        href: about.qmd",
           "  sidebar:", "    contents:",
           "      - text: \"Start here\"", "        href: index.qmd", *side,
           "      - text: \"About\"", "        href: about.qmd", ""]
    open(os.path.join(HERE, "_lectures.yml"), "w").write("\n".join(yml))
    md = ["| | Lecture | Notebooks |", "|---|---|---|", *table, ""]
    open(os.path.join(HERE, "_lectures_table.md"), "w").write("\n".join(md))


if __name__ == "__main__":
    what = sys.argv[1:] or ["slides", "notebooks", "pages"]
    if "slides" in what:
        build_slides()
    if "notebooks" in what:
        build_notebooks()
    if "pages" in what:
        build_pages()
