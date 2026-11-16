"use client";

import Link from "next/link";
import { PageHeading } from "./availability";

const stages = [
  {
    stage: "Setup and source review",
    items: [
      {
        id: 1,
        file: "01_project_setup_and_source_registry.ipynb",
        purpose: "Project setup and source registry",
        feature: "Research foundation",
      },
      {
        id: 2,
        file: "02_apy_dataset_acquisition_and_audit.ipynb",
        purpose: "Agricultural production data acquisition and audit",
        feature: "Yield Prediction",
      },
      {
        id: 3,
        file: "03_weather_dataset_acquisition_and_audit.ipynb",
        purpose: "Weather data acquisition and audit",
        feature: "Weather Intelligence",
      },
    ],
  },
  {
    stage: "Agricultural data analysis",
    items: [
      {
        id: 4,
        file: "04_apy_data_overview.ipynb",
        purpose: "Agricultural production data overview",
        feature: "Yield Prediction",
      },
      {
        id: 5,
        file: "05_apy_data_cleaning.ipynb",
        purpose: "Agricultural production data cleaning",
        feature: "Yield Prediction",
      },
      {
        id: 6,
        file: "06_apy_data_preprocessing.ipynb",
        purpose: "Agricultural production data preprocessing",
        feature: "Yield Prediction",
      },
      {
        id: 7,
        file: "07_apy_eda_analysis.ipynb",
        purpose: "Exploratory analysis of agricultural production",
        feature: "Crop Intelligence",
      },
      {
        id: 8,
        file: "08_apy_data_visualization.ipynb",
        purpose: "Agricultural production visualization",
        feature: "Crop Intelligence",
      },
    ],
  },
  {
    stage: "Weather data analysis",
    items: [
      {
        id: 9,
        file: "09_weather_data_overview.ipynb",
        purpose: "Weather data overview",
        feature: "Weather Intelligence",
      },
      {
        id: 10,
        file: "10_weather_data_cleaning.ipynb",
        purpose: "Weather data cleaning",
        feature: "Weather Intelligence",
      },
      {
        id: 11,
        file: "11_weather_data_preprocessing.ipynb",
        purpose: "Weather data preprocessing",
        feature: "Weather Intelligence",
      },
      {
        id: 12,
        file: "12_weather_eda_analysis.ipynb",
        purpose: "Exploratory weather analysis",
        feature: "Weather Intelligence",
      },
      {
        id: 13,
        file: "13_weather_data_visualization.ipynb",
        purpose: "Weather visualization",
        feature: "Weather Intelligence",
      },
    ],
  },
  {
    stage: "Integration and model research",
    items: [
      {
        id: 14,
        file: "14_crop_weather_integration.ipynb",
        purpose: "Crop and weather research integration",
        feature: "Weather Intelligence",
      },
      {
        id: 15,
        file: "15_feature_engineering.ipynb",
        purpose: "Research feature preparation",
        feature: "Yield Prediction",
      },
      {
        id: 16,
        file: "16_yield_model_development_and_selection.ipynb",
        purpose: "Yield model comparison and selection",
        feature: "Yield Prediction · Model Development",
      },
      {
        id: 17,
        file: "17_yield_model_deployment_readiness.ipynb",
        purpose: "Yield model deployment-readiness research",
        feature: "Yield Prediction · Model Insights",
      },
    ],
  },
  {
    stage: "Agricultural intelligence and governance",
    items: [
      {
        id: 18,
        file: "18_crop_recommendation.ipynb",
        purpose: "Historical crop ranking research",
        feature: "Crop Intelligence",
      },
      {
        id: 19,
        file: "19_weather_intelligence.ipynb",
        purpose: "Weather intelligence and experimental classification",
        feature: "Weather Intelligence",
      },
      {
        id: 20,
        file: "20_agricultural_risk_intelligence.ipynb",
        purpose: "Historical agricultural risk indicators",
        feature: "Agricultural Risk",
      },
      {
        id: 21,
        file: "21_model_explainability_and_scenarios.ipynb",
        purpose: "Model explainability and scenario research",
        feature: "Explainability & Scenarios",
      },
      {
        id: 22,
        file: "22_model_registry_and_policy_outputs.ipynb",
        purpose: "Model registry and policy-output research",
        feature: "Model Insights",
      },
    ],
  },
];

const portfolio = [
  {
    group: "Trained model with saved artifact",
    name: "Yield prediction",
    method: "HistGradientBoostingRegressor",
    evidence: "Notebooks 16–17",
    status: "Inference is experimental; production approval is not granted.",
  },
  {
    group: "Benchmark experiments",
    name: "Yield model candidates and baselines",
    method:
      "Regression baselines, linear models, trees, ensembles and boosting",
    evidence: "Notebook 16",
    status: "Comparison research; not presented as separate deployed services.",
  },
  {
    group: "Experimental model research",
    name: "Weather classification experiments",
    method: "Weather-augmented model experiments",
    evidence: "Notebook 19",
    status: "Experimental research; not a production classifier.",
  },
  {
    group: "Derived analytical services",
    name: "Crop ranking, risk indicators, explainability and registry",
    method: "Historical ranking and descriptive or governance methods",
    evidence: "Notebooks 18, 20–22",
    status:
      "Research methods exist; each application capability has its own live availability status.",
  },
];

