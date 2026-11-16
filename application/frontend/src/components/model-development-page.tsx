"use client";

import Link from "next/link";
import { useState } from "react";
import { useApp } from "./app-providers";

const actuals = [10, 12, 15, 18, 20];
const estimates = [11, 10, 14, 22, 18];
const errors = actuals.map((actual, index) => actual - estimates[index]);
const mae =
  errors.reduce((sum, error) => sum + Math.abs(error), 0) / errors.length;
const rmse = Math.sqrt(
  errors.reduce((sum, error) => sum + error ** 2, 0) / errors.length,
);
const mean = actuals.reduce((sum, value) => sum + value, 0) / actuals.length;
const rSquared =
  1 -
  errors.reduce((sum, error) => sum + error ** 2, 0) /
    actuals.reduce((sum, value) => sum + (value - mean) ** 2, 0);

const lessonText = {
  en: {
    eyebrow: "Research lesson · Notebook 16",
    title: "How a model is selected",
    intro:
      "A practical, six-step look at comparing candidate models fairly, checking generalization, and preparing a selected model for use.",
    privacy: "Illustrative learning sequence · No project data exposed",
    steps: [
      [
        "Start with a baseline",
        "A simple reference shows whether a more complex approach adds useful predictive value.",
      ],
      [
        "Try different algorithms",
        "Compare linear models, regularized models, trees, ensembles, and boosting on the same task.",
      ],
      [
        "Compare errors",
        "Use more than one metric: average error, sensitivity to large misses, and explained variation tell different stories.",
      ],
      [
        "Evaluate generalization",
        "Test on later observations that were not used to fit the model. This checks whether patterns carry forward.",
      ],
      [
        "Choose the candidate",
        "Select the candidate that best balances evidence, generalization, and limitations in the tested setting.",
      ],
      [
        "Prepare for deployment",
        "Check that the saved model can be loaded consistently, validate inputs, record provenance, and monitor behavior.",
      ],
    ],
    candidates: [
      [
        "Global median baseline",
        "A single typical historical value; a simple point of comparison.",
      ],
      [
        "Crop–Season median baseline",
        "Group-level historical medians capture broad crop and season patterns.",
      ],
      [
        "Linear Regression",
        "Models additive linear relationships between inputs and the target.",
      ],
      [
        "Ridge Regression",
        "Adds regularization to reduce sensitivity to overly complex linear fits.",
      ],
      [
        "Decision Tree",
        "Learns branching rules that can represent nonlinear patterns.",
      ],
      [
        "Random Forest",
        "Combines many trees to reduce reliance on one set of decision rules.",
      ],
      [
        "HistGradientBoosting",
        "Builds trees sequentially, with later trees correcting earlier errors.",
      ],
    ],
    metricHeading: "A tiny synthetic example",
    metricIntro:
      "These five made-up values are only for learning. They are not project observations or model results.",
    mae: "MAE",
    maeCopy:
      "Mean absolute error: the average size of the miss, in the target unit.",
    rmse: "RMSE",
    rmseCopy: "Root mean squared error: larger misses count more strongly.",
    r2: "R²",
    r2Copy:
      "A relative measure of explained variation; compare it with the evaluation context and baselines.",
    actual: "Synthetic observed",
    estimate: "Synthetic estimate",
    lower: "Lower is better",
    context: "Context matters",
    modelChoice: "The project-selected candidate",
    choiceCopy:
      "HistGradientBoostingRegressor was selected from the candidates evaluated in this project. This is a project-specific choice—not a claim that boosting is universally best.",
    fit: "Why it was a reasonable fit",
    fitCopy:
      "The tested boosting approach can represent nonlinear relationships in structured data. The selection considered comparative performance and later-period evaluation, not a single headline score alone.",
    next: "From candidate to usable inference",
    nextCopy:
      "At a high level, a chosen estimator is serialized, loaded by a compatible runtime, supplied with validated supported inputs, and called to produce an estimate. Version and evaluation provenance should travel with that output. A saved artifact or working endpoint does not by itself mean production approval.",
    caveat:
      "Later-period evaluation is evidence about generalization, not a guarantee of future performance. Results depend on the evaluation design and available evidence.",
    research: "Explore the complete research journey",
    noCausal:
      "Metrics describe performance on an evaluation set; they do not establish causal relationships.",
  },
  hi: {
    eyebrow: "शोध पाठ · नोटबुक 16",
    title: "मॉडल कैसे चुना जाता है",
    intro:
      "उम्मीदवार मॉडलों की निष्पक्ष तुलना, सामान्यीकरण की जाँच और चुने गए मॉडल को उपयोग के लिए तैयार करने की छह-चरणीय जानकारी।",
    privacy: "केवल उदाहरण के लिए · परियोजना डेटा साझा नहीं",
    steps: [
      [
        "बेसलाइन से शुरू करें",
        "एक सरल संदर्भ बताता है कि जटिल तरीका उपयोगी अतिरिक्त पूर्वानुमान देता है या नहीं।",
      ],
      [
        "अलग-अलग एल्गोरिदम आज़माएँ",
        "एक ही कार्य पर रैखिक मॉडल, नियमितीकृत मॉडल, ट्री, एन्सेम्बल और बूस्टिंग की तुलना करें।",
      ],
      [
        "त्रुटियों की तुलना करें",
        "एक से अधिक माप देखें: औसत त्रुटि, बड़ी चूक का प्रभाव और समझाया गया बदलाव अलग बातें बताते हैं।",
      ],
      [
        "सामान्यीकरण जाँचें",
        "मॉडल प्रशिक्षण में उपयोग न किए गए बाद के अवलोकनों पर जाँचें कि सीखे पैटर्न टिकते हैं या नहीं।",
      ],
      [
        "उम्मीदवार चुनें",
        "परीक्षित संदर्भ में साक्ष्य, सामान्यीकरण और सीमाओं के बीच संतुलन रखने वाला विकल्प चुनें।",
      ],
      [
        "उपयोग के लिए तैयार करें",
        "सहेजे मॉडल की संगतता, इनपुट जाँच, स्रोत विवरण और व्यवहार की निगरानी सुनिश्चित करें।",
      ],
    ],
    candidates: [
      ["Global median baseline", "एक सामान्य ऐतिहासिक मान; सरल तुलना का आधार।"],
      [
        "Crop–Season median baseline",
        "फसल और मौसम के समूह-स्तरीय ऐतिहासिक मध्यक व्यापक पैटर्न दिखाते हैं।",
      ],
      [
        "Linear Regression",
        "इनपुट और लक्ष्य के बीच जोड़ात्मक रैखिक संबंध मॉडल करता है।",
      ],
      [
        "Ridge Regression",
        "अत्यधिक जटिल रैखिक फिट की संवेदनशीलता घटाने के लिए नियमितीकरण जोड़ता है।",
      ],
      [
        "Decision Tree",
        "गैर-रैखिक पैटर्न के लिए शाखाओं वाले निर्णय नियम सीखता है।",
      ],
      [
        "Random Forest",
        "कई ट्री मिलाकर एक ही निर्णय-नियम पर निर्भरता कम करता है।",
      ],
      [
        "HistGradientBoosting",
        "ट्री क्रम से बनाता है; बाद के ट्री पहले की त्रुटियाँ सुधारते हैं।",
      ],
    ],
    metricHeading: "एक छोटा कृत्रिम उदाहरण",
    metricIntro:
      "ये पाँच काल्पनिक मान केवल सीखने के लिए हैं। ये परियोजना के अवलोकन या मॉडल परिणाम नहीं हैं।",
    mae: "MAE",
    maeCopy: "औसत निरपेक्ष त्रुटि: लक्ष्य इकाई में चूक का औसत आकार।",
    rmse: "RMSE",
    rmseCopy: "वर्गमूल माध्य वर्ग त्रुटि: बड़ी चूकों को अधिक भार देती है।",
    r2: "R²",
    r2Copy: "समझाए गए बदलाव का सापेक्ष माप; संदर्भ और बेसलाइन के साथ देखें।",
    actual: "कृत्रिम अवलोकन",
    estimate: "कृत्रिम अनुमान",
    lower: "कम बेहतर",
    context: "संदर्भ ज़रूरी",
    modelChoice: "परियोजना का चयनित उम्मीदवार",
    choiceCopy:
      "इस परियोजना में जाँचे गए उम्मीदवारों में से HistGradientBoostingRegressor चुना गया। यह परियोजना-विशिष्ट चयन है, सभी परिस्थितियों के लिए सर्वश्रेष्ठ होने का दावा नहीं।",
    fit: "यह उपयुक्त क्यों था",
    fitCopy:
      "परीक्षित बूस्टिंग तरीका संरचित डेटा में गैर-रैखिक संबंध पकड़ सकता है। चयन में तुलनात्मक प्रदर्शन और बाद की अवधि का मूल्यांकन शामिल था, केवल एक मुख्य स्कोर नहीं।",
    next: "उम्मीदवार से उपयोग योग्य अनुमान तक",
    nextCopy:
      "सामान्य रूप में, चुने हुए मॉडल को सहेजा जाता है, संगत रनटाइम में लोड किया जाता है, समर्थित व सत्यापित इनपुट दिए जाते हैं और अनुमान निकाला जाता है। संस्करण और मूल्यांकन का स्रोत परिणाम के साथ दर्ज होना चाहिए। केवल सहेजी फ़ाइल या चालू सेवा से उत्पादन स्वीकृति सिद्ध नहीं होती।",
    caveat:
      "बाद की अवधि का मूल्यांकन सामान्यीकरण का साक्ष्य है, भविष्य के प्रदर्शन की गारंटी नहीं। परिणाम मूल्यांकन डिज़ाइन और उपलब्ध साक्ष्य पर निर्भर करते हैं।",
    research: "पूरी शोध यात्रा देखें",
    noCausal:
      "मेट्रिक्स मूल्यांकन सेट पर प्रदर्शन बताते हैं; कारण-परिणाम संबंध सिद्ध नहीं करते।",
  },
} as const;

