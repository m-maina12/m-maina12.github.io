---
title: "A general framework for using two-stage meta-analysis with individual participant data to predict individualized treatment effects"
collection: publications
category: first-author
permalink: /publication/2026-05-14-two-stage-IPD-MA-ITE
authors:
  - Marta Mainetti
  - Konstantina Chalkou
  - Frederik Luca Philipona
  - Guido Schwarzer
  - Georgia Salanti
  - Orestis Efthimiou
excerpt: ''
date: 2026-05-14
venue: 'BMC Medical Research Methodology'
# slidesurl: 'https://m-maina12.github.io./files/slides1.pdf'
paperurl: 'https://doi.org/10.1186/s12874-026-03002-z'
paperdownloadurl: 'https://doi.org/10.1186/s12874-026-03002-z'
abstract: |
  **Background:** A key application of an individual participant data meta-analysis (IPD-MA) of randomized controlled trials is to predict individualized treatment effects (ITEs). A two-stage approach is often employed; however, analyses are typically limited to regression-based models. We present a general framework for two-stage IPD-MA for predicting ITE for a continuous outcome, applicable to any type of statistical or machine learning model. We also present a simulation study to assess the performance of the methods described here.

  **Methods:** We outline different types of models that can be used for trial-specific analyses at the first stage, including ordinary least squares (OLS) and penalized regressions, machine learning (ML) models, Bayesian models and meta-learners. Subsequently, we describe methods to synthesize results at the second stage and predict treatment effects on new individuals. Second-stage methods were chosen based on the first-stage model used, and include: (a) multivariate meta-analyses of regression coefficients, applicable to OLS; (b) weighted average of predicted ITEs, applicable to all models, with weights obtained via either bootstrapping or auxiliary OLS models; (c) multivariate Bayesian meta-analysis, applicable to Bayesian regressions; (d) weighted mixing of posterior distributions, applicable to all Bayesian models. A simulation study assessed the performance of all feasible combinations of first- and second-stage approaches under various scenarios in terms of median absolute error.

  **Results:** The performance of methods in simulations depended on the sample size, the heterogeneity of treatment effects, and the assumed form of effect modification. In scenarios with complex treatment-covariate interactions and large samples, ML models and meta-learners substantially outperformed regression methods. Conversely, in scenarios with linear effect modification, regression models performed better. Among second-stage methods for pooling ML models, we found that weighting based on an auxiliary OLS model was better than bootstrapping. We found no important differences between frequentist and Bayesian regression-based methods. Shrinkage models provided only modest improvements over unpenalized regression.

  **Conclusions:** Our framework for predicting patient-level treatment effects using two-stage IPD-MA can accommodate any type of statistical or machine learning model. The optimal method to use depends on the data generating mechanism, which in practice is unknown, and should be decided following internal validation.
# bibtexurl: 'https://m-maina12.github.io./files/bibtex1.bib'
---
