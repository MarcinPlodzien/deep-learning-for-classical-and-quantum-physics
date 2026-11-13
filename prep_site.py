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
READY = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13}

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
        summary="The lecture opens with goals of quantum physics that machine learning can serve and places deep learning within artificial intelligence, where programs are learned from data and the features that describe the data are learned by the network. We then introduce a neural network as a non-linear function with parameters. Without a non-linear activation, extra layers add no expressive power. With ReLU units a network approximates any continuous curve by straight pieces, and a steep sigmoid approximates a step, which leads to the universal approximation theorem. The lecture closes with regression and classification and with the literature of the course.",
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
        summary="We train a network by minimising a loss function, chosen for regression or for classification, with gradient descent on mini-batches, and count the training in iterations and epochs. The lecture surveys the main architectures, discusses what makes a network well trained, and describes a trained network as a model of the probability distribution of its training data. It also reviews the factors behind the recent success of deep learning. The first complete example is the classification of MNIST digits as non-linear function fitting with the categorical cross-entropy.",
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
        summary="We work through the classification of MNIST digits in detail. After the feed-forward pass we derive the parameter updates of the output layer and of the hidden layer analytically and check them against automatic differentiation. We then train the same network with a single output and the mean squared error, and with ten outputs and the categorical cross-entropy, and compare the two.",
        table_note="Lab 009: MNIST, regression versus cross-entropy",
        notebooks=[
            ("Lecture_2/Notebooks/Lab_009_MNIST_regression_vs_cross_entropy.ipynb", "lab-009-mnist", "Lab 009: MNIST, regression versus cross-entropy", "The same network trained with a single output and the mean squared error, and with ten outputs and the categorical cross-entropy."),
        ],
    ),
    4: dict(
        deck=("beamer", "Lecture_4/beamer/main.tex"),
        title="CNNs, Class Activation Maps, Adversarial Examples and the 2D Ising Model",
        summary="Convolutional networks use the spatial structure of images. We build them on CIFAR-10 from convolution kernels such as Sobel filters, with stride, padding, channels and pooling, and regularise them with L1 and L2 penalties, dropout and batch normalisation. Class activation maps and Grad-CAM show which image regions drive a prediction, and adversarial examples show how small perturbations change it. A survey of optimisers leads from stochastic gradient descent to Adam. The second half of the lecture turns to the 2D Ising model. We introduce its partition function, the exact solution of the 1D chain and Onsager's solution in 2D, critical behaviour, mean field, universality and Metropolis sampling. A CNN trained only far from the transition then classifies configurations at all temperatures, and its confidence drops near the critical temperature for lattice sizes from 10 to 50. The lecture ends with the Chinese Room thought experiment.",
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
        notes="Lecture_5/Lecture_notes/lecture_notes.pdf",   # student lecture notes, published as notes/lecture-NN.pdf
        title="Unsupervised Learning and Phase Diagrams without Labels",
        summary="Unsupervised learning finds structure in data without labels. Principal component analysis gives each sample new coordinates along the directions of largest variance, and t-SNE draws a two-dimensional map that preserves neighbourhoods. k-means and DBSCAN group the samples into clusters, and an autoencoder compresses each sample through a narrow latent layer, so that a large reconstruction error marks an anomaly. We then apply these tools to phase diagrams. For the 2D Ising model the first principal component is the magnetisation, and an autoencoder trained in one phase gives a signal that sharpens towards T_c as the lattice grows, which we compare with finite-size scaling from Swendsen–Wang cluster updates. In the frustrated J1–J2 model with ferromagnetic and stripe order, PCA finds both order parameters, and autoencoders trained in three corners of the phase diagram recover the diagram from a coarse scan. The 2D XY model has no order parameter, and its Berezinskii–Kosterlitz–Thouless transition is driven by vortices. Autoencoders trained on spins, vortex maps and bond energies place the transition above the known temperature.",
        table_note="Labs 016–023, 029–032: PCA, t-SNE, clustering, autoencoders, spin models in JAX, physics of the J1–J2 model, the 2D XY model, lattice gauge theory and spin glasses",
        notebooks=[
            ("Lecture_5/Notebooks/Lab_016_PCA_tSNE_and_clustering.ipynb", "lab-016-pca-tsne-clustering", "Lab 016: PCA, t-SNE and clustering in JAX", "Low-dimensional maps of MNIST and groups of samples found without labels."),
            ("Lecture_5/Notebooks/Lab_017_Autoencoders_and_anomaly_detection.ipynb", "lab-017-autoencoders-anomaly-detection", "Lab 017: Autoencoders and anomaly detection", "Images compressed through a narrow latent layer, and anomalies found from the reconstruction error."),
            ("Lecture_5/Notebooks/Lab_018_Spin_models_Monte_Carlo_in_JAX.ipynb", "lab-018-spin-models-monte-carlo", "Lab 018: Classical spin models in JAX, the 2D Ising and the J1–J2 model", "Metropolis and Swendsen–Wang samples of the 2D Ising model and of the frustrated J1–J2 model."),
            ("Lecture_5/Notebooks/Lab_019_Ising_phases_without_labels.ipynb", "lab-019-ising-without-labels", "Lab 019: The 2D Ising transition without labels", "PCA, autoencoders and finite-size scaling."),
            ("Lecture_5/Notebooks/Lab_020_J1J2_phase_diagram_without_labels.ipynb", "lab-020-j1j2-without-labels", "Lab 020: The J1–J2 phase diagram without labels", "PCA and autoencoders trained on one corner of the phase diagram."),
            ("Lecture_5/Notebooks/Lab_021_XY_model_without_labels.ipynb", "lab-021-xy-without-labels", "Lab 021: The 2D XY model without labels", "PCA and autoencoders on spins, vortex maps and bond energies; the magnetisation crossover, network capacity and the BKT extrapolation."),
            ("Lecture_5/Notebooks/Lab_022_Ising_gauge_theory_without_labels.ipynb", "lab-022-gauge-without-labels", "Lab 022: Ising gauge theory without labels", "Raw links, plaquettes and Wilson loops as inputs for PCA and autoencoders (optional)."),
            ("Lecture_5/Notebooks/Lab_023_Spin_glass_without_labels.ipynb", "lab-023-sk-without-labels", "Lab 023: The SK spin glass without labels", "Single snapshots against replica overlap fields, with the Mattis model as a control (optional)."),
            ("Lecture_5/Notebooks/Lab_029_Physics_of_the_J1_J2_Ising_model.ipynb", "lab-029-physics-j1j2", "Lab 029: Physics of the frustrated J1–J2 Ising model", "Ground states, domain walls, exact limits, mean field, transfer matrices and Binder cumulants."),
            ("Lecture_5/Notebooks/Lab_030_Physics_of_the_2D_XY_model.ipynb", "lab-030-physics-2d-xy", "Lab 030: Physics of the 2D XY model and the Berezinskii–Kosterlitz–Thouless transition", "Spin waves and Mermin–Wagner, vortices, the helicity modulus and its universal jump, and three Monte Carlo samplers."),
            ("Lecture_5/Notebooks/Lab_031_Physics_of_the_Ising_lattice_gauge_theory.ipynb", "lab-031-physics-ising-gauge", "Lab 031: Physics of the Ising lattice gauge theory", "Gauge symmetry, Elitzur's theorem, the exact 2D solution, Wegner duality and Wilson loops."),
            ("Lecture_5/Notebooks/Lab_032_Physics_of_the_Sherrington_Kirkpatrick_spin_glass.ipynb", "lab-032-physics-sk-spin-glass", "Lab 032: Physics of the Sherrington–Kirkpatrick spin glass", "Frustration, replicas and overlaps, parallel tempering, the energy landscape and the Mattis model."),
        ],
    ),
    6: dict(
        deck=("beamer", "Lecture_6/beamer/main.tex"),
        notes="Lecture_6/Lecture_notes/lecture_notes.pdf",   # student lecture notes, published as notes/lecture-NN.pdf
        title="Generative Models: Variational Autoencoders and Disentanglement",
        summary="A generative model learns the probability distribution of the data and draws new samples from it. An autoencoder maps each image to an isolated code, and most points of its latent space decode to images that are not digits. The variational autoencoder (VAE) replaces each code by a small cloud, fits a continuous distribution in latent space with the evidence lower bound, and generates a new image in two steps, a latent vector from the prior followed by the decoder. We compare reconstruction with generation, study interpolation and the coverage of the prior, and judge the synthetic images with classifiers trained on real data. The conditional VAE generates at a chosen condition. For spin configurations at a chosen temperature it reproduces the phase and the order parameter, while the energy deviates because the spins are drawn independently once the latent vector is fixed. The β-VAE pushes each latent coordinate towards a single property of the data. We measure the result with rate and distortion, latent traversals and the mutual information gap on simple shapes and faces, and use the same model to extract physical parameters from spin configurations, noisy trajectories and galaxy images.",
        table_note="Labs 024–028: VAE and cVAE, spin configurations from a cVAE, the β-VAE, physical parameters from trajectories, galaxy morphology",
        notebooks=[
            ("Lecture_6/Notebooks/Lab_024_Generative_models_VAE_cVAE.ipynb", "lab-024-vae-cvae", "Lab 024: Variational and conditional autoencoders", "The ELBO derived step by step, VAE and cVAE on MNIST, and synthetic images judged by a classifier."),
            ("Lecture_6/Notebooks/Lab_025_cVAE_physics_synthetic_vs_real.ipynb", "lab-025-cvae-physics", "Lab 025: Synthetic spin configurations from a conditional VAE", "Generated Ising and J1–J2 configurations tested against Monte Carlo and the Hamiltonian, the ELBO as a variational free energy, symmetry and correlation length, Monte Carlo started from generated configurations, finite-size behaviour, Ising gauge theory and long-range Ising."),
            ("Lecture_6/Notebooks/Lab_026_Disentangled_representations_beta_VAE.ipynb", "lab-026-beta-vae", "Lab 026: Disentangled representations and the β-VAE", "The β-weighted loss, rate and distortion, dSprites and the mutual information gap, CelebA faces, and the physics learned from spin configurations, noisy trajectories and galaxy images."),
            ("Lecture_6/Notebooks/Lab_028_Physical_parameters_from_trajectories.ipynb", "lab-028-trajectories", "Lab 028: Physical parameters from trajectories", "A β-VAE on noisy oscillator and coupled-mass trajectories: which latent coordinates follow the physical parameters, and a reimplementation of the question-and-answer network of Iten et al."),
            ("Lecture_6/Notebooks/Lab_027_Galaxy_morphology_beta_VAE.ipynb", "lab-027-galaxy-morphology", "Lab 027: Galaxy morphology with a β-VAE", "Galaxy10 DECaLS images in PyTorch: latent coordinates against measured size, brightness and shape, and counterfactual images for a morphology classifier."),
        ],
    ),
    7: dict(
        deck=("beamer", "Lecture_7/beamer/main.tex"),
        notes="Lecture_7/Lecture_notes/lecture_notes.pdf",   # student lecture notes, published as notes/lecture-NN.pdf
        title="Time Series: Dynamical Systems, Chaos and Embedding",
        ship_data=True,   # data files are published next to the notebooks (data/), with a download cell for Colab
        summary="A forecast maps the past of a signal to a value at a chosen horizon, and we score it by the capacity, the squared correlation between forecast and target. We describe dynamical systems by their state, phase space, flow map and attractors, follow the volume of a set of states with Liouville's theorem, and introduce three benchmark signals, the Lorenz-63 model, the Mackey–Glass delay equation at three delays and the Santa Fe laser record. Small errors grow at the rate of the Lyapunov exponents, which set a fundamental limit on the prediction horizon, and the Kaplan–Yorke dimension measures how many dimensions the attractor really occupies. Takens' theorem says that a window of past values carries the full state, so that a forecast map exists, and we choose its delay by the mutual information and its dimension by false nearest neighbours. The lecture ends with the characteristics of the benchmark signals, everything a forecast from the record alone needs.",
        table_note="Lab 033: dynamical systems, Lyapunov exponents, Kaplan–Yorke dimension, delay embedding, mutual information and false nearest neighbours",
        notebooks=[
            ("Lecture_7/Notebooks/Lab_033_Signal_characterisation.ipynb", "lab-033-signal-characterisation", "Lab 033: Signal characterisation", "Lorenz, Mackey–Glass and Santa Fe signals, autocorrelation, power spectra, surrogate data tests, delay embedding, Lyapunov exponents and the Kaplan–Yorke dimension."),
        ],
    ),
    8: dict(
        deck=("beamer", "Lecture_8/beamer/main.tex"),
        notes="Lecture_8/Lecture_notes/lecture_notes.pdf",   # student lecture notes, published as notes/lecture-NN.pdf
        title="Forecasting Models: Linear, Neural and Physics-Informed",
        ship_data=True,   # data files are published next to the notebooks (data/), with a download cell for Colab
        summary="After a recap of the forecasting problem we forecast the benchmark signals from the record alone, with AR, MA and ARMA models, the Koopman view of a linear readout and the nonlinear vector autoregression (NVAR), and then with neural networks that learn the features, the multilayer perceptron and the recurrent RNN and LSTM. The second part adds physics to the models. A neural ordinary differential equation learns the unknown vector field of the equation of motion and is trained through the solver, and the learned field is analysed like an equation of motion, with its fixed points and its divergence, which tells a dissipative from a conservative system. A physics-informed neural network (PINN) puts a known law into the loss as a residual, for the damped oscillator, the heat equation in a rod and the Schrödinger equation of a trapped particle, and we compare it with classical solvers and use it to estimate unknown parameters from sparse data. Hybrid models keep the known terms and learn only the missing one, the friction of a pendulum and the interaction of predators and prey, and sparse regression turns the learned term into a formula.",
        table_note="Labs 034–039, 041–045 and Exercises 01–04: linear models and NVAR, MLP, RNN and LSTM, neural ODEs, PINNs, hybrid models",
        notebooks=[
            ("Lecture_7/Notebooks/Lab_034_Forecasting_with_linear_models_and_NVAR.ipynb", "lab-034-linear-models-nvar", "Lab 034: Forecasting with linear models and NVAR", "Scores and baselines, AR, MA, ARMA and ARIMA models, and the nonlinear vector autoregression in JAX, scikit-learn and ReservoirPy."),
            ("Lecture_8/Notebooks/Lab_035_Lifting_and_the_Koopman_operator.ipynb", "lab-035-koopman", "Lab 035: Lifting and the Koopman operator", "An exactly linearisable nonlinear map, the Koopman operator, dynamic mode decomposition, its delay version and AR as the smallest dictionary."),
            ("Lecture_8/Notebooks/Lab_036_Recurrent_neural_networks.ipynb", "lab-036-recurrent-networks", "Lab 036: Recurrent neural networks and reservoirs", "MLP, RNN, LSTM and GRU trained in JAX and Flax, the echo state network in JAX and ReservoirPy, the echo state property, memory capacity, NARMA and the comparison on all signals."),
            ("Lecture_8/Notebooks/Lab_037_MLP_forecaster.ipynb", "lab-037-mlp-forecaster", "Lab 037: MLP forecaster", "A multilayer perceptron on the window of past values, trained in JAX and with a library version, on Santa Fe and Mackey–Glass at three delays."),
            ("Lecture_8/Notebooks/Lab_038_RNN_forecaster.ipynb", "lab-038-rnn-forecaster", "Lab 038: RNN forecaster", "The Elman recurrent network, backpropagation through time and vanishing gradients, forecasts at many horizons on Santa Fe and Mackey–Glass."),
            ("Lecture_8/Notebooks/Lab_039_LSTM_forecaster.ipynb", "lab-039-lstm-forecaster", "Lab 039: LSTM forecaster", "The long short-term memory cell, its gates and learned memory times, forecasts on Santa Fe and Mackey–Glass."),
            ("Lecture_8/Notebooks/Lab_041_Physics_informed_neural_networks.ipynb", "lab-041-pinn", "Lab 041: Physics-informed neural networks", "PINN for the damped oscillator against a classical solver, the residual as prior knowledge, an inverse problem and time marching for the pendulum."),
            ("Lecture_8/Notebooks/Lab_042_Neural_ordinary_differential_equations.ipynb", "lab-042-neural-ode", "Lab 042: Neural ordinary differential equations", "Euler steps and residual networks, training through the solver with backpropagation and the adjoint method, the damped pendulum, Lorenz-63 and irregular sampling."),
            ("Lecture_8/Notebooks/Lab_043_Pendulum_with_unknown_friction.ipynb", "lab-043-pendulum-friction", "Lab 043: Pendulum with unknown friction", "A hybrid model with known gravity and a learned friction, sparse regression of the friction law and forecasts far beyond the data."),
            ("Lecture_8/Notebooks/Lab_044_Predator_prey_with_unknown_interaction.ipynb", "lab-044-predator-prey", "Lab 044: Predator–prey with unknown interaction", "Lotka–Volterra and a saturating predator, the learned interaction, its formula from sparse regression and a seasonal driver."),
            ("Lecture_8/Notebooks/Lab_045_Schroedinger_equation_with_PINNs.ipynb", "lab-045-schroedinger-pinn", "Lab 045: Schrödinger equation with PINNs", "A particle in a harmonic trap and tunnelling in a double well, the evolution predicted from a few snapshots with and without the Schrödinger residual against split-step Fourier, energy and phase checks, scans of snapshots and noise, and unknown trap frequency and barrier height."),
            ("Lecture_8/Exercises/Exercise_01_Rossler_and_superimposed_oscillators_tasks.ipynb", "exercise-01-rossler-oscillators", "Exercise 01: Rössler system and superimposed oscillators", "Characterise and forecast the Rössler signal and a sum of sine waves with the methods of Lectures 7 and 8."),
            ("Lecture_8/Exercises/Exercise_02_Stock_market_returns_tasks.ipynb", "exercise-02-stock-market-returns", "Exercise 02: Stock market returns", "The same analysis on daily returns of the S&P 500 index, with the baselines that every forecast must beat."),
            ("Lecture_8/Exercises/Exercise_03_Koopman_operator_tasks.ipynb", "exercise-03-koopman", "Exercise 03: Koopman operator", "Closed dictionaries of a lifted map, DMD eigenvalues, Koopman eigenfunctions of the pendulum with EDMD, and delay DMD of measured signals with a ridge penalty."),
            ("Lecture_8/Exercises/Exercise_04_Schroedinger_PINN_tasks.ipynb", "exercise-04-schroedinger-pinn", "Exercise 04: Schrödinger equation with PINNs", "A coherent state, Crank–Nicolson and split-step references, a PINN in an anharmonic trap, and how the collocation density controls the norm drift."),
        ],
    ),
    9: dict(
        deck=("beamer", "Lecture_9/beamer/main.tex"),
        notes="Lecture_9/Lecture_notes/lecture_notes.pdf",   # student lecture notes, published as notes/lecture-NN.pdf
        title="Reservoir Computing",
        ship_data=True,   # data files are published next to the notebooks (data/), with a download cell for Colab
        summary="Reservoir computing forecasts without training the network. Training every weight of a recurrent network through the history is slow and costly, and Koopman theory suggests another route, lifting the dynamics into many observables where it becomes nearly linear. A fixed random driven system, the echo state network, provides such a lift, and only a linear readout is fitted by one ridge solve. We define the echo state property and fading memory, measure the memory capacity, and compare the reservoir with trained networks on the benchmark signals. Run in a closed loop on the Lorenz system, the reservoir follows the weather for a few Lyapunov times and reproduces the climate. The same idea works with other systems. An elementary cellular automaton combines the bits of the input by logic, and a register of interacting qubits forgets its start only when its dynamics is chaotic, which the level-spacing ratio of its spectrum reveals.",
        table_note="Labs 046, 047, 049, 050: echo state networks, quantum reservoirs, closed-loop climate, cellular-automaton reservoirs",
        notebooks=[
            ("Lecture_9/Notebooks/Lab_046_Echo_state_networks.ipynb", "lab-046-echo-state-networks", "Lab 046: Echo state networks", "The leaky echo state network in JAX, the echo state property and fading memory, the roles of spectral radius, leak and input scale, memory capacity, NARMA and the comparison with trained networks."),
            ("Lecture_9/Notebooks/Lab_047_Quantum_reservoir_computing.ipynb", "lab-047-quantum-reservoir-computing", "Lab 047: Quantum reservoir computing", "A register of interacting qubits as a reservoir: the encoding, quantum chaos and the level-spacing ratio, forgetting, memory and forecasts of the Santa Fe laser."),
            ("Lecture_9/Notebooks/Lab_049_Reservoir_climate.ipynb", "lab-049-reservoir-climate", "Lab 049: Weather and climate of an echo state network", "A closed-loop echo state network on Lorenz-63, the valid time, attractor densities, the return map, Lyapunov exponents of the reservoir, and a scan over 240 random reservoirs."),
            ("Lecture_9/Notebooks/Lab_050_Cellular_automaton_reservoir.ipynb", "lab-050-cellular-automaton-reservoir", "Lab 050: Cellular automaton reservoir", "Elementary rules and their classes, damage spreading, the cellular automaton as a reservoir, the 5-bit memory task, the edge-of-chaos hypothesis and forecasts against the echo state network."),
        ],
    ),
    10: dict(
        deck=("beamer", "Lecture_10/beamer/main.tex"),
        last_frame="Reading",
        notes="Lecture_10/Lecture_notes/lecture_companion.pdf",
        notes_extended="Lecture_10/Lecture_notes/lecture_notes.pdf",
        title="Reinforcement Learning for Quantum State Preparation",
        ship_data=True,
        summary="We first develop reinforcement learning through states, actions, rewards, returns, policies and the Bellman equation. We show a changing Q-table, Q-learning, Double Q-learning, replay, target networks, DQN and Double DQN, followed by policy gradient, reward-to-go, REINFORCE, actor–critic and PPO. Quantum state preparation is then the implementation example. We state the target-state objective and introduce the action, matrices and exponential generators of H, T, CNOT, single-qubit rotations and XX/YY/ZZ interactions. GHZ, W and Dicke states are defined and their properties explained before constructing reference circuits. The cavity example introduces open evolution, weak measurement and the source feedback-learning result.",
        table_note="Classroom Labs 056a–063 (Bellman targets, CartPole, LunarLander, quantum targets, finite-budget GHZ, continuous angles, cavity checks) and the full studies 052–056",
        notebooks=[
            ("Lecture_10/Notebooks/Lab_063_Bellman_equations_from_experience.ipynb", "lab-063-bellman-from-experience", "Lab 063: Bellman equations from sampled experience", "Exact values of the running three-state process, sampled Bellman targets, TD errors at the solution, and tabular learning with its residual."),
            ("Lecture_10/Notebooks/Lab_061_CartPole_classroom.ipynb", "lab-061-cartpole", "Lab 061: Balancing a pole on a cart", "Observations, pushes and survival return, evaluation of a saved REINFORCE policy and one new policy-gradient update."),
            ("Lecture_10/Notebooks/Lab_062_LunarLander_classroom.ipynb", "lab-062-lunarlander", "Lab 062: Landing with discrete engine commands", "Engine actions and the shaped reward, evaluation of saved DQN and PPO agents, and a one-step TD target."),
            ("Lecture_10/Notebooks/Lab_057_GHZ_W_Dicke_target_states.ipynb", "lab-057-ghz-w-dicke-target-states", "Lab 057: GHZ, W and Dicke target states", "Gate matrices and Hamiltonian forms, target vectors, entanglement, losing a qubit, and reference circuits for GHZ6 and W6. No agent training."),
            ("Lecture_10/Notebooks/Lab_058_Finite_budget_GHZ_classroom.ipynb", "lab-058-finite-budget-ghz", "Lab 058: Finite-budget GHZ compilation", "Backward induction, a Q-table learned from transitions, DQN and Double DQN targets, and baseline estimators with an exact gradient."),
            ("Lecture_10/Notebooks/Lab_059_Continuous_angles_classroom.ipynb", "lab-059-continuous-angles", "Lab 059: Continuous angles with REINFORCE", "Gaussian and categorical scores, a small angle-and-gate policy for a two-qubit target, and a parameter-shift reference."),
            ("Lecture_10/Notebooks/Lab_060_Cavity_feedback_checks.ipynb", "lab-060-cavity-checks", "Lab 060: Cavity feedback checks", "Constant drive and threshold feedback on validation and test trajectories, with timestep, cutoff and noise scans. No agent training."),
            ("Lecture_10/Notebooks/Lab_056a_Pendulum_planning_classroom.ipynb", "lab-056a-pendulum-planning", "Lab 056a: Pendulum swing-up by planning", "Energy and phase portrait, value iteration on a grid, and evaluation of the planned policies on the continuous dynamics (optional)."),
            ("Lecture_10/Notebooks/Lab_052_Quantum_circuit_compilation.ipynb", "lab-052-quantum-circuit-compilation", "Lab 052: Quantum circuit compilation (full study)", "Discrete gate sequences learned by DQN, Double DQN and policy gradient, with exact small-system references."),
            ("Lecture_10/Notebooks/Lab_055_Quantum_state_compilation_with_policy_gradient.ipynb", "lab-055-continuous-state-compilation", "Lab 055: Compilation with continuous angles (full study)", "Policy gradient over rotation angles and entangling gates, compared with differentiating the simulator."),
            ("Lecture_10/Notebooks/Lab_054_Quantum_state_preparation.ipynb", "lab-054-quantum-state-preparation", "Lab 054: Preparation with Hamiltonian evolutions (full study)", "The full control study, including introductory and robustness extensions beyond the main lecture."),
            ("Lecture_10/Notebooks/Lab_053_Fock_state_in_a_leaky_cavity.ipynb", "lab-053-fock-state-cavity", "Lab 053: One photon in a leaky cavity (full study)", "A simplified simulation of noisy photon-number feedback and policy-gradient control, separate from the source paper's result."),
            ("Lecture_10/Notebooks/Lab_056_Pendulum_swing_up.ipynb", "lab-056-pendulum-swing-up", "Lab 056: Pendulum swing-up with Q-learning (full study)", "Value iteration and tabular Q-learning over four seeds, with learning curves and final success rates (optional)."),
        ],
    ),
    11: dict(
        deck=("beamer", "Lecture_11/beamer/main.tex"),
        last_frame="Loop Phase, Effective Coupling and Sign",
        notes="Lecture_11/Lecture_notes/lecture_notes.pdf",
        title="Quantum Information for Newcomers",
        ship_data=True,
        summary="The lecture has two parts. The first introduces quantum information theory, the rules that every qubit obeys whatever physical system carries it. One qubit is developed in the language of Pauli operators, with states, the Born rule, the Bloch sphere and every gate as the evolution operator of a Hamiltonian. A register of N qubits is stored as 2^N complex amplitudes in the computational basis, and its operators are Kronecker products, Pauli strings and sparse matrices. We follow bit strings and correlators in different bases, entanglement and the Schmidt decomposition, and the energy of a two-spin Hamiltonian estimated from measured bit strings. Density matrices, the partial trace, purity and entanglement entropy lead to general measurements, noise channels, the Lindblad equation and noise in quantum circuits, with fidelity and trace distance as distances between states. The first part closes with what quantum information allows and forbids, from the no-cloning theorem and the Holevo bound to Clifford circuits, random states, the partial-transpose test of entanglement and the quantum Fisher information. The second part turns to physical realisations of qubits. We start from an atom in classical laser light and derive how two of its levels become a qubit, through the Born–Oppenheimer and rotating-wave approximations, and compare it with a superconducting circuit, a spin-1/2 and photon polarisation. Interactions between qubits on different platforms give the native two-qubit gates, from which CZ and CNOT are compiled.",
        table_note="Classroom Labs 064–066a for the first part (one qubit, the two-spin register, density matrices, measurement and noise, what quantum information allows and forbids) and Labs 067–068 for the second part (from an atom in laser light to a qubit, from interacting qubits to two-qubit gates)",
        notebooks=[
            ("Lecture_11/Notebooks/Lab_064_One_qubit.ipynb", "lab-064-one-qubit", "Lab 064: One qubit, measurements and gates as rotations", "A qubit as a two-level system, the Pauli algebra, evolution from the Schrödinger equation, the driven atom, every single-qubit gate as a rotation, measurement in the X and Y bases, and shot noise."),
            ("Lecture_11/Notebooks/Lab_065_Two_spin_register.ipynb", "lab-065-two-spin-register", "Lab 065: The two-spin register", "Kronecker products and the ordering of the 2^N amplitudes, Pauli strings and gates on N qubits, two-qubit gates as rotations, the Bell state against a classical coin, the Schmidt decomposition, the register's Hamiltonian and energies from bit strings."),
            ("Lecture_11/Notebooks/Lab_066_Density_matrices_measurement_noise.ipynb", "lab-066-density-matrices-noise", "Lab 066: Density matrices, measurement and noise", "Pure and mixed states, the partial trace, purity and entanglement entropy, back-action and general measurements, six error models, the Lindblad equation, noise in quantum circuits, fidelity and trace distance."),
            ("Lecture_11/Notebooks/Lab_066a_What_quantum_information_allows_and_forbids.ipynb", "lab-066a-allows-and-forbids", "Lab 066a: What quantum information allows and forbids", "The no-cloning theorem, optimal one-copy discrimination of two states, the Holevo bound, controlled gates from CNOT and rotations, Clifford circuits followed by a bit update, concentration of random states and Clifford 2-designs, the Choi matrix of a channel, the partial-transpose test of mixed-state entanglement and the quantum Fisher information of GHZ states."),
            ("Lecture_11/Notebooks/Lab_067_Atom_in_laser_light_to_qubit.ipynb", "lab-067-atom-light-qubit", "Lab 067: An atom in laser light as a qubit", "The atomic Hamiltonian and Born–Oppenheimer, hydrogen orbitals and their dipole couplings, the rotating-wave approximation built step by step, the two-level block in Pauli language, Rabi oscillations, leakage, light shifts, spontaneous emission and laser pulses as gates."),
            ("Lecture_11/Notebooks/Lab_068_Interacting_qubits_to_gates.ipynb", "lab-068-interacting-qubits-gates", "Lab 068: Interactions and two-qubit gates", "A register on a connectivity graph, the physical origin of qubit couplings on four platforms, the Rydberg interaction in Pauli language, compiling CZ and CNOT from an Ising coupling, a simulated Rydberg blockade gate and SWAP routing between distant qubits."),
        ],
    ),
    12: dict(
        deck=("beamer", "Lecture_12/beamer/main.tex"),
        notes="Lecture_12/Lecture_notes/lecture_notes.pdf",
        title="Parametrised Quantum Circuits as Variational Ansätze",
        ship_data=True,
        summary="A parametrised quantum circuit prepares a trial state on a quantum register, and a classical computer tunes its gate angles from measured bit strings. We first use such circuits as variational ansätze for ground states: gradients come from the parameter-shift rule (or, with fewer circuit runs, from SPSA), and the variational quantum eigensolver with hardware-efficient and Hamiltonian-variational circuits is followed through its energy and entanglement during training on the transverse-field Ising chain. The same circuits then learn from quantum data: quantum autoencoders compress ground states and flag phase boundaries, a quantum convolutional network classifies a symmetry-protected topological phase, a quantum graph recurrent network learns an unknown Hamiltonian, and a circuit autoencoder compresses quantum channels through their Choi states. As probability models, quantum circuit Born machines learn distributions of bit strings. As classifiers, quantum kernels feed a support-vector machine and data re-uploading turns one or a few qubits into a universal classifier, with entanglement carrying information between qubits. Random states, typicality and barren plateaus finally set the limits of which circuits can be trained.",
        table_note="Classroom Labs 069–073b (circuits and gradients, SPSA, VQE, quantum autoencoders, QCNN, QGRNN, circuit autoencoder, random states and barren plateaus, Born machines, data re-uploading and quantum kernels); Lab 073 on QAOA at home",
        notebooks=[
            ("Lecture_12/Notebooks/Lab_069_Parametrised_circuits_and_gradients.ipynb", "lab-069-circuits-gradients", "Lab 069: Parametrised circuits and their gradients", "A circuit as a quantum trial state, the energy from bit strings, the parameter-shift rule against automatic differentiation and the cost of a gradient on a device (classroom route); mean field and other classical approximations in an optional appendix."),
            ("Lecture_12/Notebooks/Lab_069a_SPSA_and_Adam.ipynb", "lab-069a-spsa-adam", "Lab 069a: SPSA and Adam with few circuit runs", "Simultaneous-perturbation gradients from two circuit runs against the parameter-shift rule with two runs per angle, Adam on SPSA gradients, and the number of circuit runs each needs to reach the same energy in a shot-noise VQE."),
            ("Lecture_12/Notebooks/Lab_070_VQE_and_the_choice_of_ansatz.ipynb", "lab-070-vqe-ansatz", "Lab 070: VQE and the choice of ansatz", "Hardware-efficient and Hamiltonian-variational circuits for the transverse-field Ising chain, energy and mid-chain entanglement entropy during training, and the eight-spin phase diagram against exact results."),
            ("Lecture_12/Notebooks/Lab_070a_VQE_phase_diagram_of_the_XXZ_chain_in_a_field.ipynb", "lab-070a-xxz-phase-diagram", "Lab 070a: VQE phase diagram of the XXZ chain in a field", "Exact and variational maps of energy, order parameters, entanglement entropy and fidelity over the anisotropy and transverse field (at home; runs several minutes, or redraws the saved scan)."),
            ("Lecture_12/Notebooks/Lab_070b_Quantum_autoencoder.ipynb", "lab-070b-quantum-autoencoder", "Lab 070b: Quantum autoencoder", "Compressing ground states into fewer qubits, the trash Hamming distance as a local cost and its fidelity bound, Schmidt rank and compressibility, and phase boundaries flagged by the trash infidelity."),
            ("Lecture_12/Notebooks/Lab_070c_Quantum_convolutional_neural_network.ipynb", "lab-070c-qcnn", "Lab 070c: Quantum convolutional neural network", "The cluster-Ising chain and its symmetry-protected topological phase, string order, and a QCNN with shared kernels and pooling that classifies the phase from 40 labelled ground states."),
            ("Lecture_12/Notebooks/Lab_070d_Quantum_graph_recurrent_neural_network.ipynb", "lab-070d-qgrnn", "Lab 070d: Quantum graph recurrent neural network", "Learning the couplings of an unknown Ising Hamiltonian on a graph from time-evolved states, with Trotter layers as the model and the SWAP test as the fidelity estimate."),
            ("Lecture_12/Notebooks/Lab_070e_VQE_for_the_XYZ_chain_three_ansatze.ipynb", "lab-070e-xyz-three-ansatze", "Lab 070e: VQE for the XYZ chain, three ansätze", "A hardware-efficient circuit and two Hamiltonian-variational circuits on the XYZ chain, and why a mirror-symmetric ansatz cannot reach a mirror-odd ground state (at home)."),
            ("Lecture_12/Notebooks/Lab_070f_Quantum_circuit_autoencoder.ipynb", "lab-070f-circuit-autoencoder", "Lab 070f: Quantum circuit autoencoder", "Compressing quantum channels instead of states, through their Choi states, with the Choi fidelity as the figure of merit."),
            ("Lecture_12/Notebooks/Lab_071a_Random_states_and_typicality.ipynb", "lab-071a-random-states", "Lab 071a: Random states and typicality", "Haar-random states, concentration on the high-dimensional sphere and Lévy's lemma, the Page value of entanglement, and why typical states make gradients vanish (read before Lab 071)."),
            ("Lecture_12/Notebooks/Lab_071_Barren_plateaus.ipynb", "lab-071-barren-plateaus", "Lab 071: Barren plateaus", "Gradient variances over random angles for global and local costs and for structured circuits, and the number of shots needed to resolve a gradient."),
            ("Lecture_12/Notebooks/Lab_072_Modelling_probabilities_with_a_quantum_circuit.ipynb", "lab-072-born-machine", "Lab 072: Modelling probabilities with a quantum circuit", "Continuous data binned into bit strings, the Born-rule model, the Kullback–Leibler divergence as negative log-likelihood, product against entangling circuits, ancilla qubits, depth and evaluation from samples."),
            ("Lecture_12/Notebooks/Lab_073a_Data_reuploading_classifier.ipynb", "lab-073a-data-reuploading", "Lab 073a: Data re-uploading classifier", "One qubit as a classifier, label states for several classes, the circuit output as a Fourier series, multi-qubit classifiers and how entanglement carries information to the read-out qubit (optional cells switched by RUN_OPTIONAL)."),
            ("Lecture_12/Notebooks/Lab_073b_Quantum_kernels.ipynb", "lab-073b-quantum-kernels", "Lab 073b: Quantum kernels", "Data-encoding states as features, the quantum kernel in a support-vector machine, kernel entries estimated from shots, kernel alignment and exponential concentration of deep kernels."),
            ("Lecture_12/Notebooks/Lab_073_QUBO_and_QAOA.ipynb", "lab-073-qubo-qaoa", "Lab 073: QUBO and QAOA (at home)", "Binary optimisation as an Ising Hamiltonian diagonal in the computational basis, MaxCut, the QAOA circuit, its training and the sampled bit strings; not covered in the lecture slides."),
        ],
    ),
    13: dict(
        deck=("beamer", "Lecture_13/beamer/main.tex"),
        last_frame="Labs and Reading",
        notes="Lecture_13/Lecture_notes/lecture_notes.pdf",
        title="Learning Quantum States and Hamiltonians",
        ship_data=True,
        summary="A quantum device returns only bit strings, and this lecture asks what they reveal about the device itself. State tomography reconstructs the full density matrix from measurements in all Pauli settings, by linear inversion, least squares, projection onto physical states and maximum likelihood, and its cost grows exponentially with the number of qubits. Classical shadows estimate many local properties from randomised single-qubit measurements at a cost independent of the system size. A neural network trained on simulated data corrects few-shot tomographic estimates, following the attention-based method of Macarone Palmieri et al., including one-axis-twisted states of four qubits and their quantum Fisher information. Hamiltonian learning then infers the coefficients of the generator of the dynamics from measured bit strings by maximum likelihood through a differentiable forward model, with its identifiability limits, shot-noise and Cramér–Rao bounds, the rugged landscapes of strongly interacting models, neural differential equations as a remedy and a worked example of learning decay and dephasing rates of an open system.",
        table_note="Classroom Labs 074–077 (state tomography, classical shadows, neural-network tomography, Hamiltonian and Lindblad learning)",
        notebooks=[
            ("Lecture_13/Notebooks/Lab_074_Quantum_state_tomography.ipynb", "lab-074-state-tomography", "Lab 074: Quantum state tomography", "One qubit from three settings, Pauli measurements of two qubits, linear inversion, unphysical estimates and their projection, maximum likelihood by the RρR iteration and by a Cholesky parametrisation, shot scaling and the cost wall."),
            ("Lecture_13/Notebooks/Lab_075_Classical_shadows.ipynb", "lab-075-classical-shadows", "Lab 075: Classical shadows", "Random single-qubit measurements, snapshots and the inverse measurement channel, the 3^k variance, median of means, the energy and correlations of an eight-spin Ising chain from one data set, and independence of the system size."),
            ("Lecture_13/Notebooks/Lab_076_Neural_network_tomography.ipynb", "lab-076-nn-tomography", "Lab 076: Neural-network tomography", "Bias of physical estimates, the Cholesky representation, a multilayer perceptron and a self-attention network trained from scratch on two qubits, then four qubits with one-axis-twisted states and their quantum Fisher information."),
            ("Lecture_13/Notebooks/Lab_077_Hamiltonian_learning.ipynb", "lab-077-hamiltonian-learning", "Lab 077: Hamiltonian learning", "Maximum-likelihood learning of an XYZ chain from bit strings, the Ĥ ↔ −Ĥ* ambiguity, shot noise and the Cramér–Rao bound, learning decay and dephasing rates, rugged landscapes of the PXP model and neural differential equations."),
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
    media = os.path.join(out, "media")
    if os.path.isdir(media):
        shutil.rmtree(media)
    for lec in published():
        for rel in LECTURES[lec].get("media", []):
            os.makedirs(media, exist_ok=True)
            shutil.copyfile(os.path.join(COURSE, rel), os.path.join(media, os.path.basename(rel)))
            print(f"media   lecture {lec}: slides/media/{os.path.basename(rel)}")
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


def build_notes():
    """Copy the compiled lecture notes of published lectures to ./notes/lecture-NN.pdf (compressed)."""
    out = os.path.join(HERE, "notes"); os.makedirs(out, exist_ok=True)
    for old in glob.glob(os.path.join(out, "lecture-*.pdf")):
        n = int(re.search(r"lecture-(\d+)", old).group(1))
        if n not in READY or not LECTURES.get(n, {}).get("notes"):
            os.remove(old)
    for lec in published():
        rel = LECTURES[lec].get("notes")
        if not rel:
            continue
        src = os.path.join(COURSE, rel)
        if not os.path.exists(src):
            sys.exit(f"lecture {lec}: lecture notes not found: {src}")
        target = os.path.join(out, f"lecture-{lec:02d}.pdf")
        run(["gs", "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.5", "-dPDFSETTINGS=/ebook",
             "-dNOPAUSE", "-dBATCH", "-dQUIET", f"-sOutputFile={target}", src])
        if os.path.getsize(target) > os.path.getsize(src):
            shutil.copyfile(src, target)
        print(f"notes   lecture {lec}: {os.path.getsize(target) / 1e6:.1f} MB")
        extended = LECTURES[lec].get("notes_extended")
        if extended:
            extended_src = os.path.join(COURSE, extended)
            extended_dst = os.path.join(out, f"lecture-{lec:02d}-extended.pdf")
            run(["gs", "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.5", "-dPDFSETTINGS=/ebook",
                 "-dNOPAUSE", "-dBATCH", "-dQUIET", f"-sOutputFile={extended_dst}", extended_src])


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


def copy_md_figures(md, src_nb, out_dir):
    """Images referenced in markdown are copied next to the web notebook (figures/x.png)
    and the reference is rewritten."""
    def fix(m):
        alt, path = m.group(1), m.group(2)
        if path.startswith(("http", "data:")):
            return m.group(0)
        full = os.path.normpath(os.path.join(os.path.dirname(src_nb), path))
        if not os.path.exists(full):
            return m.group(0)
        os.makedirs(os.path.join(out_dir, "figures"), exist_ok=True)
        shutil.copyfile(full, os.path.join(out_dir, "figures", os.path.basename(full)))
        return f"![{alt}](figures/{os.path.basename(full)})"
    return re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)", fix, md)


def data_files(nb, src):
    """Data files data/<name> that the notebook uses and that exist next to the source notebook."""
    text = "\n".join(c.source for c in nb.cells)
    names = sorted(set(re.findall(r"(?<![\w.-])([\w.-]+\.(?:txt|csv|npz|npy))\b", text)))
    return [n for n in names if os.path.exists(os.path.join(os.path.dirname(src), "data", n))]


def with_data(nb, src, out_dir, rel):
    """Copy the data files next to the web notebook and add a first code cell that downloads
    them from the course repository when the notebook runs elsewhere (Colab)."""
    names = data_files(nb, src)
    if not names:
        return
    os.makedirs(os.path.join(out_dir, "data"), exist_ok=True)
    for n in names:
        shutil.copyfile(os.path.join(os.path.dirname(src), "data", n), os.path.join(out_dir, "data", n))
    base = f"https://raw.githubusercontent.com/{REPO}/main/{os.path.dirname(rel)}/data"
    cell = nbformat.v4.new_code_cell(
        "# data files of this notebook, downloaded from the course repository if they are not in ./data\n"
        "import os, urllib.request\n"
        "os.makedirs(\"data\", exist_ok=True)\n"
        f"for name in {names!r}:\n"
        "    if not os.path.exists(f\"data/{name}\"):\n"
        f"        urllib.request.urlretrieve(f\"{base}/{{name}}\", f\"data/{{name}}\")")
    cell.id = "web-data"
    for c in nb.cells:
        if c.cell_type == "markdown":
            c.source = re.sub(r"(?m)^> (\d+)\. Upload [^\n]*`(?:data/)?[\w.-]+\.txt`[^\n]*next to the notebook\.",
                              r"> \1. The first code cell downloads the data file into a folder `data` next to the notebook.",
                              c.source)
    first = next(i for i, c in enumerate(nb.cells) if c.cell_type == "code")
    nb.cells.insert(first, cell)


def build_notebooks():
    dst = os.path.join(HERE, "notebooks")
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    for lec in published():
        web_names = {os.path.basename(src): web for src, web, _, _ in notebooks_of(lec)}
        for src, web_name, title, _ in notebooks_of(lec):
            nb = nbformat.read(src, as_version=4)
            rel = f"notebooks/lecture-{lec:02d}/{web_name}.ipynb"
            nb.cells = drop_slide_export(nb.cells)
            for c in nb.cells:
                c.metadata.pop("execution", None)   # run timestamps
                if c.cell_type == "markdown":
                    c.source = strip_dates(c.source)
                    c.source = copy_md_figures(c.source, src, os.path.join(HERE, os.path.dirname(rel)))
                    c.source = re.sub(r"(?m)^\s*---\s*$", "<hr/>", c.source)
                    c.source = re.sub(r"\]\(([\w.-]+\.ipynb)\)",
                                      lambda m: f"]({web_names[m.group(1)]}.ipynb)" if m.group(1) in web_names else m.group(0),
                                      c.source)   # links between notebooks of the lecture use the web names
                elif c.cell_type == "code":
                    c.source = standalone_paths(c.source)
            if LECTURES[lec].get("ship_data"):
                with_data(nb, src, os.path.join(HERE, os.path.dirname(rel)), rel)
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
        buttons = []
        if L["deck"]:
            buttons.append(f"[Download the slides (PDF)](../slides/lecture-{lec:02d}.pdf){{.btn .btn-outline-primary}}")
        if L.get("notes"):
            notes_label = "Download the lecture companion (PDF)" if L.get("notes_extended") else "Download the lecture notes (PDF)"
            buttons.append(f"[{notes_label}](../notes/lecture-{lec:02d}.pdf){{.btn .btn-outline-primary}}")
        if L.get("notes_extended"):
            buttons.append(f"[Download the full lecture notes (PDF)](../notes/lecture-{lec:02d}-extended.pdf){{.btn .btn-outline-primary}}")
        if buttons:
            heading = "## Slides and lecture notes" if (L["deck"] and L.get("notes")) else ("## Slides" if L["deck"] else "## Lecture notes")
            text.append(heading + "\n\n" + " ".join(buttons) + "\n")
            if L.get("notes_extended"):
                text.append("The lecture companion follows the main presentation. The full notes include the derivations and extended comparisons.\n")
        if L["deck"]:
            text.append(f'<iframe src="../slides/lecture-{lec:02d}.pdf" width="100%" height="620" '
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
        build_notes()
    if "notebooks" in what:
        build_notebooks()
    if "pages" in what:
        build_pages()
        build_resources()