export function ResearchPage() {
  return (
    <div className="research-page">
      <PageHeading
        eyebrow="Research & Models"
        title="From agricultural research to usable evidence"
        intro="A public-facing overview of the work behind BharatCrop Intelligence. This page describes methods and decisions without exposing records, feature-level inputs, or internal data movement."
      />
      <nav className="research-tabs" aria-label="Research sections">
        <a href="#portfolio">Model Portfolio</a>
        <a href="#journey">22-Notebook Journey</a>
        <a href="#methodology">Research Methodology</a>
        <a href="#model-development">Model Development & Evaluation</a>
      </nav>

      <section className="research-section" id="portfolio">
        <div className="section-intro">
          <p className="eyebrow">01 / Portfolio</p>
          <h2>What has been researched</h2>
          <p>
            Research artifacts, analytical methods, and live inference are
            different things. The status text distinguishes them.
          </p>
        </div>
        <div className="portfolio-grid">
          {portfolio.map((item, index) => (
            <article className="portfolio-card" key={item.name}>
              <div className="module-topline">
                <span>0{index + 1}</span>
                <span className="portfolio-group">{item.group}</span>
              </div>
              <h3>{item.name}</h3>
              <p>{item.method}</p>
              <dl className="portfolio-meta">
                <div>
                  <dt>Research evidence</dt>
                  <dd>{item.evidence}</dd>
                </div>
                <div>
                  <dt>Status</dt>
                  <dd>{item.status}</dd>
                </div>
              </dl>
            </article>
          ))}
        </div>
      </section>

      <section className="research-section" id="journey">
        <div className="section-intro">
          <p className="eyebrow">02 / Chronological research</p>
          <h2>The 22-notebook journey</h2>
          <p>
            Each entry names the research stage, notebook purpose, and the
            product area it informs.
          </p>
        </div>
        <div className="notebook-timeline">
          {stages.map((stage, stageIndex) => (
            <section className="timeline-stage" key={stage.stage}>
              <div className="timeline-stage-heading">
                <span>{String(stageIndex + 1).padStart(2, "0")}</span>
                <h3>{stage.stage}</h3>
              </div>
              <div className="notebook-list">
                {stage.items.map((item) => (
                  <article className="notebook-entry" key={item.id}>
                    <span className="notebook-number">
                      {String(item.id).padStart(2, "0")}
                    </span>
                    <div>
                      <strong>{item.file}</strong>
                      <p>{item.purpose}</p>
                    </div>
                    <span className="notebook-feature">{item.feature}</span>
                  </article>
                ))}
              </div>
            </section>
          ))}
        </div>
      </section>

      <section
        className="research-section methodology-section"
        id="methodology"
      >
        <div className="section-intro">
          <p className="eyebrow">03 / Methodology</p>
          <h2>Evidence before claims</h2>
          <p>
            Research outputs should be interpreted with their evaluation scope
            and current integration status in view.
          </p>
        </div>
        <div className="methodology-grid">
          <article>
            <span>01</span>
            <h3>Establish context</h3>
            <p>
              Review source quality, definitions, and the scope of the
              historical evidence before drawing conclusions.
            </p>
          </article>
          <article>
            <span>02</span>
            <h3>Compare consistently</h3>
            <p>
              Use common evaluation conditions to compare a simple baseline with
              more complex candidates.
            </p>
          </article>
          <article>
            <span>03</span>
            <h3>Check generalization</h3>
            <p>
              Later-period evaluation helps test whether learned patterns
              persist beyond the training examples.
            </p>
          </article>
          <article>
            <span>04</span>
            <h3>Communicate limitations</h3>
            <p>
              Show experimental, exploratory, or unavailable status clearly; do
              not imply causal or agronomic advice.
            </p>
          </article>
        </div>
      </section>

      <section className="model-development-cta" id="model-development">
        <div>
          <p className="eyebrow">04 / Interactive learning</p>
          <h2>How do we build and select a model?</h2>
          <p>
            Follow a short lesson on baselines, candidate algorithms, evaluation
            metrics, later-period generalization, and the project-specific
            selection decision.
          </p>
        </div>
        <Link className="btn-primary" href="/model-development">
          Open the learning guide <span aria-hidden="true">↗</span>
        </Link>
      </section>
      <p className="research-privacy-note">
        This overview intentionally excludes raw records, feature-level data,
        private artifacts, file locations, and operational infrastructure
        details.
      </p>
    </div>
  );
}
