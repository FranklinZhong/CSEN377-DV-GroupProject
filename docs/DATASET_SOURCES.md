# Dataset Sources

MedInsight uses three publicly available datasets, all free for academic use.

| Dataset | Source | License |
|---------|--------|---------|
| WebMD Drug Reviews | [Kaggle](https://www.kaggle.com/datasets/rohanharode07/webmd-drug-reviews-dataset) | CC BY-NC-SA 4.0 (academic only) |
| FAERS Drug Event Signals | [Kaggle](https://www.kaggle.com/datasets/anurmi/faers-drug-event-signals) | Public Domain (FDA official data) |
| FDA Drug Label API | [open.fda.gov](https://open.fda.gov/apis/drug/label/) | Public Domain (government open API) |

## Usage in the Project

- **WebMD Drug Reviews** — Patient review text and ratings; used for Vis 3 sentiment tug-of-war chart and paginated review viewer (NLP: spaCy + VADER).
- **FAERS** — Official FDA adverse event reports; used for Vis 1 side-effect body highlight and Vis 2 quarterly timeline animation.
- **FDA Drug Label API** — Official drug indications (benefits); used for Vis 1 benefit body highlight and the Drug Overview card.

## Academic Use Notice

WebMD data is used under the CC BY-NC-SA 4.0 license strictly for academic research.
This project is not intended for commercial use.
