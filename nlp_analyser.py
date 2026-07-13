import re
from collections import Counter

from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords

from vaderSentiment.vaderSentiment import (
    SentimentIntensityAnalyzer
)

from sklearn.feature_extraction.text import (
    TfidfVectorizer
)


# --------------------------------------------------
# TF-IDF KEY PHRASES
# --------------------------------------------------

def extract_key_phrases(text, top_n=10):

    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        max_features=100
    )

    try:

        matrix = vectorizer.fit_transform([text])

        scores = zip(
            vectorizer.get_feature_names_out(),
            matrix.toarray()[0]
        )

        ranked = sorted(
            scores,
            key=lambda x: x[1],
            reverse=True
        )

        return [
            phrase
            for phrase, score in ranked[:top_n]
        ]

    except:
        return []


# --------------------------------------------------
# SUMMARY
# --------------------------------------------------

def generate_summary(text):

    sentences = sent_tokenize(text)

    return " ".join(
        sentences[:5]
    )


# --------------------------------------------------
# MANAGEMENT TONE
# --------------------------------------------------

def analyse_tone(text):

    analyzer = SentimentIntensityAnalyzer()

    score = analyzer.polarity_scores(text)

    compound = score["compound"]

    if compound > 0.2:
        overall = "Positive"

    elif compound < -0.2:
        overall = "Negative"

    else:
        overall = "Neutral"

    return {
        "overall": overall,
        "score": round(compound, 3)
    }


# --------------------------------------------------
# BUSINESS CHANGES
# --------------------------------------------------

BUSINESS_PATTERNS = [
    "launched",
    "introduced",
    "acquired",
    "partnership",
    "expanded",
    "new product",
    "new segment",
    "joint venture",
    "entered"
]


def extract_business_changes(text):

    results = []

    for sentence in sent_tokenize(text):

        lower = sentence.lower()

        if any(
            word in lower
            for word in BUSINESS_PATTERNS
        ):

            results.append(
                {
                    "description":
                    sentence.strip()
                }
            )

    return results[:10]


# --------------------------------------------------
# RISKS
# --------------------------------------------------

RISK_WORDS = [
    "risk",
    "challenge",
    "slowdown",
    "inflation",
    "competition",
    "uncertainty",
    "pressure",
    "weak demand",
    "delay",
    "headwind"
]


def extract_risks(text):

    risks = []

    for sentence in sent_tokenize(text):

        lower = sentence.lower()

        if any(
            word in lower
            for word in RISK_WORDS
        ):

            risks.append(
                {
                    "risk":
                    sentence.strip()
                }
            )

    return risks[:10]


# --------------------------------------------------
# COMMITMENTS
# --------------------------------------------------

COMMITMENT_WORDS = [
    "expect",
    "plan",
    "target",
    "aim",
    "guidance",
    "forecast",
    "will"
]


def extract_commitments(text):

    commitments = []

    for sentence in sent_tokenize(text):

        lower = sentence.lower()

        if any(
            word in lower
            for word in COMMITMENT_WORDS
        ):

            commitments.append(
                {
                    "commitment":
                    sentence.strip()
                }
            )

    return commitments[:10]


# --------------------------------------------------
# METRICS
# --------------------------------------------------

def extract_metrics(text):

    revenue = re.findall(
        r"\d+\.?\d*\s*%",
        text
    )

    return {

        "revenue_growth":
        revenue[0] if revenue else "",

        "margin":
        revenue[1] if len(revenue) > 1 else "",

        "order_book":
        "",

        "guidance":
        ""
    }


# --------------------------------------------------
# SINGLE QUARTER
# --------------------------------------------------

def analyse_quarter(transcript):

    text = transcript["text"]

    key_phrases = extract_key_phrases(text)

    earnings = [
        {"trigger": x}
        for x in key_phrases[:5]
    ]

    return {

        "quarter":
        transcript["quarter"],

        "summary":
        generate_summary(text),

        "management_tone":
        analyse_tone(text),

        "key_metrics_mentioned":
        extract_metrics(text),

        "earnings_triggers":
        earnings,

        "business_changes":
        extract_business_changes(text),

        "risks_and_issues":
        extract_risks(text),

        "commitments_made":
        extract_commitments(text)
    }


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def run_full_analysis(
    transcripts,
    company_name=None,
    verbose=False
):

    quarterly_analyses = []

    for transcript in transcripts:

        quarterly_analyses.append(
            analyse_quarter(transcript)
        )

    return {

        "company_name":
        company_name,

        "quarterly_analyses":
        quarterly_analyses
    }
