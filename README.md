# Deep Learning in Classical and Quantum Physics

Lecture slides and notebooks of the course *Deep Learning in Classical and Quantum Physics*, Jagiellonian University in Kraków, by [Marcin Płodzień](https://chaos.if.uj.edu.pl/marcinplodzien/).

Website: <https://marcinplodzien.github.io/deep-learning-for-classical-and-quantum-physics/>

- `slides/` — the slides of each lecture (PDF)
- `notebooks/lecture-NN/` — the notebooks of each lecture, with their outputs; each can be opened in Google Colab
- `docs/` — the rendered website

The site is built with [Quarto](https://quarto.org) by `build.sh` and published from `docs/` by GitHub Actions.

## Publishing a new lecture

All lectures are described in `LECTURES` in `prep_site.py` (deck, title, summary, notebooks); only the lectures listed in `READY` are published. Lectures 5 (*Unsupervised Learning*) and 6 (*Generative Models*) are prepared but not yet published. To publish one:

1. add its number to `READY = {1, 2, 3, 4}` in `prep_site.py`;
2. run `./build.sh`;
3. commit and push.

`prep_site.py` then writes the slides, the notebooks, the lecture page `lectures/lecture-NN.qmd`, the navbar menu and sidebar (`_lectures.yml`, merged into `_quarto.yml`) and the table of lectures on the start page (`_lectures_table.md`); none of these is edited by hand. For Lecture 6, fill in `summary` and check the `deck` path (`Lecture_6/beamer/main.tex`) once the folder exists; with `notebooks=None` every `Lab_*.ipynb` in `Lecture_6/Notebooks` is published, titled from its `# Lab NNN — ...` heading (replace with an explicit list to add one-line descriptions).

## Slides

A lecture with `deck=None` is published without slides. To add the slides of Lectures 1–3, set their `deck` to `("beamer", "Lecture_N/beamer/main.tex")` (the line is already in `prep_site.py` as a comment) and run `./build.sh`. `last_frame` publishes a deck only up to the last page of the frame with that title; Lecture 4 ends at *Interpretation of the Result*.
