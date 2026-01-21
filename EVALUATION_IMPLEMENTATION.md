# Evaluation System Implementation

This document describes the evaluation and refinement system added to the PRISM agentic flow.

## Overview

The evaluation system adds quality gates to ensure responses meet minimum quality thresholds before being shown to users. It uses mathematical formulas to evaluate responses and includes an automatic refinement loop.

## Architecture

### Flow Changes

**Previous Flow:**
```
query_refinement → relevance → course_rag → (web_search) → personalization → END
```

**New Flow:**
```
query_refinement → relevance → course_rag → (web_search) → personalization → evaluation → (refinement loop) → END
```

### Key Components

1. **Evaluation Node** (`core/nodes/evaluation.py`)
   - Mathematically evaluates response quality
   - Uses different formulas for course vs. web sources
   - Returns scores and pass/fail decision

2. **Refinement Node** (`core/nodes/refinement.py`)
   - Improves responses based on evaluation feedback
   - Uses LLM to refine weak areas
   - Returns improved response

3. **State Updates** (`core/state.py`)
   - Added `evaluation_scores`: Dict of metric scores
   - Added `evaluation_passed`: Boolean pass/fail
   - Added `refinement_attempts`: Counter for refinement loop

4. **Graph Updates** (`core/graph.py`)
   - Added evaluation and refinement nodes
   - Added routing logic for refinement loop
   - Max 3 refinement attempts

## Evaluation Metrics

### Course-Based Responses
Evaluates using 4 metrics:
- **Relevance Score** (30% weight): Semantic alignment with query and context
- **Readability & Complexity** (25% weight): Matches degree level (Bachelors/Masters/PhD)
- **Coherence & Fluency** (20% weight): Logical flow and sentence coherence
- **Coverage** (25% weight): Completeness of answer

**Threshold:** Overall score >= 0.70 (70%)

### Web-Based Responses
Evaluates using 7 metrics:
- **Relevance Score** (20% weight)
- **Readability & Complexity** (15% weight)
- **Coherence & Fluency** (15% weight)
- **Coverage** (15% weight)
- **Source Credibility** (15% weight): Reputation of web sources
- **Consensus Score** (10% weight): Agreement across sources
- **Logical Consistency** (10% weight): Absence of contradictions

**Threshold:** Overall score >= 0.70 (70%)

## Mathematical Formulas

### Relevance Score
```python
relevance = 0.5 * query_answer_similarity + 0.5 * answer_context_similarity
```
Uses cosine similarity between embeddings.

### Readability & Complexity
```python
readability = exp(-((fk_grade - target_mean)² / (2 * target_variance)))
```
Uses Flesch-Kincaid grade level matched to degree:
- Bachelors: Grade 10-14
- Masters: Grade 12-16
- PhD: Grade 14-18

### Coherence & Fluency
```python
coherence = 0.5 * perplexity_score + 0.5 * local_coherence
```
- Perplexity: Normalized between 10-150
- Local coherence: Average cosine similarity of adjacent sentences

### Coverage
```python
coverage = found_subparts / total_subparts
```
Splits query into sub-questions and checks how many are addressed.

### Source Credibility (Web Only)
```python
credibility = mean([venue, author, recency, citation, integrity])
```
Weighted average of source quality metrics.

### Consensus Score (Web Only)
```python
consensus = mean((entailment_scores + 1) / 2)
```
Currently simplified - uses source count as proxy.

### Logical Consistency (Web Only)
```python
consistency = 1 - contradiction_rate
```
Currently defaults to 0.8 (can be enhanced with contradiction detection).

## Refinement Process

1. **Evaluation** checks if overall score >= 0.70
2. If **failed** and attempts < 3:
   - Identify weak areas from scores
   - Generate refinement prompt with specific feedback
   - LLM refines the response
   - Increment attempt counter
   - Loop back to evaluation
3. If **passed** or attempts >= 3:
   - If max attempts reached, prepend disclaimer
   - Return final response

## Configuration

### Threshold
Default threshold: **0.70** (70%)
Can be adjusted in `evaluation_node()` function.

### Max Refinement Attempts
Default: **3 attempts**
Can be adjusted in `route_after_evaluation()` function.

### Weights
Metric weights can be adjusted in:
- `evaluate_course_response()` for course metrics
- `evaluate_web_response()` for web metrics

## Dependencies Added

- `textstat>=0.7.3` - Readability metrics
- `scikit-learn>=1.3.0` - Cosine similarity
- `nltk>=3.8.1` - Sentence tokenization
- `numpy>=1.24.0` - Numerical operations

## Usage

The evaluation system is automatically integrated into the agent flow. No changes needed to existing code - it runs after personalization and before returning the final response.

## Future Enhancements

1. **Consensus Score**: Implement entailment model for better consensus detection
2. **Logical Consistency**: Add contradiction detection model
3. **Source Credibility**: Enhance with URL/domain analysis
4. **Perplexity Calculation**: Add actual perplexity calculation instead of default
5. **Caching**: Cache embeddings for repeated evaluations
6. **Tuning**: Add configuration file for thresholds and weights

## Testing

To test the evaluation system:
1. Run a query through the system
2. Check logs for evaluation scores
3. Verify refinement loop triggers when score < 0.70
4. Confirm disclaimer appears after 3 failed attempts

## Notes

- Evaluation happens **after** personalization, so the response is already personalized
- Refinement maintains citations and factual information
- The system gracefully handles errors by returning default scores
- All scores are normalized to [0.0, 1.0] range