export function ModelDevelopmentPage() {
  const { language } = useApp();
  const copy = lessonText[language];
  const [activeStep, setActiveStep] = useState(0);

  return (
    <div className="learning-page">
      <header className="learning-hero">
        <p className="eyebrow">{copy.eyebrow}</p>
        <h1>{copy.title}</h1>
        <p className="intro">{copy.intro}</p>
        <span className="learning-privacy">{copy.privacy}</span>
      </header>

      <section className="lesson-panel" aria-labelledby="lesson-title">
        <div className="lesson-heading">
          <div>
            <p className="eyebrow">01 / 06</p>
            <h2 id="lesson-title">{copy.steps[activeStep][0]}</h2>
          </div>
          <span className="lesson-count">
            {String(activeStep + 1).padStart(2, "0")} / 06
          </span>
        </div>
        <p>{copy.steps[activeStep][1]}</p>
        <div className="lesson-progress" aria-hidden="true">
          <span style={{ width: `${((activeStep + 1) / 6) * 100}%` }} />
        </div>
        <nav
          className="lesson-steps"
          aria-label="Model selection learning steps"
        >
          {copy.steps.map(([title], index) => (
            <button
              aria-current={activeStep === index ? "step" : undefined}
              className={
                activeStep === index ? "lesson-step active" : "lesson-step"
              }
              key={title}
              onClick={() => setActiveStep(index)}
              type="button"
            >
              <span>{String(index + 1).padStart(2, "0")}</span>
              {title}
            </button>
          ))}
        </nav>
      </section>

      <section className="lesson-section" aria-labelledby="candidate-title">
        <div className="section-intro">
          <p className="eyebrow">02 / Candidate models</p>
          <h2 id="candidate-title">
            A comparison should include meaningful baselines
          </h2>
          <p>
            A complex estimator is not automatically better. Candidate methods
            need the same target, evaluation split, and comparison conditions.
          </p>
        </div>
        <div className="candidate-grid">
          {copy.candidates.map(([name, description], index) => (
            <article className="candidate-card" key={name}>
              <span className="candidate-index">
                {String(index + 1).padStart(2, "0")}
              </span>
              <h3>{name}</h3>
              <p>{description}</p>
            </article>
          ))}
        </div>
        <p className="lesson-note">
          Weather-augmented Random Forest and HistGradientBoosting were explored
          as experiments, not separate production models.
        </p>
      </section>

      <section className="metrics-lesson" aria-labelledby="metrics-title">
        <div className="section-intro">
          <p className="eyebrow">03 / Evaluation metrics</p>
          <h2 id="metrics-title">{copy.metricHeading}</h2>
          <p>{copy.metricIntro}</p>
        </div>
        <div
          className="synthetic-chart"
          role="img"
          aria-label={`${copy.actual} and ${copy.estimate}: five synthetic values, not project data`}
        >
          <div className="chart-legend">
            <span>
              <i className="legend-dot observed" />
              {copy.actual}
            </span>
            <span>
              <i className="legend-dot predicted" />
              {copy.estimate}
            </span>
            <span className="synthetic-tag">SYNTHETIC EXAMPLE</span>
          </div>
          <div className="bar-chart">
            {actuals.map((value, index) => (
              <div className="bar-pair" key={index}>
                <div className="bar-track">
                  <span
                    className="bar observed"
                    style={{ height: `${(value / 24) * 100}%` }}
                  />
                  <span
                    className="bar predicted"
                    style={{ height: `${(estimates[index] / 24) * 100}%` }}
                  />
                </div>
                <span className="bar-label">Example {index + 1}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="metric-explainers">
          <article className="metric-explainer">
            <span className="metric-acronym">{copy.mae}</span>
            <strong>
              {mae.toFixed(1)} <small>synthetic units</small>
            </strong>
            <p>{copy.maeCopy}</p>
            <span className="metric-direction">{copy.lower}</span>
          </article>
          <article className="metric-explainer">
            <span className="metric-acronym">{copy.rmse}</span>
            <strong>
              {rmse.toFixed(1)} <small>synthetic units</small>
            </strong>
            <p>{copy.rmseCopy}</p>
            <span className="metric-direction">{copy.lower}</span>
          </article>
          <article className="metric-explainer">
            <span className="metric-acronym">{copy.r2}</span>
            <strong>{rSquared.toFixed(2)}</strong>
            <p>{copy.r2Copy}</p>
            <span className="metric-direction">{copy.context}</span>
          </article>
        </div>
        <p className="lesson-note">{copy.noCausal}</p>
      </section>

      <section className="selection-panel" aria-labelledby="selection-title">
        <p className="eyebrow">04 / Project decision</p>
        <h2 id="selection-title">{copy.modelChoice}</h2>
        <p>{copy.choiceCopy}</p>
        <div className="selection-detail">
          <div>
            <span className="detail-index">A</span>
            <h3>{copy.fit}</h3>
            <p>{copy.fitCopy}</p>
          </div>
          <div>
            <span className="detail-index">B</span>
            <h3>{copy.context}</h3>
            <p>{copy.caveat}</p>
          </div>
        </div>
      </section>

      <section className="deployment-lesson" aria-labelledby="deployment-title">
        <p className="eyebrow">05 / After selection</p>
        <h2 id="deployment-title">{copy.next}</h2>
        <p>{copy.nextCopy}</p>
        <div
          className="deployment-flow"
          aria-label="Conceptual model lifecycle"
        >
          {["Serialize", "Load & validate", "Infer", "Monitor & review"].map(
            (item, index) => (
              <div className="deployment-node" key={item}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <strong>{item}</strong>
              </div>
            ),
          )}
        </div>
      </section>

      <footer className="lesson-footer">
        <p>
          Research foundation: Notebook 16 · Yield model development and
          selection
        </p>
        <Link href="/research">
          {copy.research} <span aria-hidden="true">→</span>
        </Link>
      </footer>
    </div>
  );
}
